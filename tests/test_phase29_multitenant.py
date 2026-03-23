"""Phase 29 — Multi-Tenant SaaS Readiness.

Tests cover:
- TenantTier enum
- Tenant model and to_dict
- TenantContext set/get/require/clear/scope
- TenantStore CRUD (create, get, get_by_name, list, update, delete)
- TenantStore enable/disable and counts
- TenantScoped mixin
- PlatformRole and ROLE_PERMISSIONS
- TokenClaims properties (is_expired, highest_role, permissions, has_permission)
- AuthConfig validation
- JWTValidator mock mode
- RBACEnforcer check and require
- APIKeyStore create/validate/revoke/delete/list
- MeterType enum
- TenantMeter record/get/reset/summary
- MeteringService cross-tenant tracking
- RateLimiter allow/remaining/wait_time/set_limits
"""

from __future__ import annotations

import time

import pytest

from src.api.auth import (
    APIKey,
    APIKeyStore,
    AuthConfig,
    JWTValidator,
    PlatformRole,
    RBACEnforcer,
    ROLE_PERMISSIONS,
    TokenClaims,
)
from src.core.metering import (
    MeterType,
    MeteringService,
    RateLimiter,
    TenantMeter,
    UsageMetric,
)
from src.core.tenant import (
    Tenant,
    TenantContext,
    TenantScoped,
    TenantStore,
    TenantTier,
)


# ===================================================================
# TenantTier enum
# ===================================================================


class TestTenantTier:
    def test_tier_values(self):
        assert TenantTier.FREE.value == "free"
        assert TenantTier.ENTERPRISE.value == "enterprise"
        assert len(TenantTier) == 4


# ===================================================================
# Tenant model
# ===================================================================


class TestTenant:
    def test_tenant_defaults(self):
        t = Tenant(tenant_id="t1", name="Acme")
        assert t.tier == TenantTier.STANDARD
        assert t.enabled is True
        assert t.max_concurrent_migrations == 3

    def test_to_dict(self):
        t = Tenant(tenant_id="t1", name="Acme", tier=TenantTier.PREMIUM)
        d = t.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["tier"] == "premium"
        assert "created_at" in d


# ===================================================================
# TenantContext
# ===================================================================


class TestTenantContext:
    def test_set_and_get(self):
        t = Tenant(tenant_id="t1", name="Test")
        TenantContext.set(t)
        assert TenantContext.get() is t
        TenantContext.clear()
        assert TenantContext.get() is None

    def test_require_raises(self):
        TenantContext.clear()
        with pytest.raises(RuntimeError, match="No tenant"):
            TenantContext.require()

    def test_require_succeeds(self):
        t = Tenant(tenant_id="t1", name="Test")
        TenantContext.set(t)
        assert TenantContext.require() is t
        TenantContext.clear()

    def test_scope_context_manager(self):
        t = Tenant(tenant_id="t1", name="Test")
        assert TenantContext.get() is None
        with TenantContext.scope(t) as tenant:
            assert tenant is t
            assert TenantContext.get() is t
        assert TenantContext.get() is None


# ===================================================================
# TenantStore
# ===================================================================


class TestTenantStore:
    def test_create(self):
        store = TenantStore()
        t = store.create("Acme", TenantTier.PREMIUM)
        assert t.name == "Acme"
        assert t.tier == TenantTier.PREMIUM
        assert store.count == 1

    def test_get(self):
        store = TenantStore()
        t = store.create("Acme")
        assert store.get(t.tenant_id) is t
        assert store.get("nonexistent") is None

    def test_get_by_name(self):
        store = TenantStore()
        store.create("Acme")
        assert store.get_by_name("Acme") is not None
        assert store.get_by_name("Missing") is None

    def test_list_all(self):
        store = TenantStore()
        store.create("A")
        store.create("B")
        assert len(store.list_all()) == 2

    def test_update(self):
        store = TenantStore()
        t = store.create("Acme")
        updated = store.update(t.tenant_id, name="Acme Corp")
        assert updated is not None
        assert updated.name == "Acme Corp"

    def test_update_nonexistent(self):
        store = TenantStore()
        assert store.update("x", name="whatever") is None

    def test_delete(self):
        store = TenantStore()
        t = store.create("Acme")
        assert store.delete(t.tenant_id) is True
        assert store.count == 0
        assert store.delete(t.tenant_id) is False

    def test_disable_enable(self):
        store = TenantStore()
        t = store.create("Acme")
        assert store.active_count == 1
        store.disable(t.tenant_id)
        assert store.active_count == 0
        store.enable(t.tenant_id)
        assert store.active_count == 1

    def test_disable_nonexistent(self):
        store = TenantStore()
        assert store.disable("x") is False
        assert store.enable("x") is False


