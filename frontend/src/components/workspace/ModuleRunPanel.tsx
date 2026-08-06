import { useEffect, useMemo, useRef, useState } from "react";
import type { ModuleKey, RunMode, TaskSpace } from "../../lib/domain";
import {
  getModuleRunErrorCode,
  findModule,
  getDefaultPayload,
  hasAsync,
  listModules,
  runModule,
  uploadTaskFile
} from "../../api/modules";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";
import { DEV_ACCEL_ENABLED, getAssessmentDevPreset, getModuleDevPreset } from "../../lib/dev-presets";
import { getTestCases } from "../../lib/dev-test-cases";
import { fetchArtifactBlob } from "../../api/artifacts";
import {
  buildBcrPayload as createBcrPayload,
  buildAssessmentPayload as createAssessmentPayload,
  buildCnFlowPayload as createCnFlowPayload,
  buildCpraPayload as createCpraPayload,
  buildDiagnosisPayload as createDiagnosisPayload,
  buildDpiaPayload as createDpiaPayload,
  buildDocumentReviewPayload as createDocumentReviewPayload,
  buildEuSccPayload as createEuSccPayload,
  buildPipiaPayload as createPipiaPayload,
  buildTiaPayload as createTiaPayload,
  buildUs14117Payload as createUs14117Payload,
} from "../../features/module-runner/payload-builders";

import {
  ASSESSMENT_STEPS,
  BCR_STEPS,
  CN_FLOW_STEPS,
  CPRA_STEPS,
  DIAGNOSIS_STEPS,
  DIAGNOSIS_STEP_SHORT_TITLES,
  DPIA_STEPS,
  EU_SCC_STEPS,
  JURISDICTIONS,
  PIPIA_STEPS,
  REVIEW_ASYNC_STATE_LABEL,
  TIA_STEPS,
  US14117_STEPS,
  assertInput,
  basenameFromPath,
  buildAutoExtractResult,
  buildUserFacingResult,
  canInlinePreviewDocumentReviewExt,
  createDefaultAssessmentValues,
  createDefaultBcrValues,
  createDefaultCnFlowValues,
  createDefaultCpraValues,
  createDefaultDiagnosisValues,
  createDefaultDocumentReviewValues,
  createDefaultDpiaValues,
  createDefaultEuSccValues,
  createDefaultPipiaValues,
  createDefaultTiaValues,
  createDefaultUs14117Values,
  formatDocumentReviewFileDate,
  formatDocumentReviewFileSize,
  getDocumentReviewDocTypeLabel,
  getDocumentReviewExtractStatusMeta,
  getDocumentReviewFileExt,
  getDocumentReviewFileKey,
  getDocumentReviewTypeLabel,
  hasText,
  inferCnFlowAttachmentFormat,
  inferCpraAttachmentFormat,
  inferDocxPdfFormat,
  inferDpiaAttachmentFormat,
  isDocumentReviewImagePreviewExt,
  isDocumentReviewTextPreviewExt,
  isValidUrl,
  localizeFieldLabel,
  localizeOptionLabel,
  localizeStepTitle,
  seedDocumentReviewValuesForFile,
  splitCsv,
  toFileName,
  type AssessmentFormValues,
  type AsyncRunProgressState,
  type BcrFormValues,
  type CnFlowFormValues,
  type CpraFormValues,
  type DiagnosisFieldConfig,
  type DiagnosisFormValues,
  type DocumentReviewExtractState,
  type DocumentReviewFormValues,
  type DpiaFormValues,
  type EuSccFormValues,
  type PipiaFormValues,
  type TiaFormValues,
  type Us14117FieldConfig,
  type Us14117FormValues,
} from "../../features/module-runner/model";

