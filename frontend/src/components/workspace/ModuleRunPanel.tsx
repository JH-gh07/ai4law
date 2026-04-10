import { useEffect, useMemo, useState } from "react";
import type { ModuleKey, RunMode, TaskSpace } from "../../lib/domain";
import {
  findModule,
  getDefaultPayload,
  hasAsync,
  listModules,
  runModule,
  uploadTaskFile
} from "../../lib/module-adapter";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";

export type RunOutput = {
  module: ModuleKey;
  runMode: RunMode;
  request: unknown;
  response?: unknown;
  success: boolean;
  error?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

type ModuleRunPanelProps = {
  onRunDone: (output: RunOutput) => void;
  taskSpace: TaskSpace;
};

type DiagnosisSelectValue =
  | "yes"
  | "no"
  | "unknown"
  | "contract_performance"
  | "hr_management"
  | "emergency"
  | "legal_duty"
  | "other"
  | "intra_group"
  | "third_party";

type DiagnosisFieldType = "text" | "textarea" | "number" | "select";

type DiagnosisFieldConfig = {
  name: keyof DiagnosisFormValues;
  label: string;
  type: DiagnosisFieldType;
  options?: Array<{ value: DiagnosisSelectValue; label: string }>;
  min?: number;
  step?: number;
};

type DiagnosisStepConfig = {
  title: string;
  fields: DiagnosisFieldConfig[];
};

type DiagnosisFormValues = {
  company_name: string;
  q5_no_personal_info: "yes" | "no" | "unknown";
  q6_scenario: "contract_performance" | "hr_management" | "emergency" | "legal_duty" | "other";
  q7_receiver_type: "intra_group" | "third_party";
  q1_is_ciio: "yes" | "no" | "unknown";
  q2_has_important_data: "yes" | "no" | "unknown";
  q3_pii_count: number;
  q4_spi_count: number;
  q8_purpose: string;
};

type AssessmentFieldType = "text" | "textarea" | "number" | "checkbox";

type AssessmentFieldConfig = {
  name: keyof AssessmentFormValues;
  label: string;
  type: AssessmentFieldType;
  min?: number;
  step?: number;
};

type AssessmentStepConfig = {
  title: string;
  fields: AssessmentFieldConfig[];
};

type AssessmentFormValues = {
  company_name: string;
  industry: string;
  receiver_country: string;
  is_ciio: boolean;
  contains_important_data: boolean;
  pii_count: number;
  spi_count: number;
  transfer_purpose: string;
  force_override_path: boolean;
};

type PipiaRouteType = "scc_filing" | "certification";
type PipiaAttachmentRole = "scc_contract" | "certification_material" | "internal_policy" | "supporting_evidence";

type PipiaFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

type PipiaFieldConfig = {
  name: keyof PipiaFormValues;
  label: string;
  type: PipiaFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

type PipiaStepConfig = {
  title: string;
  fields: PipiaFieldConfig[];
};

type PipiaFormValues = {
  company_name: string;
  company_uscc: string;
  industry: string;
  is_ciio: boolean;
  processing_person_count: number;
  outbound_pi_count: number;
  outbound_spi_count: number;
  route_type: PipiaRouteType;
  purpose: string;
  recipient_name: string;
  recipient_country_region: string;
  legal_basis: string;
  pi_categories: string;
  spi_categories: string;
  subject_volume: number;
  notice_mechanism: string;
  consent_mechanism: string;
  dsar_channel: string;
  retention_policy: string;
  incident_response_sla_hours: number;
  escalation_path: string;
  attachment_role: PipiaAttachmentRole;
};

const JURISDICTIONS = ["CN", "EU", "US"] as const;

const DIAGNOSIS_STEPS: DiagnosisStepConfig[] = [
  {
    title: "基础识别",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      {
        name: "q5_no_personal_info",
        label: "Q1 本次出境数据是否完全不含个人信息和重要数据？",
        type: "select",
        options: [
          { value: "no", label: "否（含个人信息或重要数据）" },
          { value: "yes", label: "是（纯业务/技术数据）" },
          { value: "unknown", label: "不确定" }
        ]
      },
      {
        name: "q6_scenario",
        label: "Q2 本次数据出境的主要业务场景",
        type: "select",
        options: [
          { value: "other", label: "其他商业目的" },
          { value: "contract_performance", label: "履行合同 / 向消费者提供服务" },
          { value: "hr_management", label: "跨国公司内部人力资源管理" },
          { value: "emergency", label: "紧急情况保护自然人生命、健康或财产安全" },
          { value: "legal_duty", label: "依法履行法定职责或法定义务" }
        ]
      },
      {
        name: "q7_receiver_type",
        label: "Q3 境外数据接收方类型",
        type: "select",
        options: [
          { value: "third_party", label: "独立第三方（合作伙伴 / 服务商）" },
          { value: "intra_group", label: "集团内部关联公司" }
        ]
      }
    ]
  },
  {
    title: "强制路径触发项",
    fields: [
      {
        name: "q1_is_ciio",
        label: "Q4 是否为关键信息基础设施运营者（CIIO）？",
        type: "select",
        options: [
          { value: "no", label: "否" },
          { value: "yes", label: "是" },
          { value: "unknown", label: "不确定" }
        ]
      },
      {
        name: "q2_has_important_data",
        label: "Q5 出境数据是否包含重要数据？",
        type: "select",
        options: [
          { value: "no", label: "否" },
          { value: "yes", label: "是" },
          { value: "unknown", label: "不确定" }
        ]
      },
      { name: "q3_pii_count", label: "Q6 近12个月累计向境外提供个人信息的人数", type: "number", min: 0, step: 1000 },
      { name: "q4_spi_count", label: "Q7 近12个月累计向境外提供敏感个人信息的人数", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "补充说明",
    fields: [
      { name: "q8_purpose", label: "Q8 出境目的简述（可选）", type: "textarea" }
    ]
  }
];

const ASSESSMENT_STEPS: AssessmentStepConfig[] = [
  {
    title: "企业基本信息",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "industry", label: "行业", type: "text" },
      { name: "receiver_country", label: "接收方国家", type: "text" }
    ]
  },
  {
    title: "数据出境特征",
    fields: [
      { name: "is_ciio", label: "是否 CIIO", type: "checkbox" },
      { name: "contains_important_data", label: "是否涉及重要数据", type: "checkbox" },
      { name: "pii_count", label: "普通个人信息量", type: "number", min: 0, step: 1000 },
      { name: "spi_count", label: "敏感个人信息量", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "传输目的与材料",
    fields: [
      { name: "transfer_purpose", label: "出境目的", type: "textarea" },
      { name: "force_override_path", label: "允许路径不一致时继续生成", type: "checkbox" }
    ]
  }
];

const PIPIA_STEPS: PipiaStepConfig[] = [
  {
    title: "企业基本信息",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "company_uscc", label: "统一社会信用代码", type: "text" },
      { name: "industry", label: "行业", type: "text" },
      { name: "is_ciio", label: "是否 CIIO", type: "checkbox" },
      { name: "processing_person_count", label: "处理个人信息规模", type: "number", min: 0, step: 1000 },
      { name: "outbound_pi_count", label: "出境普通个人信息规模", type: "number", min: 0, step: 1000 },
      { name: "outbound_spi_count", label: "出境敏感个人信息规模", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "出境场景与范围",
    fields: [
      { name: "route_type", label: "路径类型", type: "select", options: ["scc_filing", "certification"] },
      { name: "purpose", label: "出境目的", type: "textarea" },
      { name: "recipient_name", label: "境外接收方", type: "text" },
      { name: "recipient_country_region", label: "接收方国家/地区", type: "text" },
      { name: "legal_basis", label: "处理合法性基础", type: "text" },
      { name: "pi_categories", label: "普通个人信息类别（逗号分隔）", type: "text" },
      { name: "spi_categories", label: "敏感个人信息类别（逗号分隔）", type: "text" },
      { name: "subject_volume", label: "数据主体规模", type: "number", min: 0, step: 1000 }
    ]
  },
  {
    title: "权利保障与应急",
    fields: [
      { name: "notice_mechanism", label: "告知机制", type: "textarea" },
      { name: "consent_mechanism", label: "同意机制", type: "text" },
      { name: "dsar_channel", label: "权利请求渠道", type: "text" },
      { name: "retention_policy", label: "保存与删除策略", type: "textarea" },
      { name: "incident_response_sla_hours", label: "事件响应SLA（小时）", type: "number", min: 1, step: 1 },
      { name: "escalation_path", label: "升级路径", type: "text" },
      {
        name: "attachment_role",
        label: "附件角色",
        type: "select",
        options: ["scc_contract", "certification_material", "internal_policy", "supporting_evidence"]
      }
    ]
  }
];

const asRecord = (value: unknown): Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const toString = (value: unknown, fallback = ""): string => (typeof value === "string" ? value : fallback);
const toNumber = (value: unknown, fallback = 0): number =>
  typeof value === "number" && Number.isFinite(value) ? value : fallback;
const toBoolean = (value: unknown, fallback = false): boolean => (typeof value === "boolean" ? value : fallback);

const toRouteType = (value: unknown): PipiaRouteType =>
  value === "certification" ? "certification" : "scc_filing";

const toAttachmentRole = (value: unknown): PipiaAttachmentRole => {
  if (value === "certification_material") return "certification_material";
  if (value === "internal_policy") return "internal_policy";
  if (value === "supporting_evidence") return "supporting_evidence";
  return "scc_contract";
};

const splitCsv = (value: string): string[] =>
  value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

const basenameFromPath = (path: string): string => {
  const normalized = path.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || "attachment.txt";
};

const inferAttachmentFormat = (value: string): "doc" | "docx" | "pdf" | "txt" | "md" | "json" | "csv" => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "doc") return "doc";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "md") return "md";
  if (suffix === "json") return "json";
  if (suffix === "csv") return "csv";
  return "txt";
};

