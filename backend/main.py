from backend.app import create_app
from backend.modules.assessment.router import router as assessment_router
from backend.modules.bcr.router import router as bcr_router
from backend.modules.cn_flow.router import router as cn_flow_router
from backend.modules.cpra.router import router as cpra_router
from backend.modules.dpia.router import router as dpia_router
from backend.modules.diagnosis.router import router as diagnosis_router
from backend.modules.pipia.router import router as pipia_router
from backend.modules.scc.router import router as scc_router
from backend.modules.tia.router import router as tia_router
from backend.modules.v0_task_gateway.router import router as v0_task_gateway_router

app = create_app()

app.include_router(diagnosis_router, prefix="/api/v1")
app.include_router(assessment_router, prefix="/api/v1")
app.include_router(scc_router, prefix="/api/v1")
app.include_router(pipia_router, prefix="/api/v1")
app.include_router(bcr_router, prefix="/api/v1")
app.include_router(dpia_router, prefix="/api/v1")
app.include_router(tia_router, prefix="/api/v1")
app.include_router(cn_flow_router, prefix="/api/v1")
app.include_router(cpra_router, prefix="/api/v1")
app.include_router(v0_task_gateway_router, prefix="/api/v0")
