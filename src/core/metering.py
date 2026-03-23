"""Usage metering and rate limiting per tenant.

Provides:
- ``UsageMetric`` — individual usage metric entry.
- ``MeterType`` — types of metered resources.
- ``TenantMeter`` — per-tenant usage counters.
- ``MeteringService`` — aggregate usage tracking across tenants.
- ``RateLimiter`` — token-bucket rate limiter per tenant.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Meter types
# ---------------------------------------------------------------------------


class MeterType(str, Enum):
    """Categories of metered resources."""

    ASSETS_MIGRATED = "assets_migrated"
    LLM_TOKENS = "llm_tokens"
    API_CALLS = "api_calls"
    STORAGE_BYTES = "storage_bytes"
    SCREENSHOTS_CAPTURED = "screenshots_captured"
    PIPELINE_RUNS = "pipeline_runs"


# ---------------------------------------------------------------------------
# Usage metric
# ---------------------------------------------------------------------------


@dataclass
class UsageMetric:
    """A single usage metric entry."""

    meter_type: MeterType
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tenant meter
# ---------------------------------------------------------------------------


class TenantMeter:
    """Per-tenant usage counters."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._counters: dict[MeterType, float] = {m: 0.0 for m in MeterType}
        self._history: list[UsageMetric] = []

    def record(self, meter_type: MeterType, value: float = 1.0, **metadata: Any) -> None:
        """Record a usage event."""
        self._counters[meter_type] = self._counters.get(meter_type, 0.0) + value
        self._history.append(UsageMetric(
            meter_type=meter_type,
            value=value,
            metadata=metadata,
        ))

    def get(self, meter_type: MeterType) -> float:
        return self._counters.get(meter_type, 0.0)

    def reset(self, meter_type: MeterType | None = None) -> None:
        if meter_type:
            self._counters[meter_type] = 0.0
        else:
            for m in MeterType:
                self._counters[m] = 0.0

    @property
    def totals(self) -> dict[str, float]:
        return {m.value: v for m, v in self._counters.items() if v > 0}

    @property
    def history(self) -> list[UsageMetric]:
        return list(self._history)

    @property
    def event_count(self) -> int:
        return len(self._history)

    def summary(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "totals": self.totals,
            "event_count": self.event_count,
        }


# ---------------------------------------------------------------------------
# Metering service
# ---------------------------------------------------------------------------


class MeteringService:
    """Aggregate usage tracking across all tenants."""

    def __init__(self) -> None:
        self._meters: dict[str, TenantMeter] = {}

    def _get_or_create(self, tenant_id: str) -> TenantMeter:
        if tenant_id not in self._meters:
            self._meters[tenant_id] = TenantMeter(tenant_id)
        return self._meters[tenant_id]

    def record(self, tenant_id: str, meter_type: MeterType, value: float = 1.0, **metadata: Any) -> None:
        meter = self._get_or_create(tenant_id)
        meter.record(meter_type, value, **metadata)

    def get_meter(self, tenant_id: str) -> TenantMeter | None:
        return self._meters.get(tenant_id)

    def get_usage(self, tenant_id: str, meter_type: MeterType) -> float:
        meter = self._meters.get(tenant_id)
        return meter.get(meter_type) if meter else 0.0

    def get_all_summaries(self) -> list[dict[str, Any]]:
        return [m.summary() for m in self._meters.values()]

    def total_across_tenants(self, meter_type: MeterType) -> float:
        return sum(m.get(meter_type) for m in self._meters.values())

    @property
    def tenant_count(self) -> int:
        return len(self._meters)


# ---------------------------------------------------------------------------
# Rate limiter (token-bucket)
# ---------------------------------------------------------------------------


@dataclass
class _Bucket:
    """Internal token bucket state."""

    tokens: float
    max_tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)


class RateLimiter:
    """Token-bucket rate limiter per tenant.

    Each tenant gets a bucket with ``max_tokens`` capacity,
    refilling at ``refill_rate`` tokens per second.
    """

    def __init__(
        self,
        max_tokens: float = 100.0,
        refill_rate: float = 10.0,
    ) -> None:
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate
        self._buckets: dict[str, _Bucket] = {}

    def _get_bucket(self, tenant_id: str) -> _Bucket:
        if tenant_id not in self._buckets:
            self._buckets[tenant_id] = _Bucket(
                tokens=self._max_tokens,
                max_tokens=self._max_tokens,
                refill_rate=self._refill_rate,
            )
        bucket = self._buckets[tenant_id]
        # Refill tokens based on elapsed time
        now = time.time()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(bucket.max_tokens, bucket.tokens + elapsed * bucket.refill_rate)
        bucket.last_refill = now
        return bucket

    def allow(self, tenant_id: str, cost: float = 1.0) -> bool:
        """Check if the request is allowed (consumes tokens if yes)."""
        bucket = self._get_bucket(tenant_id)
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True
        return False

    def remaining(self, tenant_id: str) -> float:
        """Return remaining tokens for a tenant."""
        bucket = self._get_bucket(tenant_id)
        return bucket.tokens

    def wait_time(self, tenant_id: str, cost: float = 1.0) -> float:
        """Return seconds until enough tokens are available."""
        bucket = self._get_bucket(tenant_id)
        if bucket.tokens >= cost:
            return 0.0
        deficit = cost - bucket.tokens
        return deficit / bucket.refill_rate

    def set_limits(self, tenant_id: str, max_tokens: float, refill_rate: float) -> None:
        """Override limits for a specific tenant."""
        bucket = self._get_bucket(tenant_id)
        bucket.max_tokens = max_tokens
        bucket.refill_rate = refill_rate
        if bucket.tokens > max_tokens:
            bucket.tokens = max_tokens

    @property
    def tenant_count(self) -> int:
        return len(self._buckets)
