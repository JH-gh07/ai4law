"""
本文件用于定义应用容器类 `AppContainer`，该类负责管理应用的核心组件和服务的实例化与依赖注入。
`AppContainer` 包含数据库引擎、会话工厂、WebSocket 管理器、任务调度器、LLM 客户端、文件服务、报告服务、会话服务、法律 API 服务、诊断服务和文档审查服务等。
"""
from backend.common.llm.client import LLMClient
from backend.core.db import build_engine, build_session_factory
from backend.core.settings import Settings
from backend.services.diagnosis_session_service import DiagnosisSessionService
from backend.services.file_service import FileService
from backend.integrations.delilegal import DeliLegalService
from backend.services.report_service import ReportService
from backend.domains.cn.document_review.service import ReviewService
from backend.services.session_service import SessionService
from backend.services.task_dispatcher import build_task_dispatcher
from backend.services.websocket_manager import WebSocketManager


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings.report_dir.mkdir(parents=True, exist_ok=True)

        self.engine = build_engine(settings.database_url)
        self.session_factory = build_session_factory(self.engine)
        self.websocket_manager = WebSocketManager()
        self.task_dispatcher = build_task_dispatcher(settings.task_mode)

        self.llm_client = LLMClient(settings)
        self.file_service = FileService(settings)
        self.report_service = ReportService(settings)
        self.session_service = SessionService()
        self.legal_api_service = DeliLegalService(settings)
        self.diagnosis_service = DiagnosisSessionService(
            self.report_service, self.session_service, self.legal_api_service, self.llm_client
        )
        self.review_service = ReviewService(
            file_service=self.file_service,
            report_service=self.report_service,
            task_dispatcher=self.task_dispatcher,
            websocket_manager=self.websocket_manager,
            session_factory=self.session_factory,
            legal_api_service=self.legal_api_service,
            llm_client=self.llm_client,
        )