# ===================================================================
# TenantScoped
# ===================================================================


class TestTenantScoped:
    def test_belongs_to(self):
        scoped = TenantScoped("t1")
        t = Tenant(tenant_id="t1", name="Test")
        assert scoped.belongs_to(t) is True

    def test_not_belongs_to(self):
        scoped = TenantScoped("t1")
        t = Tenant(tenant_id="t2", name="Other")
        assert scoped.belongs_to(t) is False

    def test_tenant_id_property(self):
        scoped = TenantScoped("abc")
        assert scoped.tenant_id == "abc"


# ===================================================================
# PlatformRole and permissions
# ===================================================================


class TestPlatformRole:
    def test_role_values(self):
        assert PlatformRole.ADMIN.value == "admin"
        assert PlatformRole.OPERATOR.value == "operator"
        assert PlatformRole.VIEWER.value == "viewer"

    def test_admin_has_all_permissions(self):
        admin_perms = ROLE_PERMISSIONS[PlatformRole.ADMIN]
        operator_perms = ROLE_PERMISSIONS[PlatformRole.OPERATOR]
        viewer_perms = ROLE_PERMISSIONS[PlatformRole.VIEWER]
        assert operator_perms.issubset(admin_perms)
        assert viewer_perms.issubset(admin_perms)


# ===================================================================
# TokenClaims
# ===================================================================


class TestTokenClaims:
    def test_not_expired(self):
        c = TokenClaims(sub="user1", expires_at=time.time() + 3600)
        assert c.is_expired is False

    def test_expired(self):
        c = TokenClaims(sub="user1", expires_at=time.time() - 10)
        assert c.is_expired is True

    def test_no_expiry(self):
        c = TokenClaims(sub="user1", expires_at=0.0)
        assert c.is_expired is False

    def test_highest_role_admin(self):
        c = TokenClaims(sub="u", roles=[PlatformRole.VIEWER, PlatformRole.ADMIN])
        assert c.highest_role == PlatformRole.ADMIN

    def test_highest_role_default(self):
        c = TokenClaims(sub="u")
        assert c.highest_role == PlatformRole.VIEWER

    def test_permissions_union(self):
        c = TokenClaims(sub="u", roles=[PlatformRole.OPERATOR, PlatformRole.VIEWER])
        assert "migration:create" in c.permissions
        assert "migration:read" in c.permissions

    def test_has_permission(self):
        c = TokenClaims(sub="u", roles=[PlatformRole.ADMIN])
        assert c.has_permission("tenant:delete") is True
        assert c.has_permission("nonexistent:perm") is False


# ===================================================================
# AuthConfig
# ===================================================================


class TestAuthConfig:
    def test_valid_config(self):
        cfg = AuthConfig(
            issuer="https://login.microsoftonline.com/xxx/v2.0",
            audience="api://oac2fabric",
        )
        assert cfg.validate() == []

    def test_invalid_config(self):
        cfg = AuthConfig(enabled=True, issuer="", audience="")
        errors = cfg.validate()
        assert len(errors) >= 2

    def test_disabled_skips_validation(self):
        cfg = AuthConfig(enabled=False)
        assert cfg.validate() == []


# ===================================================================
# JWTValidator
# ===================================================================


