"""Cost controller — per-agent token budgets, semantic caching, and cost logging.

Tracks token consumption per agent per wave, enforces budgets, and provides
a semantic cache (embedding-based dedup) to avoid redundant LLM calls for
similar prompts.

Usage::

    controller = CostController(default_budget=100_000)
    controller.set_budget("04-semantic", 200_000)

    if controller.can_spend("04-semantic", estimated_tokens=500):
        response = await llm.complete(...)
        controller.record("04-semantic", response.total_tokens, cost_usd=0.02)
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TokenUsageRecord:
    """A single token-usage event."""

    agent_id: str
    prompt_hash: str
    tokens: int
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    cached: bool = False


@dataclass
class AgentBudget:
    """Per-agent budget tracking."""

    agent_id: str
    budget: int  # max tokens
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.used)

    @property
    def utilization(self) -> float:
        return self.used / self.budget if self.budget > 0 else 0.0

    @property
    def exhausted(self) -> bool:
        return self.budget > 0 and self.used >= self.budget


@dataclass
class CostSummary:
    """Aggregate cost summary."""

    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_calls: int = 0
    cache_hits: int = 0
    cache_hit_rate: float = 0.0
    by_agent: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Semantic cache
# ---------------------------------------------------------------------------


class SemanticCache:
    """Simple hash-based cache for prompts.

    Uses SHA-256 of the prompt pair as the key.  For true semantic
    similarity (embedding-based), swap the key function to use a
    vector store — the interface stays the same.
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._store: dict[str, Any] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _key(system: str, user: str) -> str:
        raw = f"{system}||{user}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, system: str, user: str) -> Any | None:
        k = self._key(system, user)
        if k in self._store:
            self._hits += 1
            return self._store[k]
        self._misses += 1
        return None

    def put(self, system: str, user: str, value: Any) -> None:
        if len(self._store) >= self._max_size:
            # Evict oldest entry (FIFO)
            oldest = next(iter(self._store))
            del self._store[oldest]
        k = self._key(system, user)
        self._store[k] = value

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0


# ---------------------------------------------------------------------------
# Cost controller
# ---------------------------------------------------------------------------


class CostController:
    """Manages token budgets and cost tracking across agents.

    Parameters
    ----------
    default_budget
        Default per-agent token budget (0 = unlimited).
    cost_per_1k_tokens
        Default cost per 1,000 tokens (for estimation).
    cache_max_size
        Maximum semantic cache entries.
    """

    def __init__(
        self,
        default_budget: int = 500_000,
        cost_per_1k_tokens: float = 0.03,
        cache_max_size: int = 10_000,
    ) -> None:
        self._default_budget = default_budget
        self._cost_per_1k = cost_per_1k_tokens
        self._budgets: dict[str, AgentBudget] = {}
        self._records: list[TokenUsageRecord] = []
        self.cache = SemanticCache(max_size=cache_max_size)

    # ---- budget management ----

    def set_budget(self, agent_id: str, budget: int) -> None:
        """Set or update the token budget for an agent."""
        if agent_id in self._budgets:
            self._budgets[agent_id].budget = budget
        else:
            self._budgets[agent_id] = AgentBudget(agent_id=agent_id, budget=budget)

    def get_budget(self, agent_id: str) -> AgentBudget:
        """Get (or lazily create) the budget for an agent."""
        if agent_id not in self._budgets:
            self._budgets[agent_id] = AgentBudget(
                agent_id=agent_id, budget=self._default_budget,
            )
        return self._budgets[agent_id]

    def can_spend(self, agent_id: str, estimated_tokens: int = 0) -> bool:
        """Check if the agent can afford *estimated_tokens*."""
        budget = self.get_budget(agent_id)
        if budget.budget <= 0:
            return True  # unlimited
        return budget.remaining >= estimated_tokens

    # ---- recording ----

    def record(
        self,
        agent_id: str,
        tokens: int,
        *,
        cost_usd: float | None = None,
        prompt_hash: str = "",
        cached: bool = False,
    ) -> None:
        """Record token usage for an agent."""
        actual_cost = cost_usd if cost_usd is not None else (tokens / 1000) * self._cost_per_1k
        budget = self.get_budget(agent_id)
        budget.used += tokens

        self._records.append(TokenUsageRecord(
            agent_id=agent_id,
            prompt_hash=prompt_hash,
            tokens=tokens,
            cost_usd=actual_cost,
            cached=cached,
        ))

        if budget.exhausted:
            logger.warning(
                "Agent %s token budget exhausted: %d/%d",
                agent_id, budget.used, budget.budget,
            )

    # ---- reporting ----

    def summary(self) -> CostSummary:
        """Generate aggregate cost summary."""
        s = CostSummary()
        by_agent: dict[str, dict[str, Any]] = {}

        for rec in self._records:
            s.total_tokens += rec.tokens
            s.total_cost_usd += rec.cost_usd
            s.total_calls += 1
            if rec.cached:
                s.cache_hits += 1

            if rec.agent_id not in by_agent:
                by_agent[rec.agent_id] = {"tokens": 0, "cost_usd": 0.0, "calls": 0}
            by_agent[rec.agent_id]["tokens"] += rec.tokens
            by_agent[rec.agent_id]["cost_usd"] += rec.cost_usd
            by_agent[rec.agent_id]["calls"] += 1

        s.by_agent = by_agent
        s.cache_hit_rate = self.cache.hit_rate
        return s

    def reset(self, agent_id: str | None = None) -> None:
        """Reset usage counters.  If *agent_id* is given, reset only that agent."""
        if agent_id:
            b = self._budgets.get(agent_id)
            if b:
                b.used = 0
        else:
            for b in self._budgets.values():
                b.used = 0
            self._records.clear()
            self.cache.clear()
