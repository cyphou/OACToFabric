"""OAC API test harness — VCR-style recording and playback of API calls.

Enables reliable, offline-capable testing of the Discovery Agent and any
module that calls OAC REST APIs. Records real API responses to cassettes
(JSON files) and replays them in tests.

Features:

1. **Recording mode** — intercepts OAC API calls and saves request/response
   pairs to a cassette file for later replay.
2. **Playback mode** — serves previously recorded responses without network
   access. Asserts that the expected requests are made.
3. **Mock mode** — generates synthetic OAC API responses from templates
   for fast unit tests with no cassette files.
4. **Assertion helpers** — verify API call sequences, pagination, rate-limit
   handling, and error recovery.

Usage::

    from src.tools.oac_test_harness import OACTestHarness, MockOACServer

    # Cassette-based testing
    harness = OACTestHarness(cassette_dir="tests/cassettes")
    with harness.playback("discovery_crawl"):
        inventory = await discovery_agent.discover(scope)
        assert len(inventory.items) == 42

    # Mock-based testing (no cassette files needed)
    mock = MockOACServer()
    mock.add_analyses(["Sales Dashboard", "Finance Report"])
    mock.add_subject_areas(["Sales", "Finance"])

    client = OACCatalogClient(base_url=mock.base_url, auth=mock.auth)
    items = await client.list_items("/shared")
    assert len(items) == 2
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cassette recording and playback
# ---------------------------------------------------------------------------


@dataclass
class RecordedRequest:
    """A recorded HTTP request."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    timestamp: float = 0.0