export type RunOutput = {
  module: ModuleKey;
  runMode: RunMode;
  request: unknown;
  response?: unknown;
  success: boolean;
  error?: string;
  errorCode?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

type ModuleRunPanelProps = {
  onRunDone: (output: RunOutput) => void;
  taskSpace: TaskSpace;
  onTaskCreated?: (taskId: string, module: ModuleKey, request: unknown) => void;
};

export function ModuleRunPanel({ onRunDone, taskSpace, onTaskCreated }: ModuleRunPanelProps) {
  const { t, lang } = useLang();
  const diagnosisStepTopRef = useRef<HTMLDivElement | null>(null);
  const [jurisdiction, setJurisdiction] = useState<(typeof JURISDICTIONS)[number]>(taskSpace.jurisdiction);
  const [moduleKey, setModuleKey] = useState<ModuleKey>(taskSpace.module);
  const [payloadText, setPayloadText] = useState("");
  const [responseData, setResponseData] = useState<unknown>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [asyncRunProgress, setAsyncRunProgress] = useState<AsyncRunProgressState | null>(null);
  const [diagnosisStepIndex, setDiagnosisStepIndex] = useState(0);
  const [diagnosisValues, setDiagnosisValues] = useState<DiagnosisFormValues>(createDefaultDiagnosisValues);
  const [assessmentStepIndex, setAssessmentStepIndex] = useState(0);
  const [assessmentValues, setAssessmentValues] = useState<AssessmentFormValues>(createDefaultAssessmentValues);
  const [assessmentFiles, setAssessmentFiles] = useState<File[]>([]);
  const [assessmentDevFilePaths, setAssessmentDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getAssessmentDevPreset().backendFilePaths : []
  );
  const [pipiaStepIndex, setPipiaStepIndex] = useState(0);
  const [pipiaValues, setPipiaValues] = useState<PipiaFormValues>(createDefaultPipiaValues);
  const [pipiaFiles, setPipiaFiles] = useState<File[]>([]);
  const [pipiaDevFilePaths, setPipiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("pipia").backendFilePaths : []
  );
  const [documentReviewValues, setDocumentReviewValues] = useState<DocumentReviewFormValues>(createDefaultDocumentReviewValues);
  const [documentReviewFiles, setDocumentReviewFiles] = useState<File[]>([]);
  const [documentReviewDevFilePaths, setDocumentReviewDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("document_review").backendFilePaths : []
  );
  const [documentReviewSelectedFileIndex, setDocumentReviewSelectedFileIndex] = useState(0);
  const [documentReviewPreviewUrl, setDocumentReviewPreviewUrl] = useState<string | null>(null);
  const [documentReviewTextPreview, setDocumentReviewTextPreview] = useState("");
  const [documentReviewFileFormValues, setDocumentReviewFileFormValues] = useState<Record<string, DocumentReviewFormValues>>(
    {}
  );
  const [documentReviewExtractStates, setDocumentReviewExtractStates] = useState<Record<string, DocumentReviewExtractState>>(
    {}
  );
  const documentReviewParsedKeysRef = useRef<Set<string>>(new Set());
  const [euSccStepIndex, setEuSccStepIndex] = useState(0);
  const [euSccValues, setEuSccValues] = useState<EuSccFormValues>(createDefaultEuSccValues);
  const [euSccFiles, setEuSccFiles] = useState<File[]>([]);
  const [euSccDevFilePaths, setEuSccDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("eu_scc").backendFilePaths : []
  );
  const [bcrStepIndex, setBcrStepIndex] = useState(0);
  const [bcrValues, setBcrValues] = useState<BcrFormValues>(createDefaultBcrValues);
  const [bcrFiles, setBcrFiles] = useState<File[]>([]);
  const [bcrDevFilePaths, setBcrDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("bcr").backendFilePaths : []
  );
  const [dpiaStepIndex, setDpiaStepIndex] = useState(0);
  const [dpiaValues, setDpiaValues] = useState<DpiaFormValues>(createDefaultDpiaValues);
  const [dpiaFiles, setDpiaFiles] = useState<File[]>([]);
  const [dpiaDevFilePaths, setDpiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("dpia").backendFilePaths : []
  );
  const [tiaStepIndex, setTiaStepIndex] = useState(0);
  const [tiaValues, setTiaValues] = useState<TiaFormValues>(createDefaultTiaValues);
  const [tiaFiles, setTiaFiles] = useState<File[]>([]);
  const [tiaDevFilePaths, setTiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("tia").backendFilePaths : []
  );
  const [cnFlowStepIndex, setCnFlowStepIndex] = useState(0);
  const [cnFlowValues, setCnFlowValues] = useState<CnFlowFormValues>(createDefaultCnFlowValues);
  const [cnFlowDataInventoryFiles, setCnFlowDataInventoryFiles] = useState<File[]>([]);
  const [cnFlowEntityInventoryFiles, setCnFlowEntityInventoryFiles] = useState<File[]>([]);
  const [cnFlowSupportingFiles, setCnFlowSupportingFiles] = useState<File[]>([]);
  const [cnFlowDevFilePaths, setCnFlowDevFilePaths] = useState<string[]>([]);
  const [us14117StepIndex, setUs14117StepIndex] = useState(0);
  const [us14117Values, setUs14117Values] = useState<Us14117FormValues>(createDefaultUs14117Values);
  const [us14117Files, setUs14117Files] = useState<File[]>([]);
  const [cpraStepIndex, setCpraStepIndex] = useState(0);
  const [cpraValues, setCpraValues] = useState<CpraFormValues>(createDefaultCpraValues);
  const [cpraPrivacyPolicyFiles, setCpraPrivacyPolicyFiles] = useState<File[]>([]);
  const [cpraRightsSopFiles, setCpraRightsSopFiles] = useState<File[]>([]);
  const [cpraDataMapFiles, setCpraDataMapFiles] = useState<File[]>([]);
  const [cpraVendorListFiles, setCpraVendorListFiles] = useState<File[]>([]);
  const [cpraOtherFiles, setCpraOtherFiles] = useState<File[]>([]);

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

  const userFacingResult = useMemo(() => buildUserFacingResult(responseData, lang), [responseData, lang]);

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
    setResponseData(undefined);
    setError(null);
    if (moduleKey === "diagnosis") {
      setDiagnosisStepIndex(0);
      setDiagnosisValues(createDefaultDiagnosisValues());
    }
    if (moduleKey === "assessment") {
      setAssessmentStepIndex(0);
      setAssessmentValues(createDefaultAssessmentValues());
      setAssessmentFiles([]);
      setAssessmentDevFilePaths(DEV_ACCEL_ENABLED ? getAssessmentDevPreset().backendFilePaths : []);
    }
    if (moduleKey === "pipia") {
      setPipiaStepIndex(0);
      setPipiaValues(createDefaultPipiaValues());
      setPipiaFiles([]);
      setPipiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("pipia").backendFilePaths : []);
    }
    if (taskTemplate?.id === "cn_document_review") {
      setDocumentReviewValues(createDefaultDocumentReviewValues());
      setDocumentReviewFiles([]);
      setDocumentReviewDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("document_review").backendFilePaths : []);
      setDocumentReviewSelectedFileIndex(0);
      setDocumentReviewPreviewUrl(null);
      setDocumentReviewTextPreview("");
      setDocumentReviewFileFormValues({});
      setDocumentReviewExtractStates({});
      documentReviewParsedKeysRef.current = new Set();
    }
    if (taskTemplate?.id === "eu_scc") {
      setEuSccStepIndex(0);
      setEuSccValues(createDefaultEuSccValues());
      setEuSccFiles([]);
      setEuSccDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("eu_scc").backendFilePaths : []);
    }
    if (moduleKey === "bcr") {
      setBcrStepIndex(0);
      setBcrValues(createDefaultBcrValues());
      setBcrFiles([]);
      setBcrDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("bcr").backendFilePaths : []);
    }
    if (moduleKey === "dpia") {
      setDpiaStepIndex(0);
      setDpiaValues(createDefaultDpiaValues());
      setDpiaFiles([]);
      setDpiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("dpia").backendFilePaths : []);
    }
    if (moduleKey === "tia") {
      setTiaStepIndex(0);
      setTiaValues(createDefaultTiaValues());
      setTiaFiles([]);
      setTiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("tia").backendFilePaths : []);
    }
    if (moduleKey === "cn_flow") {
      setCnFlowStepIndex(0);
      setCnFlowValues(createDefaultCnFlowValues());
      setCnFlowDataInventoryFiles([]);
      setCnFlowEntityInventoryFiles([]);
      setCnFlowSupportingFiles([]);
      setCnFlowDevFilePaths([]);
    }
    if (moduleKey === "us_14117") {
      setUs14117StepIndex(0);
      setUs14117Values(createDefaultUs14117Values());
      setUs14117Files([]);
    }
    if (moduleKey === "cpra") {
      setCpraStepIndex(0);
      setCpraValues(createDefaultCpraValues());
      setCpraPrivacyPolicyFiles([]);
      setCpraRightsSopFiles([]);
      setCpraDataMapFiles([]);
      setCpraVendorListFiles([]);
      setCpraOtherFiles([]);
    }
  }, [moduleKey, taskTemplate?.id]);

  const definition = findModule(moduleKey);
  const isDocumentReviewTask = taskTemplate?.id === "cn_document_review";
  const isEuSccTask = taskTemplate?.id === "eu_scc";
  const isDiagnosisModule = moduleKey === "diagnosis";
  const isAssessmentModule = moduleKey === "assessment";
  const isPipiaModule = moduleKey === "pipia";
  const isBcrModule = moduleKey === "bcr";
  const isDpiaModule = moduleKey === "dpia";
  const isTiaModule = moduleKey === "tia";
  const isCnFlowModule = moduleKey === "cn_flow";
  const isUs14117Module = moduleKey === "us_14117";
  const isCpraModule = moduleKey === "cpra";

  // ── 开发者测试案例 ──
  const devTestCases = DEV_ACCEL_ENABLED ? getTestCases(moduleKey) : [];
  const [showCasePicker, setShowCasePicker] = useState(false);
  const selectDevCase = (index: number) => {
    const tc = devTestCases[index];
    if (!tc?.formDefaults) return;
    const fd = tc.formDefaults as Record<string, unknown>;
    if (isCpraModule) setCpraValues((prev) => ({ ...prev, ...fd } as CpraFormValues));
    else if (isDiagnosisModule) setDiagnosisValues((prev) => ({ ...prev, ...fd } as DiagnosisFormValues));
    else if (isAssessmentModule) setAssessmentValues((prev) => ({ ...prev, ...fd } as AssessmentFormValues));
    else if (isPipiaModule) setPipiaValues((prev) => ({ ...prev, ...fd } as PipiaFormValues));
    else if (isBcrModule) setBcrValues((prev) => ({ ...prev, ...fd } as BcrFormValues));
    else if (isDpiaModule) setDpiaValues((prev) => ({ ...prev, ...fd } as DpiaFormValues));
    else if (isTiaModule) setTiaValues((prev) => ({ ...prev, ...fd } as TiaFormValues));
    else if (isCnFlowModule) setCnFlowValues((prev) => ({ ...prev, ...fd } as CnFlowFormValues));
    else if (isUs14117Module) setUs14117Values((prev) => ({ ...prev, ...fd } as Us14117FormValues));
    else if (isEuSccTask) setEuSccValues((prev) => ({ ...prev, ...fd } as EuSccFormValues));
    else if (isDocumentReviewTask) {
      setDocumentReviewValues((prev) => ({ ...prev, ...fd } as DocumentReviewFormValues));
      setDocumentReviewFiles([]);
      setDocumentReviewDevFilePaths(
        DEV_ACCEL_ENABLED ? (tc.backendFilePaths?.filter((item) => item.trim().length > 0) ?? []) : []
      );
      setDocumentReviewSelectedFileIndex(0);
      setDocumentReviewPreviewUrl(null);
      setDocumentReviewTextPreview("");
      setDocumentReviewFileFormValues({});
      setDocumentReviewExtractStates({});
    }
    if (isAssessmentModule) {
      setAssessmentDevFilePaths(
        DEV_ACCEL_ENABLED ? (tc.backendFilePaths?.filter((item) => item.trim().length > 0) ?? []) : []
      );
    }
    if (isCnFlowModule) {
      setCnFlowDevFilePaths(
        DEV_ACCEL_ENABLED ? (tc.backendFilePaths?.filter((item) => item.trim().length > 0) ?? []) : []
      );
    }
    setShowCasePicker(false);
  };


  useEffect(() => {
    if (!isDiagnosisModule) return;
    const anchor = diagnosisStepTopRef.current;
    if (!anchor) return;
    const frame = requestAnimationFrame(() => {
      anchor.scrollIntoView({ block: "start", behavior: "auto" });
    });
    return () => cancelAnimationFrame(frame);
  }, [isDiagnosisModule, diagnosisStepIndex]);

  const updateDiagnosisValue = (name: string, value: unknown) => {
    setDiagnosisValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateAssessmentValue = <K extends keyof AssessmentFormValues>(name: K, value: AssessmentFormValues[K]) => {
    setAssessmentValues((prev) => ({ ...prev, [name]: value }));
  };

  const updatePipiaValue = <K extends keyof PipiaFormValues>(name: K, value: PipiaFormValues[K]) => {
    setPipiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateDocumentReviewValue = <K extends keyof DocumentReviewFormValues>(
    name: K,
    value: DocumentReviewFormValues[K]
  ) => {
    const nextValues = { ...documentReviewValues, [name]: value };
    setDocumentReviewValues(nextValues);
    const activeFile = documentReviewFiles[documentReviewSelectedFileIndex] ?? null;
    if (activeFile) {
      const fileKey = getDocumentReviewFileKey(activeFile);
      setDocumentReviewFileFormValues((prev) => ({ ...prev, [fileKey]: nextValues }));
    }
  };

  const syncDocumentReviewValuesForFile = (file: File) => {
    const fileKey = getDocumentReviewFileKey(file);
    const savedValues = documentReviewFileFormValues[fileKey];
    if (savedValues) {
      setDocumentReviewValues(savedValues);
      return;
    }

    const defaultValues = createDefaultDocumentReviewValues();
    const seededValues = seedDocumentReviewValuesForFile(
      {
        ...defaultValues,
        company_name: documentReviewValues.company_name || defaultValues.company_name,
        publisher_entity: documentReviewValues.publisher_entity || defaultValues.publisher_entity,
        receiver_name: documentReviewValues.receiver_name || defaultValues.receiver_name,
        receiver_country: documentReviewValues.receiver_country || defaultValues.receiver_country,
        transfer_purpose: documentReviewValues.transfer_purpose || defaultValues.transfer_purpose,
        pii_count: documentReviewValues.pii_count,
        spi_count: documentReviewValues.spi_count,
        has_scc_draft: documentReviewValues.has_scc_draft,
        review_focus: documentReviewValues.review_focus || defaultValues.review_focus,
        contact_channel: documentReviewValues.contact_channel || defaultValues.contact_channel,
        sensitive_pi_disclosed: documentReviewValues.sensitive_pi_disclosed,
        rights_channel_disclosed: documentReviewValues.rights_channel_disclosed,
        crossborder_rule_disclosed: documentReviewValues.crossborder_rule_disclosed
      },
      file
    );

    setDocumentReviewValues(seededValues);
    setDocumentReviewFileFormValues((prev) => ({ ...prev, [fileKey]: seededValues }));
  };

  const onSelectDocumentReviewFiles = (incomingFiles: FileList | null) => {
    const next = Array.from(incomingFiles ?? []);
    if (next.length === 0) return;
    const hadNoUploadedFiles = documentReviewFiles.length === 0;
    setDocumentReviewFiles((prev) => {
      const merged = [...prev];
      for (const file of next) {
        const duplicate = merged.some(
          (item) =>
            item.name === file.name &&
            item.size === file.size &&
            item.lastModified === file.lastModified
        );
        if (!duplicate) {
          merged.push(file);
        }
      }
      return merged;
    });
    if (hadNoUploadedFiles) {
      setDocumentReviewSelectedFileIndex(0);
      syncDocumentReviewValuesForFile(next[0]);
    }
  };

  const updateEuSccValue = <K extends keyof EuSccFormValues>(name: K, value: EuSccFormValues[K]) => {
    setEuSccValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateBcrValue = <K extends keyof BcrFormValues>(name: K, value: BcrFormValues[K]) => {
    setBcrValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateDpiaValue = <K extends keyof DpiaFormValues>(name: K, value: DpiaFormValues[K]) => {
    setDpiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateTiaValue = <K extends keyof TiaFormValues>(name: K, value: TiaFormValues[K]) => {
    setTiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateCnFlowValue = <K extends keyof CnFlowFormValues>(name: K, value: CnFlowFormValues[K]) => {
    setCnFlowValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateUs14117Value = <K extends keyof Us14117FormValues>(name: K, value: Us14117FormValues[K]) => {
    setUs14117Values((prev) => ({ ...prev, [name]: value }));
  };

  const updateCpraValue = <K extends keyof CpraFormValues>(name: K, value: CpraFormValues[K]) => {
    setCpraValues((prev) => ({ ...prev, [name]: value }));
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

  const buildAssessmentPayloadFrom = async (
    values: AssessmentFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写企业名称。");
    assertInput(hasText(values.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(values.receiver_country), "请填写接收方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写出境目的。");
    assertInput(hasText(values.legal_basis), "请填写合法性基础。");
    assertInput(hasText(values.necessity_basis), "请填写必要性说明。");
    assertInput(hasText(values.data_inventory_summary), "请填写数据清单摘要。");
    assertInput(hasText(values.system_chain_summary), "请填写系统与出境链路说明。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(
      files.length > 0 || presetFilePaths.length > 0,
      "请上传至少1份安全评估附件材料（如数据清单、系统链路图、制度文件）。"
    );

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    return createAssessmentPayload(values, uploadedFiles);
  };

  const buildAssessmentPayload = async (): Promise<unknown> =>
    buildAssessmentPayloadFrom(assessmentValues, assessmentFiles, assessmentDevFilePaths);

  const buildPipiaPayloadFrom = async (
    values: PipiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写处理者名称。");
    assertInput(hasText(values.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(values.purpose), "请填写拟出境活动目的。");
    assertInput(hasText(values.recipient_name), "请填写境外接收方名称。");
    assertInput(hasText(values.recipient_country_region), "请填写接收方国家/地区。");
    assertInput(hasText(values.legal_basis), "请填写处理合法性基础。");
    assertInput(splitCsv(values.pi_categories).length > 0, "请至少填写一类拟出境个人信息。");
    assertInput(hasText(values.notice_mechanism), "请填写告知机制。");
    assertInput(hasText(values.consent_mechanism), "请填写单独同意机制。");
    assertInput(hasText(values.dsar_channel), "请填写个人权利请求渠道。");
    assertInput(hasText(values.retention_policy), "请填写保存与删除策略。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份PIPIA相关附件。");
    if (values.route_type === "scc_filing") {
      assertInput(
        values.attachment_role === "scc_contract",
        "标准合同备案路径下，附件角色需选择为 scc_contract。"
      );
    }

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    return createPipiaPayload(values, uploadedFiles);
  };

  const buildPipiaPayload = async (): Promise<unknown> =>
    buildPipiaPayloadFrom(pipiaValues, pipiaFiles, pipiaDevFilePaths);

  const buildDocumentReviewPayloadFrom = async (
    values: DocumentReviewFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(
      hasText(values.publisher_entity) || hasText(values.company_name),
      "请填写企业名称或发布主体。"
    );
    assertInput(hasText(values.document_title), "请填写文档名称。");
    assertInput(hasText(values.review_focus), "请填写本次审查重点。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请至少上传1份合同或政策文本后再执行审查。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    return createDocumentReviewPayload(values, uploadedFiles);
  };

  const buildDocumentReviewPayload = async (): Promise<unknown> =>
    buildDocumentReviewPayloadFrom(documentReviewValues, documentReviewFiles, documentReviewDevFilePaths);

  const buildEuSccPayloadFrom = async (
    values: EuSccFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(values.importer_name), "请填写数据进口方名称。");
    assertInput(hasText(values.importer_country), "请填写进口方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(values.data_categories), "请填写数据类别。");
    assertInput(hasText(values.tom_summary), "请填写技术与组织措施（TOM）摘要。");
    assertInput(hasText(values.rights_and_complaint), "请填写数据主体权利与投诉机制。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份SCC文本或配套附件。");
    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    return createEuSccPayload(values, uploadedFiles);
  };

  const buildEuSccPayload = async (): Promise<unknown> =>
    buildEuSccPayloadFrom(euSccValues, euSccFiles, euSccDevFilePaths);

  const buildBcrPayloadFrom = async (
    values: BcrFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写集团名称。");
    assertInput(hasText(values.group_structure), "请填写集团结构与申请主体信息。");
    assertInput(hasText(values.data_flow_scope), "请填写数据流与处理活动范围。");
    assertInput(hasText(values.binding_mechanism), "请填写内部约束机制。");
    assertInput(hasText(values.third_country_assessment), "请填写第三国法律评估机制。");
    assertInput(hasText(values.government_access_process), "请填写政府访问请求处理机制。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份BCR主文本或配套申请材料。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    uploadedFiles.forEach((path) => {
      const format = inferDocxPdfFormat(path);
      assertInput(!!format, `BCR附件仅支持 .docx 或 .pdf：${basenameFromPath(path)}`);
    });
    return createBcrPayload(values, uploadedFiles);
  };

  const buildBcrPayload = async (): Promise<unknown> =>
    buildBcrPayloadFrom(bcrValues, bcrFiles, bcrDevFilePaths);

  const buildDpiaPayloadFrom = async (
    values: DpiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.project_name), "请填写项目名称。");
    assertInput(hasText(values.processing_description), "请填写处理活动描述。");
    assertInput(hasText(values.purpose_and_necessity), "请填写目的与必要性说明。");
    assertInput(hasText(values.lawful_basis), "请填写合法性基础。");
    assertInput(hasText(values.risk_assessment), "请填写风险评估。");
    assertInput(hasText(values.mitigation_measures), "请填写缓解措施。");
    assertInput(hasText(values.residual_risk), "请填写剩余风险结论。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份DPIA附件（流程图/制度/合同等）。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    uploadedFiles.forEach((path) => {
      const format = inferDpiaAttachmentFormat(path);
      assertInput(!!format, `DPIA附件仅支持 .docx/.pdf/.png/.jpg：${basenameFromPath(path)}`);
    });

    return createDpiaPayload(values, uploadedFiles);
  };

  const buildDpiaPayload = async (): Promise<unknown> =>
    buildDpiaPayloadFrom(dpiaValues, dpiaFiles, dpiaDevFilePaths);

  const buildTiaPayloadFrom = async (
    values: TiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.data_exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(values.data_importer_name), "请填写数据进口方名称。");
    assertInput(hasText(values.importer_country_region), "请填写进口方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(values.law_findings), "请填写第三国法律评估发现。");
    assertInput(hasText(values.supplementary_technical), "请填写技术性补充措施。");
    assertInput(hasText(values.post_effectiveness), "请填写补充措施后的有效性判断。");
    assertInput(hasText(values.key_actions), "请填写关键行动项。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份TIA附件。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    uploadedFiles.forEach((path) => {
      const format = inferDocxPdfFormat(path);
      assertInput(!!format, `TIA附件仅支持 .docx 或 .pdf：${basenameFromPath(path)}`);
    });
    return createTiaPayload(values, uploadedFiles);
  };

  const buildTiaPayload = async (): Promise<unknown> =>
    buildTiaPayloadFrom(tiaValues, tiaFiles, tiaDevFilePaths);

  const buildCnFlowPayload = async (): Promise<unknown> => {
    assertInput(hasText(cnFlowValues.company_name), "请填写企业名称。");
    assertInput(hasText(cnFlowValues.transfer_purpose), "请填写出境目的。");
    assertInput(splitCsv(cnFlowValues.data_categories).length > 0, "请至少填写一类拟出境数据。");
    assertInput(hasText(cnFlowValues.transfer_chain), "请填写传输链路说明。");
    assertInput(hasText(cnFlowValues.primary_recipient_name), "请填写主要接收方名称。");
    assertInput(hasText(cnFlowValues.primary_recipient_country), "请填写主要接收方国家/地区。");
    const devDataInventoryPath = DEV_ACCEL_ENABLED ? cnFlowDevFilePaths[0] : undefined;
    const devEntityInventoryPath = DEV_ACCEL_ENABLED ? cnFlowDevFilePaths[1] : undefined;
    const devSupportingPaths = DEV_ACCEL_ENABLED ? cnFlowDevFilePaths.slice(2) : [];
    assertInput(cnFlowDataInventoryFiles.length > 0 || !!devDataInventoryPath, "请上传数据清单附件（data_inventory）。");
    assertInput(cnFlowEntityInventoryFiles.length > 0 || !!devEntityInventoryPath, "请上传实体清单附件（entity_inventory）。");

    const [dataInventoryPaths, entityInventoryPaths, supportingPaths] = await Promise.all([
      devDataInventoryPath ? Promise.resolve([devDataInventoryPath]) : uploadFiles(cnFlowDataInventoryFiles),
      devEntityInventoryPath ? Promise.resolve([devEntityInventoryPath]) : uploadFiles(cnFlowEntityInventoryFiles),
      devSupportingPaths.length > 0 ? Promise.resolve(devSupportingPaths) : uploadFiles(cnFlowSupportingFiles)
    ]);

    dataInventoryPaths.forEach((path) => {
      assertInput(
        !!inferCnFlowAttachmentFormat(path),
        `数据清单附件格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`
      );
    });
    entityInventoryPaths.forEach((path) => {
      assertInput(
        !!inferCnFlowAttachmentFormat(path),
        `实体清单附件格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`
      );
    });
    supportingPaths.forEach((path) => {
      assertInput(
        !!inferCnFlowAttachmentFormat(path),
        `补充材料格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`
      );
    });

    return createCnFlowPayload(cnFlowValues, {
      dataInventory: dataInventoryPaths,
      entityInventory: entityInventoryPaths,
      supporting: supportingPaths,
    });
  };

  const buildCpraPayload = async (): Promise<unknown> => {
    assertInput(hasText(cpraValues.company_name), "请填写企业名称。");
    assertInput(hasText(cpraValues.business_model), "请填写业务模型。");
    assertInput(hasText(cpraValues.data_lifecycle), "请填写数据生命周期说明。");
    assertInput(hasText(cpraValues.notice_and_consent), "请填写告知与同意机制。");
    assertInput(hasText(cpraValues.consumer_rights_process), "请填写消费者权利响应机制。");
    assertInput(hasText(cpraValues.opt_out_and_sale_sharing), "请填写出售/共享与Opt-out机制。");
    assertInput(
      hasText(cpraValues.privacy_policy_url) || cpraPrivacyPolicyFiles.length > 0,
      "请提供隐私政策URL或上传隐私政策文件。"
    );

    const [
      privacyPaths,
      rightsPaths,
      dataMapPaths,
      vendorPaths,
      otherPaths
    ] = await Promise.all([
      uploadFiles(cpraPrivacyPolicyFiles),
      uploadFiles(cpraRightsSopFiles),
      uploadFiles(cpraDataMapFiles),
      uploadFiles(cpraVendorListFiles),
      uploadFiles(cpraOtherFiles)
    ]);

    const validatePaths = (paths: string[], label: string) => {
      paths.forEach((path) => {
        assertInput(
          !!inferCpraAttachmentFormat(path),
          `${label}附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`
        );
      });
    };
    validatePaths(privacyPaths, "隐私政策");
    validatePaths(rightsPaths, "权利流程");
    validatePaths(dataMapPaths, "数据映射");
    validatePaths(vendorPaths, "供应商");
    validatePaths(otherPaths, "补充");
    if (hasText(cpraValues.privacy_policy_url)) {
      assertInput(isValidUrl(cpraValues.privacy_policy_url), "隐私政策URL格式不正确，请使用 http(s) 链接。");
    }

    return createCpraPayload(cpraValues, {
      privacyPolicy: privacyPaths,
      rightsSop: rightsPaths,
      dataMap: dataMapPaths,
      vendorList: vendorPaths,
      other: otherPaths,
    });
  };

  const buildUs14117Payload = async (): Promise<unknown> => {
    assertInput(hasText(us14117Values.company_name), "请填写企业名称。");
    assertInput(hasText(us14117Values.project_name), "请填写项目名称。");
    assertInput(hasText(us14117Values.transaction_description), "请填写交易描述。");
    assertInput(hasText(us14117Values.data_item_name), "请填写数据项名称。");
    assertInput(hasText(us14117Values.entity_name), "请填写接收方实体名称。");
    assertInput(hasText(us14117Values.country_of_registration), "请填写接收方注册国家/地区。");

    const uploadedPaths = us14117Files.length > 0 ? await uploadFiles(us14117Files) : [];
    return createUs14117Payload(us14117Values, uploadedPaths);
  };

  const buildDiagnosisPayloadFrom = (values: DiagnosisFormValues): unknown =>
    createDiagnosisPayload(values);

  const buildDiagnosisPayload = (): unknown => buildDiagnosisPayloadFrom(diagnosisValues);

  const runWithPayload = async (requestPayload: unknown) => {
    setLoading(true);
    setError(null);
    setAsyncRunProgress(null);
    try {
      const preferredRunMode: RunMode = hasAsync(definition) ? "async" : "sync";
      const timeoutMs =
        moduleKey === "review"
          ? 900000
          : moduleKey === "assessment"
            ? 900000
            : 180000;
      const result = await runModule(
        definition,
        requestPayload,
        preferredRunMode,
        timeoutMs,
        (progress) => setAsyncRunProgress(progress),
        (taskId) => onTaskCreated?.(taskId, moduleKey, requestPayload),
      );
      setResponseData(result.response);
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
      const errorCode = getModuleRunErrorCode(runErr);
      const asyncTaskId =
        runErr instanceof Error && "asyncTaskId" in runErr && typeof runErr.asyncTaskId === "string"
          ? runErr.asyncTaskId
          : undefined;
      const asyncState =
        runErr instanceof Error && "asyncState" in runErr && typeof runErr.asyncState === "string"
          ? runErr.asyncState
          : undefined;
      setResponseData(undefined);
      setError(message);
      onRunDone({
        module: moduleKey,
        runMode: hasAsync(definition) ? "async" : "sync",
        request: requestPayload,
        success: false,
        error: message,
        errorCode,
        asyncTaskId,
        asyncState,
      });
    } finally {
      setLoading(false);
    }
  };

  const execute = async () => {
    let requestPayload: unknown;
    try {
      if (isDocumentReviewTask) {
        requestPayload = await buildDocumentReviewPayload();
      } else if (isEuSccTask) {
        requestPayload = await buildEuSccPayload();
      } else if (isDiagnosisModule) {
        requestPayload = buildDiagnosisPayload();
      } else if (isAssessmentModule) {
        requestPayload = await buildAssessmentPayload();
      } else if (isPipiaModule) {
        requestPayload = await buildPipiaPayload();
      } else if (isBcrModule) {
        requestPayload = await buildBcrPayload();
      } else if (isDpiaModule) {
        requestPayload = await buildDpiaPayload();
      } else if (isTiaModule) {
        requestPayload = await buildTiaPayload();
      } else if (isCnFlowModule) {
        requestPayload = await buildCnFlowPayload();
      } else if (isUs14117Module) {
        requestPayload = await buildUs14117Payload();
      } else if (isCpraModule) {
        requestPayload = await buildCpraPayload();
      } else {
        requestPayload = JSON.parse(payloadText);
      }
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Payload parse error";
      setError(message);
      onRunDone({
        module: moduleKey,
        runMode: "sync",
        request: isDocumentReviewTask
          ? documentReviewValues
          : isEuSccTask
          ? euSccValues
          : isDiagnosisModule
          ? diagnosisValues
          : isAssessmentModule
            ? assessmentValues
            : isPipiaModule
              ? pipiaValues
              : isBcrModule
                ? bcrValues
                : isDpiaModule
                  ? dpiaValues
                  : isTiaModule
                    ? tiaValues
                    : isCnFlowModule
                      ? cnFlowValues
                      : isCpraModule
                        ? cpraValues
              : payloadText,
        success: false,
        error: message
      });
      return;
    }

    await runWithPayload(requestPayload);
  };

  const runAssessmentDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isAssessmentModule || loading) return;
    const preset = getAssessmentDevPreset();
    const nextValues: AssessmentFormValues = {
      ...assessmentValues,
      ...(preset.formDefaults as Partial<AssessmentFormValues>)
    };
    setAssessmentValues(nextValues);
    setAssessmentFiles([]);
    setAssessmentDevFilePaths(preset.backendFilePaths);
    setAssessmentStepIndex(ASSESSMENT_STEPS.length - 1);
    const payload = await buildAssessmentPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runPipiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isPipiaModule || loading) return;
    const preset = getModuleDevPreset("pipia");
    const nextValues: PipiaFormValues = { ...pipiaValues, ...(preset.formDefaults as Partial<PipiaFormValues>) };
    setPipiaValues(nextValues);
    setPipiaFiles([]);
    setPipiaDevFilePaths(preset.backendFilePaths);
    setPipiaStepIndex(PIPIA_STEPS.length - 1);
    const payload = await buildPipiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runEuSccDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isEuSccTask || loading) return;
    const preset = getModuleDevPreset("eu_scc");
    const nextValues: EuSccFormValues = { ...euSccValues, ...(preset.formDefaults as Partial<EuSccFormValues>) };
    setEuSccValues(nextValues);
    setEuSccFiles([]);
    setEuSccDevFilePaths(preset.backendFilePaths);
    setEuSccStepIndex(EU_SCC_STEPS.length - 1);
    const payload = await buildEuSccPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runBcrDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isBcrModule || loading) return;
    const preset = getModuleDevPreset("bcr");
    const nextValues: BcrFormValues = { ...bcrValues, ...(preset.formDefaults as Partial<BcrFormValues>) };
    setBcrValues(nextValues);
    setBcrFiles([]);
    setBcrDevFilePaths(preset.backendFilePaths);
    setBcrStepIndex(BCR_STEPS.length - 1);
    const payload = await buildBcrPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runDpiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDpiaModule || loading) return;
    const preset = getModuleDevPreset("dpia");
    const nextValues: DpiaFormValues = { ...dpiaValues, ...(preset.formDefaults as Partial<DpiaFormValues>) };
    setDpiaValues(nextValues);
    setDpiaFiles([]);
    setDpiaDevFilePaths(preset.backendFilePaths);
    setDpiaStepIndex(DPIA_STEPS.length - 1);
    const payload = await buildDpiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runTiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isTiaModule || loading) return;
    const preset = getModuleDevPreset("tia");
    const nextValues: TiaFormValues = { ...tiaValues, ...(preset.formDefaults as Partial<TiaFormValues>) };
    setTiaValues(nextValues);
    setTiaFiles([]);
    setTiaDevFilePaths(preset.backendFilePaths);
    setTiaStepIndex(TIA_STEPS.length - 1);
    const payload = await buildTiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runDiagnosisDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDiagnosisModule || loading) return;
    const preset = getModuleDevPreset("diagnosis");
    const nextValues: DiagnosisFormValues = {
      ...diagnosisValues,
      ...(preset.formDefaults as Partial<DiagnosisFormValues>)
    };
    setDiagnosisValues(nextValues);
    setDiagnosisStepIndex(DIAGNOSIS_STEPS.length - 1);
    const payload = buildDiagnosisPayloadFrom(nextValues);
    await runWithPayload(payload);
  };

  const runDocumentReviewDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDocumentReviewTask || loading) return;
    const preset = getModuleDevPreset("document_review");
    const nextValues: DocumentReviewFormValues = {
      ...documentReviewValues,
      ...(preset.formDefaults as Partial<DocumentReviewFormValues>)
    };
    setDocumentReviewValues(nextValues);
    setDocumentReviewFiles([]);
    setDocumentReviewDevFilePaths(preset.backendFilePaths);
    const payload = await buildDocumentReviewPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const currentAssessmentStep = ASSESSMENT_STEPS[assessmentStepIndex];
  const assessmentProgress = Math.round(((assessmentStepIndex + 1) / ASSESSMENT_STEPS.length) * 100);
  const currentDiagnosisStep = DIAGNOSIS_STEPS[diagnosisStepIndex];
  const diagnosisProgress = Math.round(((diagnosisStepIndex + 1) / DIAGNOSIS_STEPS.length) * 100);
  const visibleDiagnosisFields = useMemo(() => {
    const seen = new Set<string>();
    const fields: DiagnosisFieldConfig[] = [];
    for (const field of currentDiagnosisStep.fields) {
      const visible = field.visibleWhen ? field.visibleWhen(diagnosisValues) : true;
      if (!visible) continue;
      if (seen.has(field.name)) continue;
      seen.add(field.name);
      fields.push(field);
    }
    return fields;
  }, [currentDiagnosisStep.fields, diagnosisValues]);

  const diagnosisFieldGroups = useMemo(() => {
    const order: string[] = [];
    const map = new Map<string, DiagnosisFieldConfig[]>();

    for (const field of visibleDiagnosisFields) {
      const groupName = field.group ?? "";
      if (!map.has(groupName)) {
        map.set(groupName, []);
        order.push(groupName);
      }
      map.get(groupName)?.push(field);
    }

    return order.map((groupName) => ({ groupName, fields: map.get(groupName) ?? [] }));
  }, [visibleDiagnosisFields]);
  const currentPipiaStep = PIPIA_STEPS[pipiaStepIndex];
  const pipiaProgress = Math.round(((pipiaStepIndex + 1) / PIPIA_STEPS.length) * 100);
  const currentEuSccStep = EU_SCC_STEPS[euSccStepIndex];
  const euSccProgress = Math.round(((euSccStepIndex + 1) / EU_SCC_STEPS.length) * 100);
  const currentBcrStep = BCR_STEPS[bcrStepIndex];
  const bcrProgress = Math.round(((bcrStepIndex + 1) / BCR_STEPS.length) * 100);
  const currentDpiaStep = DPIA_STEPS[dpiaStepIndex];
  const dpiaProgress = Math.round(((dpiaStepIndex + 1) / DPIA_STEPS.length) * 100);
  const currentTiaStep = TIA_STEPS[tiaStepIndex];
  const tiaProgress = Math.round(((tiaStepIndex + 1) / TIA_STEPS.length) * 100);
  const currentCnFlowStep = CN_FLOW_STEPS[cnFlowStepIndex];
  const cnFlowProgress = Math.round(((cnFlowStepIndex + 1) / CN_FLOW_STEPS.length) * 100);
  const currentUs14117Step = US14117_STEPS[us14117StepIndex];
  const us14117Progress = Math.round(((us14117StepIndex + 1) / US14117_STEPS.length) * 100);
  const currentCpraStep = CPRA_STEPS[cpraStepIndex];
  const cpraProgress = Math.round(((cpraStepIndex + 1) / CPRA_STEPS.length) * 100);
  const panelModuleLabel =
    isDocumentReviewTask && taskTemplate
      ? getTaskTemplateTitle(taskTemplate, lang)
      : definition.label;

  const selectedDocumentReviewFile = documentReviewFiles[documentReviewSelectedFileIndex] ?? null;
  const selectedDocumentReviewFileExt = selectedDocumentReviewFile
    ? getDocumentReviewFileExt(selectedDocumentReviewFile.name)
    : "";
  const selectedDocumentReviewFileKey = selectedDocumentReviewFile
    ? getDocumentReviewFileKey(selectedDocumentReviewFile)
    : "";
  const selectedDocumentReviewExtractState = selectedDocumentReviewFileKey
    ? documentReviewExtractStates[selectedDocumentReviewFileKey]
    : undefined;
  const documentReviewSourceCount = documentReviewFiles.length + documentReviewDevFilePaths.length;
  const documentReviewPreviewableCount = documentReviewFiles.filter((file) =>
    canInlinePreviewDocumentReviewExt(getDocumentReviewFileExt(file.name))
  ).length;
  const documentReviewParsedCount = documentReviewFiles.filter((file) =>
    documentReviewParsedKeysRef.current.has(getDocumentReviewFileKey(file))
  ).length;
  const selectedDocumentReviewCanPreview = canInlinePreviewDocumentReviewExt(selectedDocumentReviewFileExt);

  const openArtifactPath = async (path: string) => {
    const blob = await fetchArtifactBlob(path, "file", "打开文件失败");
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, "_blank", "noopener,noreferrer");
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  };

  const downloadArtifactPath = async (path: string) => {
    const blob = await fetchArtifactBlob(path, "download", "下载文件失败");
    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = blobUrl;
    anchor.download = toFileName(path);
    anchor.click();
    URL.revokeObjectURL(blobUrl);
  };
  const selectedDocumentReviewTypeLabel = getDocumentReviewTypeLabel(selectedDocumentReviewFileExt);
  const selectedDocumentReviewSummaryDate = selectedDocumentReviewFile
    ? formatDocumentReviewFileDate(selectedDocumentReviewFile.lastModified, lang)
    : "";
  const selectedDocumentReviewExtractMeta = getDocumentReviewExtractStatusMeta(selectedDocumentReviewExtractState);

  useEffect(() => {
    if (documentReviewFiles.length === 0) {
      setDocumentReviewSelectedFileIndex(0);
      return;
    }
    setDocumentReviewSelectedFileIndex((prev) => Math.min(prev, documentReviewFiles.length - 1));
  }, [documentReviewFiles]);

  useEffect(() => {
    if (!selectedDocumentReviewFile) {
      setDocumentReviewPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
      setDocumentReviewTextPreview("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedDocumentReviewFile);
    setDocumentReviewPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return objectUrl;
    });

    if (isDocumentReviewTextPreviewExt(selectedDocumentReviewFileExt)) {
      selectedDocumentReviewFile
        .text()
        .then((content) => setDocumentReviewTextPreview(content.slice(0, 8000)))
        .catch(() => setDocumentReviewTextPreview(""));
    } else {
      setDocumentReviewTextPreview("");
    }

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedDocumentReviewFile, selectedDocumentReviewFileExt]);

  useEffect(() => {
    if (!selectedDocumentReviewFile) return;
    const fileKey = getDocumentReviewFileKey(selectedDocumentReviewFile);
    if (documentReviewParsedKeysRef.current.has(fileKey)) return;

    let cancelled = false;
    setDocumentReviewExtractStates((prev) => ({
      ...prev,
      [fileKey]: {
        status: "loading",
        note: "正在解析文档并自动回填字段..."
      }
    }));
    buildAutoExtractResult(selectedDocumentReviewFile)
      .then((extracted) => {
        if (cancelled) return;
        setDocumentReviewValues((prev) => {
          const nextValues = {
            ...prev,
            document_title: extracted.documentTitle || prev.document_title,
            document_type: extracted.documentType || prev.document_type,
            review_focus: extracted.reviewFocus || prev.review_focus,
            transfer_purpose: extracted.transferPurpose || prev.transfer_purpose,
            sensitive_pi_disclosed: extracted.sensitivePiDisclosed,
            rights_channel_disclosed: extracted.rightsChannelDisclosed,
            crossborder_rule_disclosed: extracted.crossborderRuleDisclosed,
            contact_channel: extracted.contactChannel || prev.contact_channel,
          };
          setDocumentReviewFileFormValues((saved) => ({ ...saved, [fileKey]: nextValues }));
          return nextValues;
        });
        setDocumentReviewExtractStates((prev) => ({
          ...prev,
          [fileKey]: {
            status: "done",
            note: extracted.note
          }
        }));
        documentReviewParsedKeysRef.current.add(fileKey);
      })
      .catch(() => {
        if (cancelled) return;
        setDocumentReviewExtractStates((prev) => ({
          ...prev,
          [fileKey]: {
            status: "error",
            note: "自动提取失败，请手动确认与填写。"
          }
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDocumentReviewFile]);

  return (
    <>
    <section className="run-panel" data-guide="stage-run">
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
          <strong>{panelModuleLabel}</strong>
        </div>
      )}

      {isDocumentReviewTask ? (
        <section className="doc-review-workbench">
          <aside className="doc-review-input-pane">
            <header className="doc-review-panel-head">
              <div className="doc-review-panel-title-row">
                <div className="doc-review-panel-copy">
                  <span className="doc-review-kicker">Input Workspace</span>
                  <div className="schema-wizard-head">
                    <div className="runner-title">文档输入管理</div>
                    <span className="doc-review-count-badge">{documentReviewSourceCount} 份材料</span>
                  </div>
                  <p>集中管理上传材料、预置文件与解析进度。点击文件后，右侧立即切换到对应预览与确认状态。</p>
                </div>
                {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (
                  <button
                    type="button"
                    className="pill-btn doc-review-head-action"
                    onClick={() => setShowCasePicker(true)}
                  >
                    🧪 测试案例
                  </button>
                ) : null}
              </div>
              <div className="doc-review-panel-stats">
                <article>
                  <strong>{documentReviewFiles.length}</strong>
                  <span>已上传</span>
                </article>
                <article>
                  <strong>{documentReviewPreviewableCount}</strong>
                  <span>可预览</span>
                </article>
                <article>
                  <strong>{documentReviewParsedCount}</strong>
                  <span>已回填</span>
                </article>
              </div>
            </header>

            <label className="doc-review-upload-drop">
              <div className="doc-review-upload-copy">
                <span>上传待审查文档</span>
                <p>建议上传隐私政策、用户协议、标准合同、DPA 或辅助证明材料，支持批量导入并自动去重。</p>
              </div>
              <div className="doc-review-upload-tags">
                <span>PDF</span>
                <span>DOCX</span>
                <span>Markdown</span>
                <span>CSV / JSON</span>
                <span>图片</span>
              </div>
              <input
                type="file"
                multiple
                onChange={(event) => onSelectDocumentReviewFiles(event.target.files)}
              />
            </label>

            <section className="doc-review-source-section">
              <div className="doc-review-source-head">
                <strong>上传队列</strong>
                <small>点击任一文件，可切换预览舞台与自动回填状态。</small>
              </div>
              {documentReviewFiles.length === 0 ? (
                <article className="doc-review-queue-empty">
                  <strong>上传后这里会形成统一文件队列</strong>
                  <p>每个文件会显示格式、体积、可预览性与解析状态，方便你逐份核对并进入专项审查。</p>
                </article>
              ) : (
                <div className="doc-review-file-list">
                  {documentReviewFiles.map((file, index) => {
                    const fileKey = getDocumentReviewFileKey(file);
                    const fileExt = getDocumentReviewFileExt(file.name);
                    const fileStatus = getDocumentReviewExtractStatusMeta(documentReviewExtractStates[fileKey]);
                    const canPreview = canInlinePreviewDocumentReviewExt(fileExt);
                    return (
                      <button
                        type="button"
                        key={fileKey}
                        className={`doc-review-file-item ${index === documentReviewSelectedFileIndex ? "active" : ""}`}
                        onClick={() => {
                          setDocumentReviewSelectedFileIndex(index);
                          syncDocumentReviewValuesForFile(file);
                        }}
                      >
                        <div className="doc-review-file-item-main">
                          <div className="doc-review-file-item-title-row">
                            <strong>{file.name}</strong>
                            {index === documentReviewSelectedFileIndex ? (
                              <span className="doc-review-inline-flag">当前查看</span>
                            ) : null}
                          </div>
                          <div className="doc-review-file-item-meta">
                            <span className="doc-review-meta-pill">{getDocumentReviewTypeLabel(fileExt)}</span>
                            <span className="doc-review-meta-pill">{formatDocumentReviewFileSize(file.size)}</span>
                            <span className={`doc-review-meta-pill ${canPreview ? "is-success" : "is-neutral"}`}>
                              {canPreview ? "可预览" : "不可内嵌预览"}
                            </span>
                          </div>
                        </div>
                        <div className="doc-review-file-item-side">
                          <span className={`doc-review-status-pill is-${fileStatus.tone}`}>{fileStatus.label}</span>
                          <small>{formatDocumentReviewFileDate(file.lastModified, lang)}</small>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            {DEV_ACCEL_ENABLED && documentReviewDevFilePaths.length > 0 ? (
              <section className="doc-review-source-section doc-review-source-section-muted">
                <div className="doc-review-source-head">
                  <strong>开发预置材料</strong>
                  <small>用于快速体验真实审查链路，不占用本地上传队列。</small>
                </div>
                <div className="doc-review-preset-list">
                  {documentReviewDevFilePaths.map((path) => {
                    const fileName = path.split("/").pop() || path;
                    return (
                      <article key={`dev-document-review-file-${path}`} className="doc-review-preset-item">
                        <div>
                          <strong>{fileName}</strong>
                          <div className="doc-review-file-item-meta">
                            <span className="doc-review-meta-pill">{getDocumentReviewTypeLabel(getDocumentReviewFileExt(fileName))}</span>
                            <span className="doc-review-meta-pill is-neutral">预置导入</span>
                          </div>
                        </div>
                        <span className="doc-review-status-pill is-neutral">Dev preset</span>
                      </article>
                    );
                  })}
                </div>
              </section>
            ) : null}
          </aside>

          <div className="doc-review-main-pane">
            {!selectedDocumentReviewFile ? (
              <article className="doc-review-empty-state">
                <div className="doc-review-empty-state-hero">
                  <span className="doc-review-kicker">Preview Workspace</span>
                  <h3>选择左侧文件后，这里会直接进入正文预览与审查控制</h3>
                  <p>
                    {documentReviewSourceCount > 0
                      ? `当前已纳入 ${documentReviewSourceCount} 份材料，请从左侧选择一个文件开始。`
                      : "先从左侧上传文档，系统会自动解析标题、类型和审查重点。"}
                  </p>
                </div>
                <div className="doc-review-empty-state-steps">
                  <span>上传材料</span>
                  <span>切换预览</span>
                  <span>确认字段并执行</span>
                </div>
              </article>
            ) : (
              <article className="doc-review-preview-card">
                <header className="doc-review-preview-head">
                  <div className="doc-review-preview-title-block">
                    <span className="doc-review-kicker">Preview Stage</span>
                    <strong>{selectedDocumentReviewFile.name}</strong>
                    <p>
                      {selectedDocumentReviewCanPreview
                        ? "可直接边看正文边确认自动回填字段。"
                        : "当前格式不支持内嵌预览，但仍可继续自动解析与专项审查。"}
                    </p>
                  </div>
                  <div className="doc-review-preview-meta">
                    <span className="doc-review-meta-pill">{selectedDocumentReviewTypeLabel}</span>
                    <span className="doc-review-meta-pill">{formatDocumentReviewFileSize(selectedDocumentReviewFile.size)}</span>
                    <span className="doc-review-meta-pill">{selectedDocumentReviewSummaryDate}</span>
                    <span className={`doc-review-status-pill is-${selectedDocumentReviewCanPreview ? "success" : "neutral"}`}>
                      {selectedDocumentReviewCanPreview ? "可预览" : "审查模式"}
                    </span>
                    <span className={`doc-review-status-pill is-${selectedDocumentReviewExtractMeta.tone}`}>
                      {selectedDocumentReviewExtractMeta.label}
                    </span>
                  </div>
                </header>
                <div className={`doc-review-preview-body ${selectedDocumentReviewCanPreview ? "" : "is-fallback"}`}>
                  {documentReviewPreviewUrl && selectedDocumentReviewFileExt === "pdf" ? (
                    <div className="doc-review-pdf-surface">
                      <iframe title={selectedDocumentReviewFile.name} src={documentReviewPreviewUrl} />
                    </div>
                  ) : documentReviewPreviewUrl && isDocumentReviewImagePreviewExt(selectedDocumentReviewFileExt) ? (
                    <div className="doc-review-image-surface">
                      <img src={documentReviewPreviewUrl} alt={selectedDocumentReviewFile.name} />
                    </div>
                  ) : isDocumentReviewTextPreviewExt(selectedDocumentReviewFileExt) ? (
                    <div className="doc-review-text-surface">
                      <pre>{documentReviewTextPreview || "正在读取文本..."}</pre>
                    </div>
                  ) : (
                    <div className="doc-review-preview-fallback">
                      <div className="doc-review-preview-fallback-emblem">{selectedDocumentReviewTypeLabel}</div>
                      <div className="doc-review-preview-fallback-copy">
                        <strong>当前格式暂不支持内嵌预览</strong>
                        <p>这不是失败态。文件仍会参与自动解析、字段回填与专项审查，你可以继续完成整套工作流。</p>
                      </div>
                      <div className="doc-review-preview-fallback-actions">
                        <span className={`doc-review-status-pill is-${selectedDocumentReviewExtractMeta.tone}`}>
                          {selectedDocumentReviewExtractMeta.label}
                        </span>
                        <span className="doc-review-meta-pill">{selectedDocumentReviewSummaryDate}</span>
                      </div>
                      <div className="doc-review-preview-next">
                        <span>建议下一步</span>
                        <ul>
                          <li>先核对下方结构化字段与自动回填结果</li>
                          <li>如需直观预览正文，可补充 PDF、图片或文本版本</li>
                          <li>确认无误后，直接执行专项审查生成报告</li>
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            )}

            <article className="doc-review-confirm-card">
              <header className="doc-review-confirm-head">
                <div>
                  <span className="doc-review-kicker">Review Controls</span>
                  <h4>结构化确认</h4>
                  <p>确认标题、类型与重点条款后，直接执行专项审查。</p>
                </div>
                <div className="doc-review-confirm-head-side doc-review-confirm-toolbar">
                  <div className="doc-review-confirm-quickmeta">
                    <span className="doc-review-meta-pill">
                      {selectedDocumentReviewFile ? selectedDocumentReviewFile.name : "待选择文档"}
                    </span>
                    {selectedDocumentReviewFile ? (
                      <span className="doc-review-meta-pill">
                        {selectedDocumentReviewTypeLabel} · {getDocumentReviewDocTypeLabel(documentReviewValues.document_type)}
                      </span>
                    ) : null}
                  </div>
                  <span className={`doc-review-status-pill is-${selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.tone : "neutral"}`}>
                    {selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.label : "等待选择文件"}
                  </span>
                  <div className="schema-actions-row doc-review-actions-row">
                    {DEV_ACCEL_ENABLED ? (
                      <button
                        className="pill-btn"
                        type="button"
                        onClick={runDocumentReviewDevPreset}
                        disabled={loading}
                        title="开发期一键注入文档审查预设并运行真实后端流程"
                      >
                        一键体验
                      </button>
                    ) : null}
                    <button className="pill-btn-primary" onClick={execute} disabled={loading}>
                      {loading ? t("runningNow") : "执行审查"}
                    </button>
                  </div>
                </div>
              </header>
              <p className={`doc-review-autofill-note is-${selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.tone : "neutral"}`}>
                {selectedDocumentReviewFile
                  ? selectedDocumentReviewExtractState?.note || "已选中文件，准备进入自动提取与人工确认。"
                  : "选择文件后，这里会显示自动提取结果并进入人工确认。"}
              </p>
              <div className="schema-field-grid">
                <label className="field-wrap">
                  <span>{localizeFieldLabel(lang, "document_title", "文档名称")}</span>
                  <input
                    value={String(documentReviewValues.document_title)}
                    onChange={(event) => updateDocumentReviewValue("document_title", event.target.value)}
                  />
                </label>
                <label className="field-wrap">
                  <span>{localizeFieldLabel(lang, "document_type", "文档类型")}</span>
                  <select
                    value={String(documentReviewValues.document_type)}
                    onChange={(event) =>
                      updateDocumentReviewValue("document_type", event.target.value as DocumentReviewFormValues["document_type"])
                    }
                  >
                    <option value="privacy_policy">隐私政策</option>
                    <option value="scc_contract">标准合同</option>
                    <option value="dpa">数据处理协议</option>
                    <option value="other">其他</option>
                  </select>
                </label>
                <label className="field-wrap schema-field-wide">
                  <span>{localizeFieldLabel(lang, "review_focus", "本次重点关注条款")}</span>
                  <textarea
                    className="runner-textarea schema-textarea"
                    value={String(documentReviewValues.review_focus)}
                    onChange={(event) => updateDocumentReviewValue("review_focus", event.target.value)}
                  />
                </label>
              </div>
              {loading && asyncRunProgress ? (
                <p className="doc-review-autofill-note is-loading">
                  {REVIEW_ASYNC_STATE_LABEL[asyncRunProgress.state] ?? asyncRunProgress.state}
                  {typeof asyncRunProgress.progress === "number" ? `（${asyncRunProgress.progress}%）` : ""}
                </p>
              ) : null}
            </article>
          </div>
        </section>
      ) : isEuSccTask ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">SCC Review Wizard</div>
            <span>{euSccProgress}%</span>
          </div>
          <div className="schema-stepper">
            {EU_SCC_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === euSccStepIndex ? "active" : ""}`}
                onClick={() => setEuSccStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentEuSccStep.title)}</div>
          <div className="schema-field-grid">
            {currentEuSccStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(euSccValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateEuSccValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(euSccValues[field.name])}
                    onChange={(event) => updateEuSccValue(field.name, event.target.checked as never)}
                  />
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {euSccStepIndex === EU_SCC_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">SCC文本与配套材料上传</div>
              <input type="file" multiple onChange={(event) => setEuSccFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && euSccDevFilePaths.length > 0 ? (
                  <>
                    {euSccDevFilePaths.map((path) => (
                      <article key={`dev-scc-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {euSccFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {euSccFiles.length === 0 && (!DEV_ACCEL_ENABLED || euSccDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份SCC文本或附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runEuSccDevPreset}
                disabled={loading}
                title="开发期一键注入SCC预设并运行真实后端流程"
              >
                一键体验SCC
              </button>
            ) : null}
            <button
              className="pill-btn"
              type="button"
              onClick={() => setEuSccStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={euSccStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setEuSccStepIndex((prev) => Math.min(EU_SCC_STEPS.length - 1, prev + 1))}
              disabled={euSccStepIndex === EU_SCC_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成SCC合规审查报告"}
            </button>
          </div>
        </section>
      ) : isDiagnosisModule ? (
        <section className="schema-wizard schema-wizard--diagnosis">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div ref={diagnosisStepTopRef} />
          <div className="schema-wizard-head">
            <div className="runner-title">业务数据合规需求诊断</div>
            <span>{diagnosisProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DIAGNOSIS_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === diagnosisStepIndex ? "active" : ""}`}
                onClick={() => setDiagnosisStepIndex(index)}
                type="button"
              >
                {index + 1} {DIAGNOSIS_STEP_SHORT_TITLES[index] ?? localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentDiagnosisStep.title)}</div>
          <div className="diagnosis-sections" key={`diagnosis-step-${diagnosisStepIndex}`}>
            {diagnosisFieldGroups.map(({ groupName, fields }) => (
              <section key={`diagnosis-group-${diagnosisStepIndex}-${groupName}`} className="diagnosis-section">
                {groupName ? <h4 className="diagnosis-section-title">{groupName}</h4> : null}
                <div className="schema-field-grid diagnosis-field-grid">
                  {fields.map((field) => {
              const selectedSingle = typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : "";
              const selectedMulti = Array.isArray(diagnosisValues[field.name])
                ? (diagnosisValues[field.name] as unknown[]).map((item) => String(item))
                : [];

              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                    />
                  </label>
                );
              }

              if (field.type === "single") {
                return (
                  <label key={String(field.name)} className="field-wrap diagnosis-field">
                    <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <div className={`diagnosis-option-grid ${field.name === "m1_business_channels" ? "diagnosis-option-grid--multiwide" : "diagnosis-option-grid--single"}`}>
                      {(field.options ?? []).map((option) => (
                        <label key={`${field.name}-${option.value}`} className="diagnosis-option-card">
                          <input
                            type="radio"
                            name={field.name}
                            checked={selectedSingle === option.value}
                            onChange={() => updateDiagnosisValue(field.name, option.value)}
                          />
                          <span>{localizeOptionLabel(lang, option.value, option.label)}</span>
                        </label>
                      ))}
                    </div>
                    {(field.options ?? [])
                      .filter((option) => option.extraFieldId && selectedSingle === option.value)
                      .map((option) => (
                        <input
                          key={`${field.name}-${option.extraFieldId}`}
                          className="diagnosis-extra-input"
                          value={typeof diagnosisValues[option.extraFieldId as string] === "string"
                            ? String(diagnosisValues[option.extraFieldId as string])
                            : ""}
                          onChange={(event) => updateDiagnosisValue(option.extraFieldId as string, event.target.value)}
                          placeholder={option.extraPlaceholder ?? "请补充说明"}
                        />
                      ))}
                  </label>
                );
              }

              if (field.type === "multi") {
                return (
                  <label key={String(field.name)} className="field-wrap diagnosis-field">
                    <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <div className={`diagnosis-option-grid ${field.name === "m1_business_channels" ? "diagnosis-option-grid--multiwide" : "diagnosis-option-grid--multi"}`}>
                      {(field.options ?? []).map((option) => {
                        const checked = selectedMulti.includes(option.value);
                        return (
                          <label key={`${field.name}-${option.value}`} className="diagnosis-option-card">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) => {
                                const next = event.target.checked
                                  ? [...selectedMulti, option.value]
                                  : selectedMulti.filter((item) => item !== option.value);
                                updateDiagnosisValue(field.name, next);
                                if (!event.target.checked && option.extraFieldId) {
                                  updateDiagnosisValue(option.extraFieldId, "");
                                }
                              }}
                            />
                            <span>{localizeOptionLabel(lang, option.value, option.label)}</span>
                          </label>
                        );
                      })}
                    </div>
                    {(field.options ?? [])
                      .filter((option) => option.extraFieldId && selectedMulti.includes(option.value))
                      .map((option) => (
                        <input
                          key={`${field.name}-${option.extraFieldId}`}
                          className="diagnosis-extra-input"
                          value={typeof diagnosisValues[option.extraFieldId as string] === "string"
                            ? String(diagnosisValues[option.extraFieldId as string])
                            : ""}
                          onChange={(event) => updateDiagnosisValue(option.extraFieldId as string, event.target.value)}
                          placeholder={option.extraPlaceholder ?? "请补充说明"}
                        />
                      ))}
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="field-wrap diagnosis-field">
                  <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  <input
                    className="diagnosis-extra-input"
                    value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                    onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                  />
                </label>
              );
            })}
                </div>
              </section>
            ))}
          </div>

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runDiagnosisDevPreset}
                disabled={loading}
                title="开发期一键注入诊断问卷预设并运行真实后端流程"
              >
                一键体验诊断
              </button>
            ) : null}
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
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
{DEV_ACCEL_ENABLED ? (
            <div className="schema-dev-banner">
              <strong>开发测试模式</strong>
              <span>
                当前为测试模式数据，仅用于开发联调与功能演示，不用于正式提交或合规判断。
              </span>
            </div>
          ) : null}
          <div className="schema-wizard-head">
            <div className="runner-title">Assessment Wizard</div>
            <span>{assessmentProgress}%</span>
          </div>
          <div className="schema-stepper">
            {ASSESSMENT_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === assessmentStepIndex ? "active" : ""}`}
                onClick={() => setAssessmentStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentAssessmentStep.title)}</div>
          <div className="schema-field-grid">
            {currentAssessmentStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      name={String(field.name)}
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      name={String(field.name)}
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      name={String(field.name)}
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

              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      name={String(field.name)}
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    name={String(field.name)}
                    type="checkbox"
                    checked={Boolean(assessmentValues[field.name])}
                    onChange={(event) => updateAssessmentValue(field.name, event.target.checked as never)}
                  />
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {assessmentStepIndex === ASSESSMENT_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">附件上传</div>
              <input
                name="assessmentAttachments"
                type="file"
                multiple
                onChange={(event) => setAssessmentFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && assessmentDevFilePaths.length > 0 ? (
                  <>
                    {assessmentDevFilePaths.map((path) => (
                      <article key={`dev-assessment-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {assessmentFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {assessmentFiles.length === 0 && (!DEV_ACCEL_ENABLED || assessmentDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传附件材料后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runAssessmentDevPreset}
                disabled={loading}
                title="开发期一键注入预设数据并运行真实Assessment流程"
              >
                一键体验主流程
              </button>
            ) : null}
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
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">PIPIA Wizard</div>
            <span>{pipiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {PIPIA_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === pipiaStepIndex ? "active" : ""}`}
                onClick={() => setPipiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentPipiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentPipiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                {DEV_ACCEL_ENABLED && pipiaDevFilePaths.length > 0 ? (
                  <>
                    {pipiaDevFilePaths.map((path) => (
                      <article key={`dev-pipia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {pipiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {pipiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || pipiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份PIPIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runPipiaDevPreset}
                disabled={loading}
                title="开发期一键注入PIPIA预设并运行真实后端流程"
              >
                一键体验PIPIA
              </button>
            ) : null}
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
      ) : isBcrModule ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">BCR Review Wizard</div>
            <span>{bcrProgress}%</span>
          </div>
          <div className="schema-stepper">
            {BCR_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === bcrStepIndex ? "active" : ""}`}
                onClick={() => setBcrStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentBcrStep.title)}</div>
          <div className="schema-field-grid">
            {currentBcrStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={String(bcrValues[field.name])}
                      onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(bcrValues[field.name])}
                      onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="field-wrap schema-field-wide">
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  <textarea
                    className="runner-textarea schema-textarea"
                    value={String(bcrValues[field.name])}
                    onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                  />
                </label>
              );
            })}
          </div>

          {bcrStepIndex === BCR_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">BCR主文本与配套材料上传（仅docx/pdf）</div>
              <input type="file" multiple onChange={(event) => setBcrFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && bcrDevFilePaths.length > 0 ? (
                  <>
                    {bcrDevFilePaths.map((path) => (
                      <article key={`dev-bcr-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {bcrFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {bcrFiles.length === 0 && (!DEV_ACCEL_ENABLED || bcrDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份BCR材料后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runBcrDevPreset}
                disabled={loading}
                title="开发期一键注入BCR预设并运行真实后端流程"
              >
                一键体验BCR
              </button>
            ) : null}
            <button
              className="pill-btn"
              type="button"
              onClick={() => setBcrStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={bcrStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setBcrStepIndex((prev) => Math.min(BCR_STEPS.length - 1, prev + 1))}
              disabled={bcrStepIndex === BCR_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成BCR审查报告"}
            </button>
          </div>
        </section>
      ) : isDpiaModule ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">DPIA Wizard</div>
            <span>{dpiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DPIA_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === dpiaStepIndex ? "active" : ""}`}
                onClick={() => setDpiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentDpiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentDpiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(dpiaValues[field.name])}
                    onChange={(event) => updateDpiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {dpiaStepIndex === DPIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">DPIA附件上传（docx/pdf/png/jpg）</div>
              <input type="file" multiple onChange={(event) => setDpiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && dpiaDevFilePaths.length > 0 ? (
                  <>
                    {dpiaDevFilePaths.map((path) => (
                      <article key={`dev-dpia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {dpiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {dpiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || dpiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份DPIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runDpiaDevPreset}
                disabled={loading}
                title="开发期一键注入DPIA预设并运行真实后端流程"
              >
                一键体验DPIA
              </button>
            ) : null}
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDpiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={dpiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDpiaStepIndex((prev) => Math.min(DPIA_STEPS.length - 1, prev + 1))}
              disabled={dpiaStepIndex === DPIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成DPIA草案"}
            </button>
          </div>
        </section>
      ) : isTiaModule ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">TIA Wizard</div>
            <span>{tiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {TIA_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === tiaStepIndex ? "active" : ""}`}
                onClick={() => setTiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentTiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentTiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(tiaValues[field.name])}
                    onChange={(event) => updateTiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {tiaStepIndex === TIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">TIA附件上传（docx/pdf）</div>
              <input type="file" multiple onChange={(event) => setTiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && tiaDevFilePaths.length > 0 ? (
                  <>
                    {tiaDevFilePaths.map((path) => (
                      <article key={`dev-tia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {tiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {tiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || tiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份TIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runTiaDevPreset}
                disabled={loading}
                title="开发期一键注入TIA预设并运行真实后端流程"
              >
                一键体验TIA
              </button>
            ) : null}
            <button
              className="pill-btn"
              type="button"
              onClick={() => setTiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={tiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setTiaStepIndex((prev) => Math.min(TIA_STEPS.length - 1, prev + 1))}
              disabled={tiaStepIndex === TIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成TIA草案"}
            </button>
          </div>
        </section>
      ) : isCnFlowModule ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">CN Flow Wizard</div>
            <span>{cnFlowProgress}%</span>
          </div>
          <div className="schema-stepper">
            {CN_FLOW_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === cnFlowStepIndex ? "active" : ""}`}
                onClick={() => setCnFlowStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentCnFlowStep.title)}</div>
          {currentCnFlowStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCnFlowStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <input
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <label key={String(field.name)} className="field-wrap schema-field-wide">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <textarea
                        className="runner-textarea schema-textarea"
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "select") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <select
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      >
                        {(field.options ?? []).map((option) => (
                          <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                        ))}
                      </select>
                    </label>
                  );
                }
                return (
                  <label key={String(field.name)} className="schema-checkbox-field">
                    <input
                      type="checkbox"
                      checked={Boolean(cnFlowValues[field.name])}
                      onChange={(event) => updateCnFlowValue(field.name, event.target.checked as never)}
                    />
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  </label>
                );
              })}
            </div>
          ) : null}

          {cnFlowStepIndex === CN_FLOW_STEPS.length - 1 ? (
            <>
              <section className="schema-upload-card">
                <div className="runner-title">数据清单附件（必传，data_inventory）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowDataInventoryFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowDataInventoryFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowDataInventoryFiles.length === 0 ? (
                    <p className="resource-empty">请上传至少1份数据清单（xlsx/csv/docx/pdf）。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">实体清单附件（必传，entity_inventory）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowEntityInventoryFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowEntityInventoryFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowEntityInventoryFiles.length === 0 ? (
                    <p className="resource-empty">请上传至少1份实体清单（xlsx/csv/docx/pdf）。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">补充材料（可选，supporting_material）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowSupportingFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowSupportingFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowSupportingFiles.length === 0 ? (
                    <p className="resource-empty">可上传股权结构、组织架构、合同台账等辅助材料。</p>
                  ) : null}
                </div>
              </section>
            </>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCnFlowStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={cnFlowStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCnFlowStepIndex((prev) => Math.min(CN_FLOW_STEPS.length - 1, prev + 1))}
              disabled={cnFlowStepIndex === CN_FLOW_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成14117风险评估结论报告"}
            </button>
          </div>
        </section>
      ) : isUs14117Module ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
          <div className="schema-wizard-head">
            <div className="runner-title">EO 14117 Wizard</div>
            <span>{us14117Progress}%</span>
          </div>
          <div className="schema-stepper">
            {US14117_STEPS.map((step, index) => (
              <button key={localizeStepTitle(lang, step.title)} className={`schema-step-dot ${index === us14117StepIndex ? "active" : ""}`} onClick={() => setUs14117StepIndex(index)} type="button">
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentUs14117Step.title)}</div>
          {currentUs14117Step.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentUs14117Step.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <input value={String(us14117Values[field.name as keyof Us14117FormValues])} onChange={(event) => updateUs14117Value(field.name as keyof Us14117FormValues, event.target.value as never)} />
                    </label>
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <label key={String(field.name)} className="field-wrap schema-field-wide">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <textarea className="runner-textarea schema-textarea" value={String(us14117Values[field.name as keyof Us14117FormValues])} onChange={(event) => updateUs14117Value(field.name as keyof Us14117FormValues, event.target.value as never)} />
                    </label>
                  );
                }
                if (field.type === "number") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <input type="number" min={(field as Us14117FieldConfig).min ?? 0} step={(field as Us14117FieldConfig).step ?? 1} value={Number(us14117Values[field.name as keyof Us14117FormValues])} onChange={(event) => updateUs14117Value(field.name as keyof Us14117FormValues, Number(event.target.value) as never)} />
                    </label>
                  );
                }
                if (field.type === "select") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <select value={String(us14117Values[field.name as keyof Us14117FormValues])} onChange={(event) => updateUs14117Value(field.name as keyof Us14117FormValues, event.target.value as never)}>
                        {(field.options ?? []).map((option) => (<option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>))}
                      </select>
                    </label>
                  );
                }
                return (
                  <label key={String(field.name)} className="schema-checkbox-field">
                    <input type="checkbox" checked={Boolean(us14117Values[field.name as keyof Us14117FormValues])} onChange={(event) => updateUs14117Value(field.name as keyof Us14117FormValues, event.target.checked as never)} />
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  </label>
                );
              })}
            </div>
          ) : null}

          {us14117StepIndex === US14117_STEPS.length - 1 ? (
            <>
              <section className="schema-upload-card">
                <div className="runner-title">辅助材料（可选）</div>
                <input type="file" multiple onChange={(event) => setUs14117Files(Array.from(event.target.files ?? []))} />
                <div className="schema-upload-list">
                  {us14117Files.map((file) => (<article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item"><strong>{file.name}</strong><small>{Math.max(1, Math.round(file.size / 1024))} KB</small></article>))}
                  {us14117Files.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>
            </>
          ) : null}

          <div className="schema-actions-row">
            <button className="pill-btn" type="button" onClick={() => setUs14117StepIndex((prev) => Math.max(0, prev - 1))} disabled={us14117StepIndex === 0}>上一步</button>
            <button className="pill-btn" type="button" onClick={() => setUs14117StepIndex((prev) => Math.min(US14117_STEPS.length - 1, prev + 1))} disabled={us14117StepIndex === US14117_STEPS.length - 1}>下一步</button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>{loading ? t("runningNow") : "运行 EO 14117 评估"}</button>
            {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginLeft: 8 }}>🧪 测试案例</button>) : null}
          </div>
        </section>
      ) : isCpraModule ? (
        <section className="schema-wizard">
                    {DEV_ACCEL_ENABLED && devTestCases.length > 0 ? (<button type="button" className="pill-btn" onClick={() => setShowCasePicker(true)} style={{ marginBottom: 12 }}>🧪 测试案例</button>) : null}
<div className="schema-wizard-head">
            <div className="runner-title">CPRA Wizard</div>
            <span>{cpraProgress}%</span>
          </div>
          <div className="schema-stepper">
            {CPRA_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === cpraStepIndex ? "active" : ""}`}
                onClick={() => setCpraStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentCpraStep.title)}</div>
          {currentCpraStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCpraStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <input
                        value={String(cpraValues[field.name])}
                        onChange={(event) => updateCpraValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <label key={String(field.name)} className="field-wrap schema-field-wide">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <textarea
                        className="runner-textarea schema-textarea"
                        value={String(cpraValues[field.name])}
                        onChange={(event) => updateCpraValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                return (
                  <label key={String(field.name)} className="schema-checkbox-field">
                    <input
                      type="checkbox"
                      checked={Boolean(cpraValues[field.name])}
                      onChange={(event) => updateCpraValue(field.name, event.target.checked as never)}
                    />
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  </label>
                );
              })}
            </div>
          ) : null}

          {cpraStepIndex === CPRA_STEPS.length - 1 ? (
            <>
              <section className="schema-upload-card">
                <div className="runner-title">隐私政策（privacy_policy）</div>
                <p className="resource-empty">可填写URL，也可上传文档。两者满足其一即可。</p>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraPrivacyPolicyFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraPrivacyPolicyFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraPrivacyPolicyFiles.length === 0 ? (
                    <p className="resource-empty">若未提供URL，请至少上传1份隐私政策文件。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">消费者权利SOP（rights_sop，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraRightsSopFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraRightsSopFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraRightsSopFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">数据映射材料（data_map，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraDataMapFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraDataMapFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraDataMapFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">供应商清单（vendor_list，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraVendorListFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraVendorListFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraVendorListFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">其他补充材料（other，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraOtherFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraOtherFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraOtherFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>
            </>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCpraStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={cpraStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCpraStepIndex((prev) => Math.min(CPRA_STEPS.length - 1, prev + 1))}
              disabled={cpraStepIndex === CPRA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成CPRA合规全景报告"}
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
      {responseData ? (
        <section className="runner-user-result">
          <article className="runner-user-headline">
            <strong>{userFacingResult.headline}</strong>
            {userFacingResult.chips.length > 0 ? (
              <div className="runner-user-chip-row">
                {userFacingResult.chips.map((chip) => (
                  <span key={chip} className="runner-user-chip">{chip}</span>
                ))}
              </div>
            ) : null}
          </article>

          {userFacingResult.deliverables.length > 0 ? (
            <article className="runner-user-block">
              <h4>{lang === "zh" ? "已生成文件" : "Generated Files"}</h4>
              <ul>
                {userFacingResult.deliverablePaths.map((path) => (
                  <li key={path} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                    <span>{toFileName(path)}</span>
                    <span style={{ display: "inline-flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        type="button"
                        className="pill-btn"
                        onClick={() => void openArtifactPath(path)}
                      >
                        {lang === "zh" ? "打开" : "Open"}
                      </button>
                      <button
                        type="button"
                        className="pill-btn"
                        onClick={() => void downloadArtifactPath(path)}
                      >
                        {lang === "zh" ? "下载" : "Download"}
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          ) : null}

          {userFacingResult.highlights.length > 0 ? (
            <article className="runner-user-block">
              <h4>{lang === "zh" ? "关键结果" : "Key Findings"}</h4>
              <ul>
                {userFacingResult.highlights.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </article>
          ) : null}

          <article className="runner-user-block">
            <h4>{lang === "zh" ? "建议下一步" : "Recommended Next Steps"}</h4>
            <ul>
              {userFacingResult.nextSteps.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          </article>
        </section>
      ) : (
        <div className="runner-empty-card">{t("runResultPlaceholder")}</div>
      )}

      <div className="runner-preview-hint">
        {responseData
          ? (lang === "zh" ? "结果已生成，系统会自动切换到“报告”页签进行前端预览。" : "Result generated. The workspace switches to the report tab for preview.")
          : (lang === "zh" ? "运行完成后，报告内容将在“报告”页签中预览。" : "Generated reports will be previewed in the report tab.")}
      </div>
      {error ? <div className="runner-error">{error}</div> : null}
    </section>
    {showCasePicker && devTestCases.length > 0 ? (
      <div style={{ position: "fixed", inset: 0, zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)" }} onClick={() => setShowCasePicker(false)} />
        <div style={{ position: "relative", background: "white", borderRadius: 12, boxShadow: "0 20px 60px rgba(0,0,0,0.3)", width: 520, maxHeight: "70vh", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: 16 }}>🧪 选择测试案例</h3>
            <button onClick={() => setShowCasePicker(false)} style={{ border: "none", background: "none", fontSize: 22, cursor: "pointer", padding: "0 6px", lineHeight: 1 }}>×</button>
          </div>
          <div style={{ overflow: "auto", flex: 1, padding: "4px 0" }}>
            {devTestCases.map((tc, i) => (
              <div key={i} onClick={() => selectDevCase(i)} style={{ padding: "12px 20px", cursor: "pointer", borderBottom: "1px solid #f3f4f6" }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{tc.name}</div>
                <div style={{ fontSize: 11, color: "#6b7280" }}>{tc.description}</div>
              </div>
            ))}
          </div>
          <div style={{ padding: "10px 20px", borderTop: "1px solid #e5e7eb", fontSize: 11, color: "#9ca3af" }}>
            点击案例自动回填表单，随后可编辑再手动运行
          </div>
        </div>
      </div>
    ) : null}
    </>
  );
}
