from importlib.util import find_spec

import pytest

from backend.modules.catalog import (
    MODULE_DEFINITIONS,
    MODULES_BY_FRONTEND_KEY,
    MODULES_BY_ID,
    get_module,
)


def test_catalog_has_unique_stable_ids_and_frontend_keys() -> None:
    assert len(MODULE_DEFINITIONS) == 11
    assert len(MODULES_BY_ID) == len(MODULE_DEFINITIONS)
    assert len(MODULES_BY_FRONTEND_KEY) == len(MODULE_DEFINITIONS)


@pytest.mark.parametrize("definition", MODULE_DEFINITIONS)
def test_catalog_compatibility_packages_are_importable(definition) -> None:
    assert find_spec(definition.implementation_package) is not None
    assert definition.module_id.startswith(f"{definition.jurisdiction}.")
    assert definition.v1_api_prefix.startswith("/api/v1/")


def test_get_module_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="Unknown DataComplyFlow module_id"):
        get_module("cn.unknown")