class TestJWTValidator:
    def test_auth_disabled_returns_admin(self):
        cfg = AuthConfig(enabled=False)
        v = JWTValidator(cfg)
        claims = v.validate("any-token")
        assert claims is not None
        assert PlatformRole.ADMIN in claims.roles

    def test_mock_mode(self):
        cfg = AuthConfig(enabled=True, issuer="x", audience="y")
        v = JWTValidator(cfg, mock_mode=True)
        claims = TokenClaims(sub="user1", roles=[PlatformRole.OPERATOR], expires_at=time.time() + 3600)
        v.register_mock_token("token-abc", claims)
        result = v.validate("token-abc")
        assert result is not None
        assert result.sub == "user1"

    def test_mock_invalid_token(self):
        cfg = AuthConfig(enabled=True, issuer="x", audience="y")
        v = JWTValidator(cfg, mock_mode=True)
        assert v.validate("unknown") is None

    def test_register_mock_requires_mock_mode(self):
        cfg = AuthConfig(enabled=True, issuer="x", audience="y")
        v = JWTValidator(cfg, mock_mode=False)
        with pytest.raises(RuntimeError):
            v.register_mock_token("x", TokenClaims(sub="u"))


# ===================================================================
# RBACEnforcer
# ===================================================================


class TestRBACEnforcer:
    def test_check_allowed(self):
        enforcer = RBACEnforcer()
        claims = TokenClaims(sub="u", roles=[PlatformRole.ADMIN])
        assert enforcer.check(claims, "migration:create") is True

    def test_check_denied(self):
        enforcer = RBACEnforcer()
        claims = TokenClaims(sub="u", roles=[PlatformRole.VIEWER])
        assert enforcer.check(claims, "migration:create") is False

    def test_require_raises(self):
        enforcer = RBACEnforcer()
        claims = TokenClaims(sub="u", roles=[PlatformRole.VIEWER])
        with pytest.raises(PermissionError):
            enforcer.require(claims, "migration:create")

    def test_require_passes(self):
        enforcer = RBACEnforcer()
        claims = TokenClaims(sub="u", roles=[PlatformRole.ADMIN])
        enforcer.require(claims, "migration:create")  # should not raise


# ===================================================================
# APIKeyStore
# ===================================================================


class TestAPIKeyStore:
    def test_create_key(self):
        store = APIKeyStore()
        raw, api_key = store.create_key("t1", "my-key")
        assert raw.startswith("oac2f_")
        assert api_key.tenant_id == "t1"
        assert store.count == 1

    def test_validate_key(self):
        store = APIKeyStore()
        raw, _ = store.create_key("t1", "key1")
        claims = store.validate_key(raw)
        assert claims is not None
        assert claims.tenant_id == "t1"

    def test_validate_invalid_key(self):
        store = APIKeyStore()
        assert store.validate_key("bogus") is None

    def test_revoke_key(self):
        store = APIKeyStore()
        raw, api_key = store.create_key("t1", "key1")
        assert store.revoke(api_key.key_id) is True
        assert store.validate_key(raw) is None

    def test_delete_key(self):
        store = APIKeyStore()
        _, api_key = store.create_key("t1", "key1")
        assert store.delete(api_key.key_id) is True
        assert store.count == 0

    def test_list_keys(self):
        store = APIKeyStore()
        store.create_key("t1", "a")
        store.create_key("t2", "b")
        store.create_key("t1", "c")
        assert len(store.list_keys()) == 3
        assert len(store.list_keys(tenant_id="t1")) == 2


# ===================================================================
# MeterType
# ===================================================================


class TestMeterType:
    def test_meter_values(self):
        assert MeterType.ASSETS_MIGRATED.value == "assets_migrated"
        assert MeterType.LLM_TOKENS.value == "llm_tokens"
        assert len(MeterType) == 6


# ===================================================================
# TenantMeter
# ===================================================================


