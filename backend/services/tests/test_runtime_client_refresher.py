import inspect

import pytest

from backend.app import create_app
from backend.core.settings import Settings
from backend.services.runtime_client_refresher import refresh_runtime_clients


@pytest.mark.parametrize(
    "service_class",
    [
        pytest.param(
            "backend.domains.cn.security_assessment.service:AssessmentService",
            id="assessment",
        ),
        pytest.param("backend.domains.cn.pipia.service:PIPIAService", id="pipia"),
        pytest.param("backend.domains.eu.scc_review.service:EU_SCCService", id="scc"),
        pytest.param("backend.domains.eu.bcr_review.service:BCRService", id="bcr"),
        pytest.param("backend.domains.eu.dpia.service:DPIAService", id="dpia"),
        pytest.param("backend.domains.eu.tia.service:TIAService", id="tia"),
        pytest.param("backend.domains.us.cpra.service:CPRAService", id="cpra"),
        pytest.param(
            "backend.domains.us.eo14117.service:US14117Service",
            id="eo14117",
        ),
        pytest.param(
            "backend.domains.us.eo14117_flow_review.service:CNFlowService",
            id="cn_flow",
        ),
    ],
)
def test_async_modules_bind_submission_provider_snapshot(service_class: str) -> None:
    module_name, class_name = service_class.split(":", maxsplit=1)
    module = __import__(module_name, fromlist=[class_name])
    method = getattr(getattr(module, class_name), "submit_async")

    assert "llm_client=self.llm_client" in inspect.getsource(method)


def test_runtime_refresh_rebinds_all_module_llm_consumers(tmp_path) -> None:
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'refresh.db'}",
            storage_dir=tmp_path / "storage",
            _env_file=None,
        )
    )
    container = app.state.container

    from backend.domains.cn.security_assessment.router import service as assessment
    from backend.domains.cn.transfer_diagnosis.router import renderer as diagnosis_renderer
    from backend.domains.cn.pipia.router import service as pipia
    from backend.domains.eu.bcr_review.router import service as bcr
    from backend.domains.eu.dpia.router import service as dpia
    from backend.domains.eu.scc_review.router import service as scc
    from backend.domains.eu.tia.router import service as tia
    from backend.domains.us.cpra.router import service as cpra
    from backend.domains.us.eo14117.router import service as eo14117
    from backend.domains.us.eo14117_flow_review.router import service as flow

    _ = dpia.agents
    refresh_runtime_clients(container)
    client = container.llm_client
    legal_service = container.legal_api_service

    assert container.diagnosis_service.llm_client is client
    assert container.diagnosis_service.legal_api_service is legal_service
    assert container.review_service.reviewer.llm_client is client
    assert container.review_service.knowledge_base.legal_api_service is legal_service
    assert diagnosis_renderer.llm_client is client
    assert assessment.generator.llm is client
    assert assessment.renderer.llm_client is client
    assert assessment.retriever.legal_service is legal_service
    assert pipia.llm_client is client
    assert scc.llm_client is client
    assert all(agent.llm_client is client for agent in scc.agents.values())
    assert bcr.llm_client is client
    assert bcr.type_classifier.llm_client is client
    assert bcr.clause_reviewer.llm_client is client
    assert all(agent.llm_client is client for agent in bcr.agents.values())
    assert dpia.llm_client is client
    assert dpia.generator.llm is client
    assert all(agent.llm_client is client for agent in dpia.agents.values())
    assert tia.llm_client is client
    assert all(agent.llm_client is client for agent in tia.agents.values())
    assert flow.llm_client is client
    assert cpra.llm_client is client
    assert all(agent.llm_client is client for agent in cpra.agents.values())
    assert eo14117.llm_client is client
    assert all(agent.llm_client is client for agent in eo14117.agents.values())
