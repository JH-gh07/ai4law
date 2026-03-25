from fastapi import APIRouter

from backend.modules.scc.schema import SCCRequest, SCCResult
from backend.modules.scc.service import SCCService

router = APIRouter(tags=["scc"])
service = SCCService()


@router.post("/scc/generate", response_model=SCCResult)
def generate_scc(payload: SCCRequest) -> SCCResult:
    return service.generate_report(payload)