const createDefaultAssessmentValues = (): AssessmentFormValues => {
  const demo = asRecord(getDefaultPayload("assessment"));
  return {
    company_name: toString(demo.company_name, ""),
    industry: toString(demo.industry, ""),
    receiver_country: toString(demo.receiver_country, ""),
    is_ciio: toBoolean(demo.is_ciio, false),
    contains_important_data: toBoolean(demo.contains_important_data, false),
    pii_count: toNumber(demo.pii_count, 0),
    spi_count: toNumber(demo.spi_count, 0),
    transfer_purpose: toString(demo.transfer_purpose, ""),
    force_override_path: toBoolean(demo.force_override_path, true)
  };
};

const createDefaultDiagnosisValues = (): DiagnosisFormValues => {
  const demo = asRecord(getDefaultPayload("diagnosis"));
  const answers = asRecord(demo.answers);
  return {
    company_name: toString(demo.company_name, ""),
    q5_no_personal_info:
      answers.q5_no_personal_info === "yes" || answers.q5_no_personal_info === "unknown"
        ? answers.q5_no_personal_info
        : "no",
    q6_scenario:
      answers.q6_scenario === "contract_performance" ||
      answers.q6_scenario === "hr_management" ||
      answers.q6_scenario === "emergency" ||
      answers.q6_scenario === "legal_duty"
        ? answers.q6_scenario
        : "other",
    q7_receiver_type: answers.q7_receiver_type === "intra_group" ? "intra_group" : "third_party",
    q1_is_ciio: answers.q1_is_ciio === "yes" || answers.q1_is_ciio === "unknown" ? answers.q1_is_ciio : "no",
    q2_has_important_data:
      answers.q2_has_important_data === "yes" || answers.q2_has_important_data === "unknown"
        ? answers.q2_has_important_data
        : "no",
    q3_pii_count: toNumber(answers.q3_pii_count, 0),
    q4_spi_count: toNumber(answers.q4_spi_count, 0),
    q8_purpose: toString(answers.q8_purpose, "")
  };
};

