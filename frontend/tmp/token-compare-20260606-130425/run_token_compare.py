from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path('/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.common.llm.client import LLMClient
from backend.core.settings import Settings
from backend.common.rag.retriever import retrieve_regulations
from backend.common.runtime.module_run import finalize_run
from backend.services.legal_api_service import DeliLegalService
from backend.modules.assessment.schema import AssessmentRequest
from backend.modules.assessment.service import AssessmentService
from backend.modules.diagnosis.report_renderer import DiagnosisReportRenderer
from backend.modules.diagnosis.schema import DiagnosisAnswers
from backend.modules.diagnosis.service import DiagnosisService
from backend.modules.pipia.schema import PIPIARequest
from backend.modules.pipia.service import PIPIAService

RUN_ROOT = ROOT / 'frontend' / 'tmp' / 'token-compare-20260606-130425'
ARCHIVE_DIR = RUN_ROOT / 'archive'
RESULT_JSON = RUN_ROOT / 'results.json'
RESULT_MD = RUN_ROOT / 'results.md'


def build_settings(provider_id: str, model: str) -> Settings:
    runtime_settings_path = ROOT / 'storage' / 'runtime_settings.json'
    env_path = ROOT / '.env'
    env: dict[str, str] = {}
    if env_path.exists():
        for raw in env_path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    runtime_payload: dict[str, Any] = {}
    if runtime_settings_path.exists():
        try:
            runtime_payload = json.loads(runtime_settings_path.read_text(encoding='utf-8'))
        except Exception:
            runtime_payload = {}

    provider_map: dict[str, dict[str, Any]] = {}
    llm_payload = runtime_payload.get('llm') if isinstance(runtime_payload.get('llm'), dict) else {}
    providers_payload = llm_payload.get('providers') if isinstance(llm_payload.get('providers'), list) else []
    for item in providers_payload:
        if isinstance(item, dict) and item.get('id'):
            provider_map[str(item['id'])] = item

    settings = Settings(
        database_url=f"sqlite:///{(RUN_ROOT / 'tmp_run.db').as_posix()}",
        storage_dir=RUN_ROOT / 'storage',
    )
    siliconflow_cfg = provider_map.get('siliconflow', {})
    tencent_cfg = provider_map.get('tencent_hunyuan', {})
    settings.siliconflow_api_key = (
        siliconflow_cfg.get('api_key')
        or env.get('SILICONFLOW_API_KEY')
        or env.get('AI4LAW_SILICONFLOW_API_KEY')
    )
    settings.siliconflow_api_url = (
        siliconflow_cfg.get('api_url')
        or env.get('SILICONFLOW_API_URL')
        or 'https://api.siliconflow.cn/v1'
    )
    settings.siliconflow_model = (
        siliconflow_cfg.get('model')
        or env.get('SILICONFLOW_MODEL')
        or 'deepseek-ai/DeepSeek-V3.2'
    )
    settings.tencent_api_key = (
        tencent_cfg.get('api_key')
        or env.get('TENCENT_API_KEY')
        or env.get('AI4LAW_TENCENT_API_KEY')
    )
    settings.tencent_api_url = (
        tencent_cfg.get('api_url')
        or env.get('TENCENT_API_URL')
        or 'https://api.hunyuan.cloud.tencent.com/v1'
    )
    settings.tencent_model = (
        tencent_cfg.get('model')
        or env.get('TENCENT_MODEL')
        or 'hy3-preview'
    )
    settings.llm_provider = 'auto'
    settings._runtime_llm_providers = [
        {
            'id': 'siliconflow',
            'name': 'SiliconFlow',
            'provider_type': 'openai_compatible',
            'api_url': settings.siliconflow_api_url,
            'api_key': settings.siliconflow_api_key,
            'model': settings.siliconflow_model,
            'enabled': bool(settings.siliconflow_api_key),
            'timeout': 60,
        },
        {
            'id': 'tencent_hunyuan',
            'name': 'Tencent Hunyuan',
            'provider_type': 'openai_compatible',
            'api_url': settings.tencent_api_url,
            'api_key': settings.tencent_api_key,
            'model': settings.tencent_model,
            'enabled': bool(settings.tencent_api_key),
            'timeout': 60,
        },
    ]
    settings._runtime_llm_active_provider_id = provider_id
    for item in settings._runtime_llm_providers:
        if item['id'] == provider_id:
            item['model'] = model
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    return settings


def sum_trace_usage(trace_dir: Path) -> dict[str, Any]:
    prompt = 0
    completion = 0
    total = 0
    calls = 0
    llm_files: list[str] = []
    for path in sorted(trace_dir.glob('*.json')):
        if path.name == 'manifest.json':
            continue
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        detail = ((payload.get('payload') or {}).get('detail') or {}) if isinstance(payload, dict) else {}
        if detail.get('tool') != 'llm_chat':
            continue
        usage = detail.get('usage') or {}
        if not usage:
            continue
        calls += 1
        prompt += int(usage.get('prompt_tokens') or 0)
        completion += int(usage.get('completion_tokens') or 0)
        total += int(usage.get('total_tokens') or 0)
        llm_files.append(path.name)
    return {
        'prompt_tokens': prompt,
        'completion_tokens': completion,
        'total_tokens': total,
        'llm_calls': calls,
        'llm_files': llm_files,
    }


def run_diagnosis(settings: Settings, provider_id: str, model: str) -> dict[str, Any]:
    task_id = f'{provider_id}_diagnosis'
    trace_dir = settings.storage_dir / 'traces' / f'diagnosis_{task_id}'
    trace = TraceRecorder(trace_dir=trace_dir, task_id=task_id)
    token = current_trace.set(trace)
    try:
        service = DiagnosisService()
        service._llm_client = service._llm_client.__class__(settings)
        service.agents = service.agents = __import__('backend.modules.diagnosis.agents', fromlist=['create_diag_agents']).create_diag_agents(service._llm_client)
        renderer = DiagnosisReportRenderer(llm_client=service._llm_client)
        answers = DiagnosisAnswers(
            q1_is_ciio='no',
            q2_has_important_data='no',
            q3_pii_count=450000,
            q4_spi_count=0,
            q5_no_personal_info='no',
            q6_scenario='other',
            q7_receiver_type='third_party',
            q8_purpose='将过去半年的订单数据同步至位于新加坡的亚太数据中心，用于优化区域物流算法和精准营销',
            m1_enterprise_name='跨境优品',
            m1_industry='跨境电商',
            m3_processes_personal_info='yes',
            m3_personal_info_types=['用户姓名', '收货地址', '联系电话', '商品订单号', '购买时间', '商品金额', '支付渠道编号'],
            m3_sensitive_info_types=[],
            m3_processes_important_data='no',
            m3_important_data_types=[],
            m3_data_volume_range='10-100万条',
            m4_cross_border_transfer='yes',
            m4_cross_border_regions='新加坡',
            m4_share_to_third_party='yes',
            m4_entrusted_processing='yes',
        )
        result = service.evaluate(answers)
        outputs = renderer.render('跨境优品', answers, result)
        trace.write_manifest()
        usage = sum_trace_usage(trace_dir)
        return {
            'module': 'diagnosis',
            'provider_id': provider_id,
            'model': model,
            'success': True,
            'trace_dir': str(trace_dir),
            'outputs': {k: str(v) for k, v in outputs.items()},
            'recommended_path': result.recommended_path,
            **usage,
        }
    finally:
        current_trace.reset(token)
        finalize_run(None)


def run_assessment(settings: Settings, provider_id: str, model: str) -> dict[str, Any]:
    llm_client = LLMClient(settings)
    legal_service = DeliLegalService(settings)
    service = AssessmentService(llm_client=llm_client, legal_api_service=legal_service)
    service.generator.llm = llm_client
    service.renderer.llm_client = llm_client
    service.diagnosis_service._llm_client = llm_client
    service.diagnosis_service.agents = __import__('backend.modules.diagnosis.agents', fromlist=['create_diag_agents']).create_diag_agents(service.diagnosis_service._llm_client)
    payload = AssessmentRequest.model_validate({
        'company_name': 'AT618333',
        'industry': '互联网SaaS',
        'is_ciio': False,
        'contains_important_data': False,
        'pii_count': 50000,
        'spi_count': 500,
        'transfer_purpose': '全球客服与风控联防',
        'receiver_country': '新加坡',
        'force_override_path': False,
        'uploaded_files': [],
        'path_check_mode': 'warn_only',
        'self_assessment_info': None,
        'data_inventory_items': [],
        'recipient_info': None,
        'downstream_processors': [],
        'legal_document_review': None,
        'security_capability': None,
        'compliance_history': None,
        'personal_info_protection': None,
        'system_link': None,
    })
    task_id = f'{provider_id}_assessment'
    result = service.generate_report(payload, task_id=task_id)
    trace_dir = settings.storage_dir / 'traces' / f'assessment_{task_id}'
    usage = sum_trace_usage(trace_dir)
    return {
        'module': 'assessment',
        'provider_id': provider_id,
        'model': model,
        'success': True,
        'trace_dir': str(trace_dir),
        'outputs': result.output_files,
        'report_path': result.report_path,
        **usage,
    }


def run_pipia(settings: Settings, provider_id: str, model: str) -> dict[str, Any]:
    attachment_path = settings.upload_dir / f'{provider_id}_pipia_evidence.txt'
    attachment_path.parent.mkdir(parents=True, exist_ok=True)
    attachment_path.write_text('标准合同条款示例，用于跨境客服与风控场景。', encoding='utf-8')
    service = PIPIAService(llm_client=LLMClient(settings))
    payload = PIPIARequest.model_validate({
        'route_type': 'scc_filing',
        'company_profile': {
            'company_name': '华东云链科技（测试）',
            'company_uscc': '91310000XXXXXXXXXX',
            'is_ciio': False,
            'processing_person_count': 380000,
            'outbound_pi_count': 380000,
            'outbound_spi_count': 9000,
            'industry': '跨境电商SaaS',
        },
        'transfer_context': {
            'purpose': '为境外客服中心和风控团队提供必要数据支持；场景：跨境客服与数据分析；频率：日批量+实时工单触发；方式：API接口周期同步；业务概况：跨境电商SaaS；处理活动：订单履约、客服工单、风控审查',
            'recipient_name': 'OceanStar Technology Pte. Ltd.',
            'recipient_country_region': '新加坡',
            'legal_basis': '履行合同+用户授权同意；合法性论证：已在隐私政策与业务条款中披露必要出境场景；必要性论证：境外客服能力由集团统一调度，境内无法完全替代',
        },
        'personal_info_scope': {
            'pi_categories': ['姓名', '联系方式', '订单信息', '客服工单信息', '风控审查信息'],
            'spi_categories': ['身份认证信息'],
            'subject_volume': 380000,
        },
        'rights_protection': {
            'notice_mechanism': '隐私政策+业务条款',
            'consent_mechanism': '单独同意',
            'dsar_channel': 'privacy@example.com',
            'retention_policy': '到期删除+最短必要',
        },
        'emergency_plan': {
            'incident_response_sla_hours': 24,
            'escalation_path': 'DPO -> 法务 -> 管理层',
        },
        'attachments': [
            {
                'file_role': 'scc_contract',
                'file_name': attachment_path.name,
                'file_format': 'txt',
                'storage_uri': str(attachment_path),
            }
        ],
    })
    task_id = f'{provider_id}_pipia'
    result = service.generate_report(payload, task_id=task_id)
    trace_dir = settings.storage_dir / 'traces' / f'pipia_{task_id}'
    usage = sum_trace_usage(trace_dir)
    return {
        'module': 'pipia',
        'provider_id': provider_id,
        'model': model,
        'success': True,
        'trace_dir': str(trace_dir),
        'outputs': result.output_files,
        'report_path': result.report_path,
        **usage,
    }


def safe_run(label: str, fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {
            'module': label,
            'success': False,
            'error': f'{exc.__class__.__name__}: {exc}',
        }


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        '# 中国模块 Token 实测对比',
        '',
        '| 模块 | Provider | Model | Prompt Tokens | Completion Tokens | Total Tokens | LLM Calls | 是否成功 | 备注 |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |',
    ]
    for row in results:
        note = row.get('error') or row.get('recommended_path') or ''
        lines.append(
            f"| {row.get('module','')} | {row.get('provider_id','')} | {row.get('model','')} | {row.get('prompt_tokens',0)} | {row.get('completion_tokens',0)} | {row.get('total_tokens',0)} | {row.get('llm_calls',0)} | {'PASS' if row.get('success') else 'FAIL'} | {note} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main() -> None:
    if RUN_ROOT.exists():
        (RUN_ROOT / 'storage').mkdir(parents=True, exist_ok=True)
    matrix = [
        ('siliconflow', 'deepseek-ai/DeepSeek-V3.2'),
        ('tencent_hunyuan', 'hunyuan-lite'),
    ]
    all_results: list[dict[str, Any]] = []
    for provider_id, model in matrix:
        settings = build_settings(provider_id, model)
        provider_run_root = RUN_ROOT / f"{provider_id}__{model.replace('/', '_')}"
        if provider_run_root.exists():
            shutil.rmtree(provider_run_root)
        provider_run_root.mkdir(parents=True, exist_ok=True)
        settings.storage_dir = provider_run_root / 'storage'
        settings.upload_dir_name = 'uploads'
        settings.report_dir_name = 'reports'
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.report_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(ROOT)
        # Warm RAG index once in this provider context.
        _ = retrieve_regulations('中国 数据出境 个人信息 重要数据', top_k=1, jurisdiction='cn', path='assessment')
        all_results.append(safe_run('diagnosis', lambda: run_diagnosis(settings, provider_id, model)))
        all_results.append(safe_run('assessment', lambda: run_assessment(settings, provider_id, model)))
        all_results.append(safe_run('pipia', lambda: run_pipia(settings, provider_id, model)))

    RESULT_JSON.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding='utf-8')
    RESULT_MD.write_text(render_markdown(all_results), encoding='utf-8')
    print(str(RESULT_JSON))
    print(str(RESULT_MD))
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
