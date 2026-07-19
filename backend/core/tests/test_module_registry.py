import json
from importlib.util import find_spec
from pathlib import Path

import pytest

from backend.app import create_app
from backend.core.settings import Settings


REGISTRY_PATH = Path(__file__).resolve().parents[3] / "config" / "module_registry.json"


@pytest.fixture(scope="module")
def registry() -> list[dict[str, object]]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_registry_has_unique_stable_ids_and_frontend_keys(
    registry: list[dict[str, object]],
) -> None:
    module_ids = [item["module_id"] for item in registry]
    frontend_keys = [item["frontend_key"] for item in registry]

    assert len(registry) == 12
    assert len(set(module_ids)) == len(registry)
    assert len(set(frontend_keys)) == len(registry)
    assert "cn.unknown" not in module_ids


@pytest.mark.parametrize(
    "definition",
    json.loads(REGISTRY_PATH.read_text(encoding="utf-8")),
    ids=lambda item: str(item["module_id"]),
)
def test_registry_implementation_packages_are_importable(
    definition: dict[str, object],
) -> None:
    module_id = str(definition["module_id"])
    jurisdiction = str(definition["jurisdiction"])
    implementation_package = str(definition["implementation_package"])
    api_prefix = str(definition["v1_api_prefix"])

    assert jurisdiction in {"cn", "eu", "us"}
    assert module_id.startswith(f"{jurisdiction}.")
    assert api_prefix.startswith("/api/v1/")
    assert find_spec(implementation_package) is not None


def test_registry_api_prefixes_are_mounted_by_the_application(
    registry: list[dict[str, object]],
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(storage_dir=tmp_path / "storage", _env_file=None)
    )
    mounted_paths = {route.path for route in app.routes}
    missing_prefixes = [
        str(item["v1_api_prefix"])
        for item in registry
        if not any(
            path == str(item["v1_api_prefix"])
            or path.startswith(f'{item["v1_api_prefix"]}/')
            for path in mounted_paths
        )
    ]

    assert missing_prefixes == []


def test_compatibility_and_domain_boundaries_remain_explicit(
    registry: list[dict[str, object]],
) -> None:
    by_frontend_key = {str(item["frontend_key"]): item for item in registry}
    flow_review = by_frontend_key["cn_flow"]
    document_review = by_frontend_key["review"]

    assert flow_review["module_id"] == "us.eo_14117_flow_review"
    assert flow_review["jurisdiction"] == "us"
    assert flow_review["lifecycle"] == "legacy-compatible"
    assert flow_review["implementation_package"] == (
        "backend.domains.us.eo14117_flow_review"
    )
    assert document_review["jurisdiction"] == "cn"
    assert document_review["implementation_package"] == (
        "backend.domains.cn.document_review"
    )