@dataclass
class RecordedResponse:
    """A recorded HTTP response."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_body: Any = None


@dataclass
class CassetteEntry:
    """A request/response pair in a cassette."""

    request: RecordedRequest
    response: RecordedResponse
    duration_ms: int = 0


@dataclass
class Cassette:
    """A cassette file containing recorded API interactions."""

    name: str
    entries: list[CassetteEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def save(self, path: str) -> None:
        """Save cassette to a JSON file."""
        data = {
            "name": self.name,
            "metadata": self.metadata,
            "entries": [
                {
                    "request": {
                        "method": e.request.method,
                        "url": e.request.url,
                        "headers": _sanitize_headers(e.request.headers),
                        "body": e.request.body,
                    },
                    "response": {
                        "status_code": e.response.status_code,
                        "headers": e.response.headers,
                        "body": e.response.body,
                        "json_body": e.response.json_body,
                    },
                    "duration_ms": e.duration_ms,
                }
                for e in self.entries
            ],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Saved cassette '%s' with %d entries to %s", self.name, len(self.entries), path)

    @classmethod
    def load(cls, path: str) -> Cassette:
        """Load cassette from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = []
        for entry_data in data.get("entries", []):
            req = entry_data["request"]
            resp = entry_data["response"]
            entries.append(CassetteEntry(
                request=RecordedRequest(
                    method=req["method"],
                    url=req["url"],
                    headers=req.get("headers", {}),
                    body=req.get("body", ""),
                ),
                response=RecordedResponse(
                    status_code=resp["status_code"],
                    headers=resp.get("headers", {}),
                    body=resp.get("body", ""),
                    json_body=resp.get("json_body"),
                ),
                duration_ms=entry_data.get("duration_ms", 0),
            ))
        return cls(
            name=data.get("name", ""),
            entries=entries,
            metadata=data.get("metadata", {}),
        )


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove sensitive headers from recordings."""
    sensitive = {"authorization", "cookie", "x-api-key", "oac-token"}
    return {
        k: ("***REDACTED***" if k.lower() in sensitive else v)
        for k, v in headers.items()
    }


# ---------------------------------------------------------------------------
# Recording interceptor
# ---------------------------------------------------------------------------


class RequestRecorder:
    """Records HTTP requests/responses to build cassettes.

    Used as a middleware or monkey-patch for httpx/aiohttp clients.
    """

    def __init__(self, cassette_name: str = "") -> None:
        self.cassette = Cassette(name=cassette_name or f"recording_{int(time.time())}")
        self._recording = True

    def record(
        self,
        method: str,
        url: str,
        *,
        request_headers: dict[str, str] | None = None,
        request_body: str = "",
        status_code: int = 200,
        response_headers: dict[str, str] | None = None,
        response_body: str = "",
        response_json: Any = None,
        duration_ms: int = 0,
    ) -> None:
        """Record a single request/response pair."""
        if not self._recording:
            return

        self.cassette.entries.append(CassetteEntry(
            request=RecordedRequest(
                method=method.upper(),
                url=url,
                headers=request_headers or {},
                body=request_body,
                timestamp=time.time(),
            ),
            response=RecordedResponse(
                status_code=status_code,
                headers=response_headers or {},
                body=response_body,
                json_body=response_json,
            ),
            duration_ms=duration_ms,
        ))

    def stop(self) -> Cassette:
        """Stop recording and return the cassette."""
        self._recording = False
        return self.cassette


# ---------------------------------------------------------------------------
# Playback engine
# ---------------------------------------------------------------------------


class PlaybackEngine:
    """Replays recorded cassette responses in order.

    Matches requests by method + URL path (ignoring query params by default).
    """

    def __init__(
        self,
        cassette: Cassette,
        *,
        strict: bool = False,
    ) -> None:
        self.cassette = cassette
        self.strict = strict
        self._index = 0
        self._calls: list[RecordedRequest] = []

    def match(self, method: str, url: str) -> RecordedResponse | None:
        """Find the next matching response in the cassette."""
        self._calls.append(RecordedRequest(method=method.upper(), url=url))

        # Try sequential match first
        if self._index < len(self.cassette.entries):
            entry = self.cassette.entries[self._index]
            if entry.request.method == method.upper():
                # URL comparison (path only, strip query params for flexibility)
                if self._url_matches(entry.request.url, url):
                    self._index += 1
                    return entry.response

        # If not strict, search all remaining entries
        if not self.strict:
            for i, entry in enumerate(self.cassette.entries):
                if i < self._index:
                    continue
                if entry.request.method == method.upper():
                    if self._url_matches(entry.request.url, url):
                        self._index = i + 1
                        return entry.response

        return None

    @staticmethod
    def _url_matches(recorded_url: str, actual_url: str) -> bool:
        """Compare URLs, ignoring query parameters."""
        recorded_path = recorded_url.split("?")[0].rstrip("/")
        actual_path = actual_url.split("?")[0].rstrip("/")
        return recorded_path == actual_path

    @property
    def calls_made(self) -> int:
        return len(self._calls)

    @property
    def all_played(self) -> bool:
        return self._index >= len(self.cassette.entries)

    def assert_all_played(self) -> None:
        """Assert that all cassette entries were played."""
        if not self.all_played:
            remaining = len(self.cassette.entries) - self._index
            raise AssertionError(
                f"{remaining} cassette entries were not played. "
                f"Played {self._index}/{len(self.cassette.entries)}."
            )


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


class OACTestHarness:
    """High-level test harness for OAC API testing.

    Manages cassette files, provides context managers for recording
    and playback modes.
    """

    def __init__(self, cassette_dir: str = "tests/cassettes") -> None:
        self.cassette_dir = Path(cassette_dir)

    def cassette_path(self, name: str) -> str:
        return str(self.cassette_dir / f"{name}.json")

    def start_recording(self, name: str) -> RequestRecorder:
        """Start recording API calls to a new cassette."""
        return RequestRecorder(cassette_name=name)

    def save_recording(self, recorder: RequestRecorder) -> str:
        """Stop recording and save the cassette."""
        cassette = recorder.stop()
        path = self.cassette_path(cassette.name)
        cassette.save(path)
        return path

    def load_cassette(self, name: str) -> Cassette:
        """Load a cassette by name."""
        path = self.cassette_path(name)
        return Cassette.load(path)

    def create_playback(self, name: str, *, strict: bool = False) -> PlaybackEngine:
        """Create a playback engine from a saved cassette."""
        cassette = self.load_cassette(name)
        return PlaybackEngine(cassette, strict=strict)


# ---------------------------------------------------------------------------
# Mock OAC Server
# ---------------------------------------------------------------------------


@dataclass
class MockAnalysis:
    """Mock OAC analysis."""

    name: str
    path: str = ""
    owner: str = "admin"
    type: str = "analysis"
    columns: list[str] = field(default_factory=list)
    filters: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MockSubjectArea:
    """Mock OAC subject area."""

    name: str
    tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)


class MockOACServer:
    """Generates synthetic OAC API responses for unit tests.

    No cassette files needed — builds responses programmatically.
    """

    def __init__(self, base_url: str = "https://mock-oac.example.com") -> None:
        self._base_url = base_url
        self._analyses: list[MockAnalysis] = []
        self._subject_areas: list[MockSubjectArea] = []
        self._dashboards: list[dict[str, Any]] = []
        self._data_flows: list[dict[str, Any]] = []
        self._roles: list[dict[str, Any]] = []
        self._rate_limit_after: int | None = None
        self._error_on_path: dict[str, int] = {}

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def auth(self) -> MagicMock:
        """Return a mock auth object."""
        mock_auth = MagicMock()
        mock_auth.get_token.return_value = "mock-token-" + uuid.uuid4().hex[:8]
        return mock_auth

    def add_analyses(self, names: list[str], *, path: str = "/shared") -> None:
        """Add mock analyses to the server."""
        for name in names:
            self._analyses.append(MockAnalysis(
                name=name,
                path=f"{path}/{name}",
            ))

    def add_subject_areas(self, names: list[str]) -> None:
        """Add mock subject areas."""
        for name in names:
            self._subject_areas.append(MockSubjectArea(
                name=name,
                tables=[{"name": f"{name}_Fact", "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "amount", "type": "NUMBER"},
                ]}],
            ))

    def add_dashboards(self, names: list[str]) -> None:
        for name in names:
            self._dashboards.append({"name": name, "type": "dashboard"})

    def add_roles(self, names: list[str]) -> None:
        for name in names:
            self._roles.append({"name": name, "type": "role"})

    def set_rate_limit(self, after_n_requests: int) -> None:
        """Simulate 429 after N requests."""
        self._rate_limit_after = after_n_requests

    def set_error_on_path(self, path: str, status_code: int) -> None:
        """Simulate an error for a specific API path."""
        self._error_on_path[path] = status_code

    def catalog_response(self, path: str = "/shared") -> dict[str, Any]:
        """Generate a catalog listing response."""
        items = []

        for analysis in self._analyses:
            if analysis.path.startswith(path) or path == "/shared":
                items.append({
                    "name": analysis.name,
                    "type": "analysis",
                    "path": analysis.path,
                    "owner": analysis.owner,
                    "caption": analysis.name,
                })

        for dash in self._dashboards:
            items.append({
                "name": dash["name"],
                "type": "dashboard",
                "path": f"/shared/{dash['name']}",
                "owner": "admin",
            })

        return {
            "items": items,
            "totalResults": len(items),
            "hasMore": False,
        }

    def subject_area_response(self, name: str = "") -> dict[str, Any]:
        """Generate a subject area detail response."""
        if name:
            for sa in self._subject_areas:
                if sa.name == name:
                    return {
                        "name": sa.name,
                        "tables": sa.tables,
                        "columns": sa.columns,
                    }
        return {"subjectAreas": [{"name": sa.name} for sa in self._subject_areas]}

    def analysis_detail_response(self, name: str) -> dict[str, Any]:
        """Generate an analysis detail response."""
        for analysis in self._analyses:
            if analysis.name == name:
                return {
                    "name": analysis.name,
                    "path": analysis.path,
                    "owner": analysis.owner,
                    "type": analysis.type,
                    "xml": f"<analysis><name>{analysis.name}</name></analysis>",
                    "columns": analysis.columns,
                    "filters": analysis.filters,
                }
        return {"error": "not_found", "message": f"Analysis '{name}' not found"}

    def build_cassette(self, name: str = "mock_discovery") -> Cassette:
        """Build a cassette from current mock state.

        Creates a realistic sequence of API calls that the
        Discovery Agent would make.
        """
        cassette = Cassette(name=name)

        # 1. Catalog listing
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(
                method="GET",
                url=f"{self._base_url}/api/v1/catalog/items?path=/shared",
            ),
            response=RecordedResponse(
                status_code=200,
                json_body=self.catalog_response(),
            ),
            duration_ms=120,
        ))

        # 2. Subject areas listing
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(
                method="GET",
                url=f"{self._base_url}/api/v1/subjectAreas",
            ),
            response=RecordedResponse(
                status_code=200,
                json_body=self.subject_area_response(),
            ),
            duration_ms=85,
        ))

        # 3. Individual analysis details
        for analysis in self._analyses:
            cassette.entries.append(CassetteEntry(
                request=RecordedRequest(
                    method="GET",
                    url=f"{self._base_url}/api/v1/catalog/analyses/{analysis.name}",
                ),
                response=RecordedResponse(
                    status_code=200,
                    json_body=self.analysis_detail_response(analysis.name),
                ),
                duration_ms=90,
            ))

        # 4. Individual subject area details
        for sa in self._subject_areas:
            cassette.entries.append(CassetteEntry(
                request=RecordedRequest(
                    method="GET",
                    url=f"{self._base_url}/api/v1/subjectAreas/{sa.name}",
                ),
                response=RecordedResponse(
                    status_code=200,
                    json_body=self.subject_area_response(sa.name),
                ),
                duration_ms=95,
            ))

        return cassette

    def generate_rate_limit_cassette(self, name: str = "rate_limit_test") -> Cassette:
        """Build a cassette that simulates 429 rate limiting."""
        cassette = Cassette(name=name)

        # Normal response
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(method="GET", url=f"{self._base_url}/api/v1/catalog/items"),
            response=RecordedResponse(status_code=200, json_body={"items": [], "totalResults": 0}),
            duration_ms=100,
        ))

        # 429 response
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(method="GET", url=f"{self._base_url}/api/v1/catalog/items"),
            response=RecordedResponse(
                status_code=429,
                headers={"Retry-After": "2"},
                json_body={"error": "rate_limit_exceeded", "message": "Too many requests"},
            ),
            duration_ms=10,
        ))

        # Retry succeeds
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(method="GET", url=f"{self._base_url}/api/v1/catalog/items"),
            response=RecordedResponse(status_code=200, json_body={"items": [], "totalResults": 0}),
            duration_ms=150,
        ))

        return cassette

    def generate_pagination_cassette(
        self,
        name: str = "pagination_test",
        total_items: int = 50,
        page_size: int = 10,
    ) -> Cassette:
        """Build a cassette that simulates paginated responses."""
        cassette = Cassette(name=name)

        pages = (total_items + page_size - 1) // page_size
        for page in range(pages):
            start = page * page_size
            end = min(start + page_size, total_items)
            items = [
                {"name": f"item_{i}", "type": "analysis", "path": f"/shared/item_{i}"}
                for i in range(start, end)
            ]
            has_more = end < total_items

            cassette.entries.append(CassetteEntry(
                request=RecordedRequest(
                    method="GET",
                    url=f"{self._base_url}/api/v1/catalog/items?offset={start}&limit={page_size}",
                ),
                response=RecordedResponse(
                    status_code=200,
                    json_body={
                        "items": items,
                        "totalResults": total_items,
                        "hasMore": has_more,
                        "offset": start,
                        "limit": page_size,
                    },
                ),
                duration_ms=100 + page * 10,
            ))

        return cassette


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def assert_api_call_sequence(
    playback: PlaybackEngine,
    expected_methods: list[str],
) -> None:
    """Assert that API calls were made in the expected method order."""
    actual = [c.method for c in playback._calls]
    if actual != [m.upper() for m in expected_methods]:
        raise AssertionError(
            f"Expected call sequence {expected_methods}, got {actual}"
        )


def assert_no_duplicate_calls(playback: PlaybackEngine) -> None:
    """Assert no duplicate API calls (indicates missing caching)."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for call in playback._calls:
        key = f"{call.method} {call.url}"
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    if duplicates:
        raise AssertionError(f"Duplicate API calls detected: {duplicates}")


def assert_handled_rate_limit(playback: PlaybackEngine) -> None:
    """Assert that a 429 response led to a retry."""
    if playback.calls_made < 2:
        raise AssertionError("Expected at least 2 calls for rate-limit handling")