const createDefaultPipiaValues = (): PipiaFormValues => {
  const demo = asRecord(getDefaultPayload("pipia"));
  const companyProfile = asRecord(demo.company_profile);
  const transferContext = asRecord(demo.transfer_context);
  const personalInfoScope = asRecord(demo.personal_info_scope);
  const rightsProtection = asRecord(demo.rights_protection);
  const emergencyPlan = asRecord(demo.emergency_plan);
  const firstAttachment =
    Array.isArray(demo.attachments) && demo.attachments.length > 0
      ? asRecord(demo.attachments[0])
      : {};

  return {
    company_name: toString(companyProfile.company_name, ""),
    company_uscc: toString(companyProfile.company_uscc, ""),
    industry: toString(companyProfile.industry, ""),
    is_ciio: toBoolean(companyProfile.is_ciio, false),
    processing_person_count: toNumber(companyProfile.processing_person_count, 0),
    outbound_pi_count: toNumber(companyProfile.outbound_pi_count, 0),
    outbound_spi_count: toNumber(companyProfile.outbound_spi_count, 0),
    route_type: toRouteType(demo.route_type),
    purpose: toString(transferContext.purpose, ""),
    recipient_name: toString(transferContext.recipient_name, ""),
    recipient_country_region: toString(transferContext.recipient_country_region, ""),
    legal_basis: toString(transferContext.legal_basis, ""),
    pi_categories: Array.isArray(personalInfoScope.pi_categories)
      ? personalInfoScope.pi_categories.filter((item): item is string => typeof item === "string").join(",")
      : "",
    spi_categories: Array.isArray(personalInfoScope.spi_categories)
      ? personalInfoScope.spi_categories.filter((item): item is string => typeof item === "string").join(",")
      : "",
    subject_volume: toNumber(personalInfoScope.subject_volume, 0),
    notice_mechanism: toString(rightsProtection.notice_mechanism, ""),
    consent_mechanism: toString(rightsProtection.consent_mechanism, ""),
    dsar_channel: toString(rightsProtection.dsar_channel, ""),
    retention_policy: toString(rightsProtection.retention_policy, ""),
    incident_response_sla_hours: toNumber(emergencyPlan.incident_response_sla_hours, 24),
    escalation_path: toString(emergencyPlan.escalation_path, ""),
    attachment_role: toAttachmentRole(firstAttachment.file_role)
  };
};

