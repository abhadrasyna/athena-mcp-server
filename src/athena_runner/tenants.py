"""Tenant -> Athena database/table name mapping.

Every `AthenaQuery`/`AdoptionMetric` subclass runs against one tenant's
Glue database (and, for debug-events-based queries, one tenant's
debug-events table). All onboarded tenants follow the same naming
pattern -- `unified_<tenant_id>` / `<tenant_id>_ccl_debug_events` -- so
a single `TenantConfig`/`TenantRegistry` pair is the one place that
pattern and the list of known tenants live, instead of each query/
metric class hardcoding a literal default.
"""

import dataclasses
from typing import Dict, List


@dataclasses.dataclass(frozen=True)
class TenantConfig:
  """One onboarded tenant's identity and derived Athena object names.

  Attributes:
    tenant_id: The tenant's unique id, e.g. `"e6auj7k7"`. Also the
      suffix/prefix embedded in this tenant's Glue database/table
      names.
    code: Short, unique, CLI-facing identifier for this tenant, e.g.
      `"ZA"` for South Africa.
    country: Human-readable country name, e.g. `"South Africa"`.
    database: The Athena database/catalog this tenant's queries run
      against; derived as `f"unified_{tenant_id}"`.
    debug_events_table: The debug-events table this tenant's
      debug-events-based queries run against; derived as
      `f"{tenant_id}_ccl_debug_events"`.
  """

  tenant_id: str
  code: str
  country: str
  database: str
  debug_events_table: str

  @classmethod
  def from_tenant_id(cls, tenant_id: str, code: str,
                      country: str) -> "TenantConfig":
    """Builds a `TenantConfig`, deriving `database`/`debug_events_table`
    from `tenant_id` via the standard naming pattern.

    Args:
      tenant_id: The tenant's unique id, e.g. `"e6auj7k7"`.
      code: Short, unique, CLI-facing identifier, e.g. `"ZA"`.
      country: Human-readable country name, e.g. `"South Africa"`.
    """
    return cls(
        tenant_id=tenant_id,
        code=code,
        country=country,
        database=f"unified_{tenant_id}",
        debug_events_table=f"{tenant_id}_ccl_debug_events")


class TenantRegistry:
  """Looks up `TenantConfig`s by `tenant_id` (primary) or `code`.

  New tenants register themselves here instead of query/metric classes
  hardcoding a tenant's database/table literals (Open/Closed
  principle) -- onboarding a tenant never requires touching an
  existing query/metric class.
  """

  def __init__(self) -> None:
    self._by_tenant_id: Dict[str, TenantConfig] = {}
    self._by_code: Dict[str, TenantConfig] = {}

  def register(self, tenant: TenantConfig) -> None:
    """Adds `tenant` to the registry, keyed by its `tenant_id` and `code`."""
    self._by_tenant_id[tenant.tenant_id] = tenant
    self._by_code[tenant.code] = tenant

  def get(self, key: str) -> TenantConfig:
    """Returns the registered tenant for `key`.

    Args:
      key: A `tenant_id` (e.g. `"e6auj7k7"`), tried first, or a `code`
        (e.g. `"ZA"`) as a fallback.

    Raises:
      KeyError: If `key` matches neither a registered `tenant_id` nor
        `code`.
    """
    try:
      return self._by_tenant_id[key]
    except KeyError:
      pass
    try:
      return self._by_code[key]
    except KeyError as exc:
      available = ", ".join(self.tenant_ids()) or "(none registered)"
      raise KeyError(
          f"Unknown tenant '{key}'. Available tenant ids: {available}"
      ) from exc

  def tenant_ids(self) -> List[str]:
    """Returns all registered tenant ids, in registration order."""
    return list(self._by_tenant_id)

  def all(self) -> List[TenantConfig]:
    """Returns all registered tenants, in registration order."""
    return list(self._by_tenant_id.values())


# South Africa is the default tenant for every existing query/metric
# constructor (see DA-2 in docs/database-abstraction/stories.md) -- it
# must keep behaving exactly as it did before tenants existed, so
# existing callers/cron jobs are unaffected until they explicitly opt
# into another tenant.
DEFAULT_TENANT = TenantConfig.from_tenant_id("e6auj7k7", "ZA", "South Africa")


def default_registry() -> TenantRegistry:
  """Builds the registry with all onboarded tenants pre-registered."""
  registry = TenantRegistry()
  registry.register(DEFAULT_TENANT)
  registry.register(
      TenantConfig.from_tenant_id("a7vli5h8", "ZM", "Zambia"))
  registry.register(
      TenantConfig.from_tenant_id("is1aldzq", "GH", "Ghana"))
  registry.register(
      TenantConfig.from_tenant_id("jsxgloje", "NG", "Nigeria"))
  return registry