class TestTenantMeter:
    def test_record_and_get(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.ASSETS_MIGRATED, 5)
        assert meter.get(MeterType.ASSETS_MIGRATED) == 5.0

    def test_accumulate(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.API_CALLS, 1)
        meter.record(MeterType.API_CALLS, 1)
        meter.record(MeterType.API_CALLS, 1)
        assert meter.get(MeterType.API_CALLS) == 3.0

    def test_reset_single(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.API_CALLS, 10)
        meter.reset(MeterType.API_CALLS)
        assert meter.get(MeterType.API_CALLS) == 0.0

    def test_reset_all(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.API_CALLS, 10)
        meter.record(MeterType.LLM_TOKENS, 500)
        meter.reset()
        assert meter.get(MeterType.API_CALLS) == 0.0
        assert meter.get(MeterType.LLM_TOKENS) == 0.0

    def test_totals(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.ASSETS_MIGRATED, 5)
        totals = meter.totals
        assert "assets_migrated" in totals

    def test_event_count(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.API_CALLS)
        meter.record(MeterType.API_CALLS)
        assert meter.event_count == 2

    def test_summary(self):
        meter = TenantMeter("t1")
        meter.record(MeterType.API_CALLS, 3)
        s = meter.summary()
        assert s["tenant_id"] == "t1"
        assert s["event_count"] == 1


# ===================================================================
# MeteringService
# ===================================================================


class TestMeteringService:
    def test_record_and_get(self):
        svc = MeteringService()
        svc.record("t1", MeterType.API_CALLS, 5)
        assert svc.get_usage("t1", MeterType.API_CALLS) == 5.0

    def test_get_nonexistent(self):
        svc = MeteringService()
        assert svc.get_usage("xx", MeterType.API_CALLS) == 0.0

    def test_multiple_tenants(self):
        svc = MeteringService()
        svc.record("t1", MeterType.API_CALLS, 10)
        svc.record("t2", MeterType.API_CALLS, 20)
        assert svc.total_across_tenants(MeterType.API_CALLS) == 30.0
        assert svc.tenant_count == 2

    def test_get_all_summaries(self):
        svc = MeteringService()
        svc.record("t1", MeterType.API_CALLS, 1)
        svc.record("t2", MeterType.LLM_TOKENS, 100)
        summaries = svc.get_all_summaries()
        assert len(summaries) == 2

    def test_get_meter(self):
        svc = MeteringService()
        svc.record("t1", MeterType.API_CALLS, 1)
        meter = svc.get_meter("t1")
        assert meter is not None
        assert svc.get_meter("xx") is None


# ===================================================================
# RateLimiter
# ===================================================================


class TestRateLimiter:
    def test_allow_within_limit(self):
        limiter = RateLimiter(max_tokens=10, refill_rate=0)
        assert limiter.allow("t1") is True

    def test_allow_exhausted(self):
        limiter = RateLimiter(max_tokens=2, refill_rate=0)
        assert limiter.allow("t1") is True
        assert limiter.allow("t1") is True
        assert limiter.allow("t1") is False

    def test_remaining(self):
        limiter = RateLimiter(max_tokens=5, refill_rate=0)
        limiter.allow("t1", cost=3)
        assert limiter.remaining("t1") == pytest.approx(2.0, abs=0.5)

    def test_wait_time_zero(self):
        limiter = RateLimiter(max_tokens=10, refill_rate=1)
        assert limiter.wait_time("t1") == 0.0

    def test_wait_time_positive(self):
        limiter = RateLimiter(max_tokens=1, refill_rate=1)
        limiter.allow("t1")  # exhaust
        wt = limiter.wait_time("t1")
        assert wt >= 0.0

    def test_set_limits(self):
        limiter = RateLimiter(max_tokens=10, refill_rate=1)
        limiter.set_limits("t1", max_tokens=5, refill_rate=2)
        # Bucket should exist with custom limits
        assert limiter.tenant_count == 1

    def test_independent_tenants(self):
        limiter = RateLimiter(max_tokens=2, refill_rate=0)
        limiter.allow("t1")
        limiter.allow("t1")
        assert limiter.allow("t1") is False
        assert limiter.allow("t2") is True  # t2 has its own bucket