const readDefaultPipiaAttachment = (): { path: string; role: PipiaAttachmentRole } | null => {
  const demo = asRecord(getDefaultPayload("pipia"));
  if (!Array.isArray(demo.attachments) || demo.attachments.length === 0) return null;
  const first = asRecord(demo.attachments[0]);
  const path = toString(first.storage_uri, "");
  if (!path) return null;
  return {
    path,
    role: toAttachmentRole(first.file_role)
  };
};

export function ModuleRunPanel({ onRunDone, taskSpace }: ModuleRunPanelProps) {
  const { t, lang } = useLang();
  const [jurisdiction, setJurisdiction] = useState<(typeof JURISDICTIONS)[number]>(taskSpace.jurisdiction);
  const [moduleKey, setModuleKey] = useState<ModuleKey>(taskSpace.module);
  const [runMode, setRunMode] = useState<RunMode>("sync");
  const [payloadText, setPayloadText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnosisStepIndex, setDiagnosisStepIndex] = useState(0);
  const [diagnosisValues, setDiagnosisValues] = useState<DiagnosisFormValues>(createDefaultDiagnosisValues);
  const [assessmentStepIndex, setAssessmentStepIndex] = useState(0);
  const [assessmentValues, setAssessmentValues] = useState<AssessmentFormValues>(createDefaultAssessmentValues);
  const [assessmentFiles, setAssessmentFiles] = useState<File[]>([]);
  const [pipiaStepIndex, setPipiaStepIndex] = useState(0);
  const [pipiaValues, setPipiaValues] = useState<PipiaFormValues>(createDefaultPipiaValues);
  const [pipiaFiles, setPipiaFiles] = useState<File[]>([]);

  const taskTemplate = findTaskTemplate(taskSpace.taskTemplateId);
  const templateModule = useMemo(
    () => listModules().find((item) => item.key === taskSpace.module),
    [taskSpace.module]
  );
  const lockedModule = !!taskTemplate && !!templateModule;

  const modules = useMemo(() => {
    if (lockedModule && templateModule) {
      return [templateModule];
    }
    return listModules().filter((item) => item.jurisdiction === jurisdiction);
  }, [jurisdiction, lockedModule, templateModule]);

  useEffect(() => {
    setJurisdiction(taskSpace.jurisdiction);
    setModuleKey(taskSpace.module);
  }, [taskSpace.jurisdiction, taskSpace.module]);

  useEffect(() => {
    if (!modules.find((item) => item.key === moduleKey)) {
      setModuleKey(modules[0]?.key ?? "diagnosis");
    }
  }, [moduleKey, modules]);

  useEffect(() => {
    setPayloadText(JSON.stringify(getDefaultPayload(moduleKey), null, 2));
    setResponseText("");
    setError(null);
    if (moduleKey === "diagnosis") {
      setDiagnosisStepIndex(0);
      setDiagnosisValues(createDefaultDiagnosisValues());
    }
    if (moduleKey === "assessment") {
      setAssessmentStepIndex(0);
      setAssessmentValues(createDefaultAssessmentValues());
      setAssessmentFiles([]);
    }
    if (moduleKey === "pipia") {
      setPipiaStepIndex(0);
      setPipiaValues(createDefaultPipiaValues());
      setPipiaFiles([]);
    }
  }, [moduleKey]);

  const definition = findModule(moduleKey);
  const allowAsync = hasAsync(definition);
  const isDiagnosisModule = moduleKey === "diagnosis";
  const isAssessmentModule = moduleKey === "assessment";
  const isPipiaModule = moduleKey === "pipia";

  const updateDiagnosisValue = <K extends keyof DiagnosisFormValues>(name: K, value: DiagnosisFormValues[K]) => {
    setDiagnosisValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateAssessmentValue = <K extends keyof AssessmentFormValues>(name: K, value: AssessmentFormValues[K]) => {
    setAssessmentValues((prev) => ({ ...prev, [name]: value }));
  };

  const updatePipiaValue = <K extends keyof PipiaFormValues>(name: K, value: PipiaFormValues[K]) => {
    setPipiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const uploadFiles = async (files: File[]): Promise<string[]> => {
    if (files.length === 0) return [];
    const uploadedPaths: string[] = [];
    for (const file of files) {
      const uploaded = await uploadTaskFile(file);
      uploadedPaths.push(uploaded.path);
    }
    return uploadedPaths;
  };

  const buildAssessmentPayload = async (): Promise<unknown> => {
    const uploadedFiles = await uploadFiles(assessmentFiles);
    return {
      ...assessmentValues,
      uploaded_files: uploadedFiles
    };
  };

  const buildPipiaPayload = async (): Promise<unknown> => {
    const uploadedFiles = await uploadFiles(pipiaFiles);
    const uploadedAttachments = uploadedFiles.map((path) => ({
      file_role: pipiaValues.attachment_role,
      file_name: basenameFromPath(path),
      file_format: inferAttachmentFormat(path),
      storage_uri: path
    }));

    const fallback = readDefaultPipiaAttachment();
    const attachments =
      uploadedAttachments.length > 0
        ? uploadedAttachments
        : fallback
          ? [
              {
                file_role: fallback.role,
                file_name: basenameFromPath(fallback.path),
                file_format: inferAttachmentFormat(fallback.path),
                storage_uri: fallback.path
              }
            ]
          : [
              {
                file_role: pipiaValues.attachment_role,
                file_name: "manual_note.txt",
                file_format: "txt" as const,
                storage_uri: "storage/uploads/manual_note.txt"
              }
            ];

    return {
      route_type: pipiaValues.route_type,
      company_profile: {
        company_name: pipiaValues.company_name,
        company_uscc: pipiaValues.company_uscc,
        is_ciio: pipiaValues.is_ciio,
        processing_person_count: pipiaValues.processing_person_count,
        outbound_pi_count: pipiaValues.outbound_pi_count,
        outbound_spi_count: pipiaValues.outbound_spi_count,
        industry: pipiaValues.industry
      },
      transfer_context: {
        purpose: pipiaValues.purpose,
        recipient_name: pipiaValues.recipient_name,
        recipient_country_region: pipiaValues.recipient_country_region,
        legal_basis: pipiaValues.legal_basis
      },
      personal_info_scope: {
        pi_categories: splitCsv(pipiaValues.pi_categories).length > 0 ? splitCsv(pipiaValues.pi_categories) : ["账户信息"],
        spi_categories: splitCsv(pipiaValues.spi_categories),
        subject_volume: pipiaValues.subject_volume
      },
      rights_protection: {
        notice_mechanism: pipiaValues.notice_mechanism,
        consent_mechanism: pipiaValues.consent_mechanism,
        dsar_channel: pipiaValues.dsar_channel,
        retention_policy: pipiaValues.retention_policy
      },
      emergency_plan: {
        incident_response_sla_hours: pipiaValues.incident_response_sla_hours,
        escalation_path: pipiaValues.escalation_path
      },
      attachments
    };
  };

  const buildDiagnosisPayload = (): unknown => ({
    company_name: diagnosisValues.company_name,
    answers: {
      q1_is_ciio: diagnosisValues.q1_is_ciio,
      q2_has_important_data: diagnosisValues.q2_has_important_data,
      q3_pii_count: diagnosisValues.q3_pii_count,
      q4_spi_count: diagnosisValues.q4_spi_count,
      q5_no_personal_info: diagnosisValues.q5_no_personal_info,
      q6_scenario: diagnosisValues.q6_scenario,
      q7_receiver_type: diagnosisValues.q7_receiver_type,
      q8_purpose: diagnosisValues.q8_purpose
    }
  });

  const execute = async () => {
    let requestPayload: unknown;
    try {
      if (isDiagnosisModule) {
        requestPayload = buildDiagnosisPayload();
      } else if (isAssessmentModule) {
        requestPayload = await buildAssessmentPayload();
      } else if (isPipiaModule) {
        requestPayload = await buildPipiaPayload();
      } else {
        requestPayload = JSON.parse(payloadText);
      }
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Payload parse error";
      setError(message);
      onRunDone({
        module: moduleKey,
        runMode,
        request: isDiagnosisModule
          ? diagnosisValues
          : isAssessmentModule
            ? assessmentValues
            : isPipiaModule
              ? pipiaValues
              : payloadText,
        success: false,
        error: message
      });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await runModule(definition, requestPayload, allowAsync ? runMode : "sync");
      setResponseText(JSON.stringify(result.response, null, 2));
      onRunDone({
        module: moduleKey,
        runMode: result.runMode,
        request: requestPayload,
        response: result.response,
        success: true,
        asyncTaskId: result.asyncTaskId,
        asyncState: result.asyncState
      });
    } catch (runErr) {
      const message = runErr instanceof Error ? runErr.message : "Request failed";
      setError(message);
      onRunDone({ module: moduleKey, runMode, request: requestPayload, success: false, error: message });
    } finally {
      setLoading(false);
    }
  };

  const currentAssessmentStep = ASSESSMENT_STEPS[assessmentStepIndex];
  const assessmentProgress = Math.round(((assessmentStepIndex + 1) / ASSESSMENT_STEPS.length) * 100);
  const currentDiagnosisStep = DIAGNOSIS_STEPS[diagnosisStepIndex];
  const diagnosisProgress = Math.round(((diagnosisStepIndex + 1) / DIAGNOSIS_STEPS.length) * 100);
  const currentPipiaStep = PIPIA_STEPS[pipiaStepIndex];
  const pipiaProgress = Math.round(((pipiaStepIndex + 1) / PIPIA_STEPS.length) * 100);

  return (
    <section className="run-panel" data-guide="stage-run">
      <header className="run-panel-head">
        <div>
          <div className="runner-title">{t("runPanel")}</div>
          <h3 className="font-display text-xl text-ink">{definition.label}</h3>
          {taskTemplate ? (
            <p className="run-panel-template-hint">
              {getTaskTemplateTitle(taskTemplate, lang)}
            </p>
          ) : null}
        </div>
        <div className="run-mode-group">
          <button
            className={`pill-btn ${runMode === "sync" ? "active-mode" : ""}`}
            onClick={() => setRunMode("sync")}
          >
            {t("runSync")}
          </button>
          <button
            className={`pill-btn ${runMode === "async" ? "active-mode" : ""}`}
            onClick={() => setRunMode("async")}
            disabled={!allowAsync}
          >
            {t("runAsync")}
          </button>
        </div>
      </header>

      {!lockedModule ? (
        <div className="jurisdiction-tabs">
          {JURISDICTIONS.map((item) => (
            <button
              key={item}
              className={`tab-btn ${item === jurisdiction ? "active" : ""}`}
              onClick={() => setJurisdiction(item)}
            >
              {item}
            </button>
          ))}
        </div>
      ) : null}

      {!lockedModule ? (
        <div className="module-tabs">
          {modules.map((item) => (
            <button
              key={item.key}
              className={`tab-btn ${item.key === moduleKey ? "active" : ""}`}
              onClick={() => setModuleKey(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="module-lock-line">
          {t("runLockedModule")}
          {" "}
          <strong>{definition.label}</strong>
        </div>
      )}

      {isDiagnosisModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">Diagnosis Wizard</div>
            <span>{diagnosisProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DIAGNOSIS_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === diagnosisStepIndex ? "active" : ""}`}
                onClick={() => setDiagnosisStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentDiagnosisStep.title}</div>
          <div className="schema-field-grid">
            {currentDiagnosisStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(diagnosisValues[field.name])}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(diagnosisValues[field.name])}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(diagnosisValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateDiagnosisValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="field-wrap">
                  <span>{field.label}</span>
                  <select
                    value={String(diagnosisValues[field.name])}
                    onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                  >
                    {(field.options ?? []).map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              );
            })}
          </div>

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDiagnosisStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={diagnosisStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDiagnosisStepIndex((prev) => Math.min(DIAGNOSIS_STEPS.length - 1, prev + 1))}
              disabled={diagnosisStepIndex === DIAGNOSIS_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : isAssessmentModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">Assessment Wizard</div>
            <span>{assessmentProgress}%</span>
          </div>
          <div className="schema-stepper">
            {ASSESSMENT_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === assessmentStepIndex ? "active" : ""}`}
                onClick={() => setAssessmentStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentAssessmentStep.title}</div>
          <div className="schema-field-grid">
            {currentAssessmentStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(assessmentValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateAssessmentValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(assessmentValues[field.name])}
                    onChange={(event) => updateAssessmentValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {assessmentStepIndex === ASSESSMENT_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">附件上传</div>
              <input
                type="file"
                multiple
                onChange={(event) => setAssessmentFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {assessmentFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {assessmentFiles.length === 0 ? <p className="resource-empty">未选择附件（可为空）</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setAssessmentStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={assessmentStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setAssessmentStepIndex((prev) => Math.min(ASSESSMENT_STEPS.length - 1, prev + 1))}
              disabled={assessmentStepIndex === ASSESSMENT_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : isPipiaModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">PIPIA Wizard</div>
            <span>{pipiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {PIPIA_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === pipiaStepIndex ? "active" : ""}`}
                onClick={() => setPipiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentPipiaStep.title}</div>
          <div className="schema-field-grid">
            {currentPipiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(pipiaValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updatePipiaValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(pipiaValues[field.name])}
                    onChange={(event) => updatePipiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {pipiaStepIndex === PIPIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">附件上传</div>
              <input
                type="file"
                multiple
                onChange={(event) => setPipiaFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {pipiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {pipiaFiles.length === 0 ? <p className="resource-empty">未上传新附件，将使用默认附件配置。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setPipiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={pipiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setPipiaStepIndex((prev) => Math.min(PIPIA_STEPS.length - 1, prev + 1))}
              disabled={pipiaStepIndex === PIPIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : (
        <>
          <div className="runner-title">{t("payloadLabel")}</div>
          <textarea className="runner-textarea" value={payloadText} onChange={(event) => setPayloadText(event.target.value)} />
          <div className="mt-2 flex justify-end">
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </>
      )}

      <div className="runner-title mt-3">{t("responseLabel")}</div>
      <textarea className="runner-textarea" value={responseText} readOnly placeholder={t("runResultPlaceholder")} />

      {error ? <div className="runner-error">{error}</div> : null}
    </section>
  );
}
