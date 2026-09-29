"""Per-project Athena configuration registry (`PROJECT_CONFIGS`).

Every MCP tool takes a `project` parameter (see `story.md`'s "MCP tools
exposed" section) that resolves, server-side, to a `ProjectConfig` here --
callers never pass raw profile/bucket/region values for an already-
registered project.

Registered-query registry loading mechanism (resolves `story.md`'s open
decision "exact mechanism by which `athena_mcp` loads a project's own
`AthenaQuery` registry"):

Each project keeps owning its own `AthenaQuery` subclasses/registry --
this repo does not duplicate MTN's `queries/registry.py`. A plain
`import athena_runner.queries.registry` won't work here because
`aws-access-cli` and `oasis-athena-mcp` both define a *different*
top-level package literally named `athena_runner` (this repo's own,
already-imported copy would shadow it), and a `pip install -e`-style
dependency the other direction (`aws-access-cli` depending on this repo)
isn't the chosen direction either (`aws-access-cli` keeps its own copy
until `MCP-9`). Instead, `_load_mtn_registry` below mounts the sibling
project's `queries/` directory *as* the `athena_runner.queries`
sub-package of this process's own already-imported `athena_runner`
package, using `importlib`'s file-location loading. This works cleanly
because the generic modules that MTN's query definitions still import
(e.g. `athena_runner.date_utils`, via `queries/params.py`) are the exact
same ported code already live in `sys.modules['athena_runner']` (see
`MCP-1`) -- so the mounted `queries` sub-package resolves those imports
against *this* repo's `athena_runner`, no path hacks or `sys.path`
mutation required.

Post-migration note: this repo (formerly `github_copilot/oasis-athena-mcp`)
now lives independently at `myWork/myOffice/athena-mcp-server`, no longer
a sibling checkout of `aws-access-cli` (which stays at
`github_copilot/aws-access-cli`). The mounted directory location
therefore defaults to that fixed, machine-specific absolute path rather
than a `../aws-access-cli/...` relative sibling path -- override via
`MTN_QUERY_REGISTRY_DIR` on any other machine/layout.
"""

import dataclasses
import importlib
import importlib.util
import os
import pathlib
import sys
import types
from collections.abc import Callable
from typing import Protocol

from athena_runner import config as config_lib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "output"

_DEFAULT_MTN_QUERIES_DIR = pathlib.Path(
    "/Users/abhadra/github_copilot/aws-access-cli/scripts/athena_runner/queries"
)


class AthenaQueryProtocol(Protocol):
  """Shape of a project's `AthenaQuery` implementation.

  Defined locally (Dependency Inversion) so this module never needs a
  hard import of another project's `queries.base.AthenaQuery` -- any
  object satisfying this shape (structurally, not by inheritance) works.
  """

  @property
  def name(self) -> str:
    """Short, unique, CLI-facing identifier, e.g. 'playback-outcome'."""

  @property
  def database(self) -> str:
    """The Athena database/catalog this query runs against."""

  def build_sql(self, params: dict[str, str]) -> str:
    """Renders the final SQL statement to execute for `params`."""

  def output_filename(self, params: dict[str, str]) -> str:
    """Returns the local CSV filename to save this query's result as."""


class QueryRegistryProtocol(Protocol):
  """Shape of a project's query registry (e.g. `queries.registry`)."""

  def get(self, name: str) -> AthenaQueryProtocol:
    """Returns the registered query named `name`."""

  def names(self) -> list[str]:
    """Returns all registered query names, sorted."""


RegistryLoader = Callable[[], QueryRegistryProtocol]


@dataclasses.dataclass(frozen=True)
class ProjectConfig:
  """Everything a `project` MCP tool parameter resolves to.

  Attributes:
    run_config: profile/workgroup/output_location/region/timeouts used
      to build an `AwsClientFactory` and `BotoAthenaQueryExecutor`.
    database: Default Athena database/catalog for ad-hoc SQL when the
      caller doesn't override it. Registered queries use their own
      `AthenaQuery.database` instead.
    registry_loader: Zero-arg callable returning this project's
      `QueryRegistryProtocol`, or None if registered queries aren't
      available yet for this project (ad-hoc SQL may still work).
      Lazy so importing this module never touches another project's
      filesystem/modules unless a registered-query tool is actually
      invoked.
  """

  run_config: config_lib.RunConfig
  database: str
  registry_loader: RegistryLoader | None = None


