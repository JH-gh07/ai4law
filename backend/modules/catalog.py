"""Canonical jurisdiction and module identifiers for active product modules.

Implementation packages and v1 API paths are intentionally kept as compatibility
metadata.  Consumers such as benchmark adapters should use ``module_id`` as the
stable identifier instead of deriving identity from a Python directory name.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

Jurisdiction = Literal["cn", "eu", "us"]


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    module_id: str
    jurisdiction: Jurisdiction
    frontend_key: str
    implementation_package: str
    v1_api_prefix: str
    target_package: str


MODULE_DEFINITIONS = (
    ModuleDefinition(
        module_id="cn.transfer_diagnosis",
        jurisdiction="cn",
        frontend_key="diagnosis",
        implementation_package="backend.modules.diagnosis",
        v1_api_prefix="/api/v1/diagnosis",
        target_package="backend.domains.cn.transfer_diagnosis",
    ),
    ModuleDefinition(
        module_id="cn.security_assessment",
        jurisdiction="cn",
        frontend_key="assessment",
        implementation_package="backend.modules.assessment",
        v1_api_prefix="/api/v1/assessment",
        target_package="backend.domains.cn.security_assessment",
    ),
    ModuleDefinition(
        module_id="cn.scc_review",
        jurisdiction="cn",
        frontend_key="scc",
        implementation_package="backend.modules.scc",
        v1_api_prefix="/api/v1/scc",
        target_package="backend.domains.cn.scc_review",
    ),
    ModuleDefinition(
        module_id="cn.pipia",
        jurisdiction="cn",
        frontend_key="pipia",
        implementation_package="backend.modules.pipia",
        v1_api_prefix="/api/v1/pipia",
        target_package="backend.domains.cn.pipia",
    ),
    ModuleDefinition(
        module_id="cn.data_flow",
        jurisdiction="cn",
        frontend_key="cn_flow",
        implementation_package="backend.modules.cn_flow",
        v1_api_prefix="/api/v1/cn-flow",
        target_package="backend.domains.cn.data_flow",
    ),
    ModuleDefinition(
        module_id="eu.scc_review",
        jurisdiction="eu",
        frontend_key="eu_scc",
        implementation_package="backend.modules.eu_scc",
        v1_api_prefix="/api/v1/eu_scc",
        target_package="backend.domains.eu.scc_review",
    ),
    ModuleDefinition(
        module_id="eu.bcr_review",
        jurisdiction="eu",
        frontend_key="bcr",
        implementation_package="backend.modules.bcr",
        v1_api_prefix="/api/v1/bcr",
        target_package="backend.domains.eu.bcr_review",
    ),
    ModuleDefinition(
        module_id="eu.dpia",
        jurisdiction="eu",
        frontend_key="dpia",
        implementation_package="backend.modules.dpia",
        v1_api_prefix="/api/v1/dpia",
        target_package="backend.domains.eu.dpia",
    ),
    ModuleDefinition(
        module_id="eu.tia",
        jurisdiction="eu",
        frontend_key="tia",
        implementation_package="backend.modules.tia",
        v1_api_prefix="/api/v1/tia",
        target_package="backend.domains.eu.tia",
    ),
    ModuleDefinition(
        module_id="us.eo_14117",
        jurisdiction="us",
        frontend_key="us_14117",
        implementation_package="backend.modules.us_14117",
        v1_api_prefix="/api/v1/us_14117",
        target_package="backend.domains.us.eo_14117",
    ),
    ModuleDefinition(
        module_id="us.cpra",
        jurisdiction="us",
        frontend_key="cpra",
        implementation_package="backend.modules.cpra",
        v1_api_prefix="/api/v1/cpra",
        target_package="backend.domains.us.cpra",
    ),
)

MODULES_BY_ID = MappingProxyType({item.module_id: item for item in MODULE_DEFINITIONS})
MODULES_BY_FRONTEND_KEY = MappingProxyType(
    {item.frontend_key: item for item in MODULE_DEFINITIONS}
)


def get_module(module_id: str) -> ModuleDefinition:
    """Return one canonical module definition or raise a clear lookup error."""

    try:
        return MODULES_BY_ID[module_id]
    except KeyError as exc:
        raise ValueError(f"Unknown DataComplyFlow module_id: {module_id}") from exc