def _mount_external_subpackage(
    dotted_name: str, directory: pathlib.Path) -> types.ModuleType:
  """Loads `directory` as the `dotted_name` sub-package, in `sys.modules`.

  Idempotent: returns the already-mounted module on repeat calls instead
  of re-executing `directory`'s `__init__.py`.

  Args:
    dotted_name: Full dotted name to register, e.g. 'athena_runner.queries'.
      Its parent package (e.g. 'athena_runner') must already be imported.
    directory: Filesystem directory containing that sub-package's
      `__init__.py` and sibling modules.

  Raises:
    FileNotFoundError: If `directory` (or its `__init__.py`) is missing --
      e.g. the sibling repo isn't checked out at the expected location.
  """
  if dotted_name in sys.modules:
    return sys.modules[dotted_name]
  init_path = directory / "__init__.py"
  if not init_path.is_file():
    raise FileNotFoundError(
        f"Expected an '__init__.py' at {init_path} to mount as "
        f"'{dotted_name}' -- is the sibling repo checked out there? "
        "Override with the MTN_QUERY_REGISTRY_DIR environment variable.")
  parent_name, _, child_name = dotted_name.rpartition(".")
  spec = importlib.util.spec_from_file_location(
      dotted_name, init_path, submodule_search_locations=[str(directory)])
  module = importlib.util.module_from_spec(spec)
  sys.modules[dotted_name] = module
  spec.loader.exec_module(module)
  if parent_name:
    setattr(sys.modules[parent_name], child_name, module)
  return module


def _mtn_queries_dir() -> pathlib.Path:
  """Returns the directory to mount as MTN's `athena_runner.queries`."""
  override = os.environ.get("MTN_QUERY_REGISTRY_DIR")
  return pathlib.Path(override) if override else _DEFAULT_MTN_QUERIES_DIR


def _load_mtn_registry() -> QueryRegistryProtocol:
  """Loads MTN's `queries.registry.default_registry()` from `aws-access-cli`."""
  _mount_external_subpackage("athena_runner.queries", _mtn_queries_dir())
  registry_module = importlib.import_module("athena_runner.queries.registry")
  return registry_module.default_registry()


PROJECT_CONFIGS: dict[str, ProjectConfig | None] = {
    "mtn": ProjectConfig(
        run_config=config_lib.RunConfig(
            profile="clarissa-insights-product",
            workgroup="primary",
            output_location="s3://clarissaprod-apps-athena-query-results/",
            output_dir=str(_DEFAULT_OUTPUT_DIR),
            region="eu-central-1",
        ),
        database="unified_e6auj7k7",
        registry_loader=_load_mtn_registry,
    ),
    # Registered per ASTRO-0/ASTRO-2's account/role/output-bucket/region
    # discovery and ASTRO-3's schema-incompatibility finding (see
    # tasks.md). No registered-query registry yet -- ASTRO-3 found none
    # of MTN's AthenaQuery subclasses apply to Astro's schema (they
    # hardcode FROM "unified_sessions"/"fact_navigation_interactions",
    # neither of which exists in Astro's `default` database).
    # Astro-specific AthenaQuery subclasses, ported from
    # `astro-events-household-report/queries/*.md`, are deferred to a
    # follow-up task; ad-hoc SQL via `run_athena_sql` works today.
    "astro": ProjectConfig(
        run_config=config_lib.RunConfig(
            profile="astro-insights-product",
            workgroup="primary",
            output_location=(
                "s3://aws-athena-query-results-315899926467-ap-southeast-1/"
            ),
            output_dir=str(_DEFAULT_OUTPUT_DIR),
            region="ap-southeast-1",
        ),
        database="default",
        registry_loader=None,
    ),
}


def get_project_config(project: str) -> ProjectConfig:
  """Resolves `project` to its full `ProjectConfig`.

  Args:
    project: Registered project name, e.g. 'mtn'.

  Raises:
    ValueError: If `project` isn't a registered name at all.
    NotImplementedError: If `project` is registered but not yet fully
      configured (no project currently in this state; kept for any
      future project registered ahead of its own discovery tasks).
  """
  if project not in PROJECT_CONFIGS:
    available = ", ".join(sorted(PROJECT_CONFIGS)) or "(none registered)"
    raise ValueError(
        f"Unknown project '{project}'. Registered projects: {available}.")
  project_config = PROJECT_CONFIGS[project]
  if project_config is None:
    raise NotImplementedError(
        f"Project '{project}' is registered but not fully configured yet "
        "-- its AWS account/role/output bucket/region are still pending "
        "discovery. Refusing to run with a partial config rather than "
        "silently defaulting.")
  return project_config
