export type UserFacingResult = {
  headline: string;
  chips: string[];
  deliverables: string[];
  deliverablePaths: string[];
  highlights: string[];
  nextSteps: string[];
};

export type AutoExtractResult = {
  documentTitle: string;
  documentType: DocumentReviewFormValues["document_type"];
  reviewFocus: string;
  transferPurpose: string;
  sensitivePiDisclosed: boolean;
  rightsChannelDisclosed: boolean;
  crossborderRuleDisclosed: boolean;
  contactChannel: string;
  note: string;
};

export type DocumentReviewExtractState = {
  status: "loading" | "done" | "error";
  note: string;
};

export type AsyncRunProgressState = {
  state: string;
  progress?: number;
};

export type DiagnosisOption = {
  value: string;
  label: string;
  extraFieldId?: string;
  extraPlaceholder?: string;
};

export type DiagnosisFieldType = "text" | "textarea" | "single" | "multi";

export type DiagnosisFieldConfig = {
  name: string;
  label: string;
  type: DiagnosisFieldType;
  group?: string;
  options?: DiagnosisOption[];
  visibleWhen?: (answers: DiagnosisFormValues) => boolean;
};

export type DiagnosisStepConfig = {
  title: string;
  fields: DiagnosisFieldConfig[];
};

export type DiagnosisFormValues = Record<string, unknown>;

export type AssessmentFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

export type AssessmentFieldConfig = {
  name: keyof AssessmentFormValues;
  label: string;
  type: AssessmentFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

export type AssessmentStepConfig = {
  title: string;
  fields: AssessmentFieldConfig[];
};

export type AssessmentFormValues = {
  company_name: string;
  company_uscc: string;
  legal_representative: string;
  registered_address: string;
  company_nature: string;
  industry: string;
  assessment_start_date: string;
  assessment_end_date: string;
  lead_department: string;
  participant_departments: string;
  third_party_support: boolean;
  third_party_name: string;
  third_party_scope: string;
  scenario_name: string;
  receiver_name: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  is_long_term: boolean;
  legal_basis: string;
  necessity_basis: string;
  receiver_country: string;
  is_ciio: boolean;
  contains_important_data: boolean;
  pii_count: number;
  spi_count: number;
  transfer_purpose: string;
  data_inventory_summary: string;
  system_chain_summary: string;
  security_capability_summary: string;
  force_override_path: boolean;
};

export type PipiaRouteType = "scc_filing" | "certification";

export type PipiaAttachmentRole = "scc_contract" | "certification_material" | "internal_policy" | "supporting_evidence";

export type PipiaFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

export type PipiaFieldConfig = {
  name: keyof PipiaFormValues;
  label: string;
  type: PipiaFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

export type PipiaStepConfig = {
  title: string;
  fields: PipiaFieldConfig[];
};

export type PipiaFormValues = {
  company_name: string;
  company_uscc: string;
  industry: string;
  shareholding_structure: string;
  actual_controller: string;
  overseas_investment: string;
  org_structure_privacy_team: string;
  business_overview: string;
  processing_activity_overview: string;
  is_ciio: boolean;
  processing_person_count: number;
  outbound_pi_count: number;
  outbound_spi_count: number;
  route_type: PipiaRouteType;
  outbound_scenario_name: string;
  outbound_frequency: "one_time" | "periodic" | "continuous";
  transfer_method: string;
  domestic_storage: string;
  overseas_storage: string;
  transfer_link: string;
  purpose: string;
  recipient_name: string;
  recipient_country_region: string;
  legal_basis: string;
  legality_justification: string;
  necessity_justification: string;
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

export type DocumentReviewFormValues = {
  company_name: string;
  document_title: string;
  document_version: string;
  effective_date: string;
  applicable_products: string;
  applicable_scope: string;
  publisher_entity: string;
  is_live_version: boolean;
  document_type: "privacy_policy" | "scc_contract" | "dpa" | "other";
  receiver_name: string;
  receiver_country: string;
  transfer_purpose: string;
  processor_identity_disclosed: boolean;
  scope_disclosed: boolean;
  collection_purpose_disclosed: boolean;
  processing_method_disclosed: boolean;
  category_disclosed: boolean;
  sensitive_pi_disclosed: boolean;
  crossborder_rule_disclosed: boolean;
  rights_channel_disclosed: boolean;
  contact_channel: string;
  pii_count: number;
  spi_count: number;
  has_scc_draft: boolean;
  review_focus: string;
};

export type EuSccFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

export type EuSccFieldConfig = {
  name: keyof EuSccFormValues;
  label: string;
  type: EuSccFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

export type EuSccStepConfig = {
  title: string;
  fields: EuSccFieldConfig[];
};

export type EuSccFormValues = {
  project_name_override?: string;
  scc_text_override?: string;
  exporter_name: string;
  importer_name: string;
  importer_country: string;
  transfer_role: "c2c" | "c2p" | "p2p" | "p2c";
  scc_version: "eu_2021" | "other";
  transfer_purpose: string;
  data_categories: string;
  data_subject_categories: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  retention_rule: string;
  tom_summary: string;
  onward_transfer_control: string;
  rights_and_complaint: string;
  government_access_response: string;
  supplementary_clause_review: string;
  pii_count: number;
  spi_count: number;
  has_scc_draft: boolean;
};

export type BcrFieldType = "text" | "textarea" | "select";

export type BcrFieldConfig = {
  name: keyof BcrFormValues;
  label: string;
  type: BcrFieldType;
  options?: string[];
};

export type BcrStepConfig = {
  title: string;
  fields: BcrFieldConfig[];
};

export type BcrFormValues = {
  company_name: string;
  group_structure: string;
  applicant_entity: string;
  data_flow_scope: string;
  lead_sa_rationale: string;
  binding_mechanism: string;
  third_party_beneficiary: string;
  liability_compensation: string;
  transparency_notice: string;
  training_audit: string;
  cooperation_with_sa: string;
  dp_safeguards: string;
  third_country_assessment: string;
  government_access_process: string;
  update_mechanism: string;
  definitions_quality: string;
  review_focus: string;
};

export type DpiaFieldType = "text" | "textarea" | "select" | "checkbox";

export type DpiaFieldConfig = {
  name: keyof DpiaFormValues;
  label: string;
  type: DpiaFieldType;
  options?: string[];
};

export type DpiaStepConfig = {
  title: string;
  fields: DpiaFieldConfig[];
};

export type DpiaFormValues = {
  project_name: string;
  project_goal: string;
  need_reason: string;
  controller_name: string;
  dpo_role: string;
  contact_channel: string;
  processing_description: string;
  data_types: string;
  includes_special_data: boolean;
  subject_scale: string;
  frequency: string;
  retention_period: string;
  geo_scope: string;
  has_crossborder_transfer: boolean;
  data_source: string;
  relationship_context: string;
  expectation_control: string;
  vulnerable_group: string;
  prior_concerns: string;
  novel_technology: string;
  lawful_basis: string;
  purpose_and_necessity: string;
  function_creep_control: string;
  minimization_quality: string;
  notice_plan: string;
  rights_support: string;
  processor_management: string;
  risk_assessment: string;
  mitigation_measures: string;
  residual_risk: string;
  signoff_owner: string;
  dpo_advice: string;
  review_schedule: string;
  attachment_role: "data_flow_diagram" | "security_policy" | "dpa" | "other";
};

export type TiaFieldType = "text" | "textarea" | "select" | "checkbox";

export type TiaFieldConfig = {
  name: keyof TiaFormValues;
  label: string;
  type: TiaFieldType;
  options?: string[];
};

export type TiaStepConfig = {
  title: string;
  fields: TiaFieldConfig[];
};

export type TiaFormValues = {
  data_exporter_name: string;
  data_importer_name: string;
  importer_country_region: string;
  transfer_purpose: string;
  data_categories: string;
  sensitive_data_description: string;
  data_subject_categories: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  transfer_tool: "scc" | "bcr" | "derogation";
  law_assessed: boolean;
  law_findings: string;
  pre_effectiveness: string;
  supplementary_technical: string;
  supplementary_contractual: string;
  supplementary_organizational: string;
  post_effectiveness: string;
  key_actions: string;
  dpo_opinion: string;
  review_date: string;
  attachment_role: "transfer_agreement" | "country_law_analysis" | "technical_control_doc" | "other";
};

export type CnFlowRecipientRole = "processor" | "controller" | "subprocessor" | "affiliate" | "vendor";

export type CnFlowFieldType = "text" | "textarea" | "select" | "checkbox";

export type CnFlowFieldConfig = {
  name: keyof CnFlowFormValues;
  label: string;
  type: CnFlowFieldType;
  options?: string[];
};

export type CnFlowStepConfig = {
  title: string;
  fields: CnFlowFieldConfig[];
};

export type CnFlowFormValues = {
  company_name: string;
  transfer_purpose: string;
  data_categories: string;
  sensitive_data_flags: string;
  transfer_chain: string;
  data_volume_note: string;
  necessity_justification: string;
  primary_recipient_name: string;
  primary_recipient_country: string;
  primary_recipient_role: CnFlowRecipientRole;
  primary_recipient_restricted: boolean;
  additional_recipients: string;
  internal_access_note: string;
};

export type Us14117FieldType = "text" | "textarea" | "number" | "checkbox" | "select";

export type Us14117FieldConfig = {
  name: keyof Us14117FormValues;
  label: string;
  type: Us14117FieldType;
  options?: string[];
  min?: number;
  step?: number;
};

export type Us14117StepConfig = {
  title: string;
  fields: Us14117FieldConfig[];
};

export type Us14117FormValues = {
  data_items_override?: ModuleRequestMap["us_14117"]["data_items"];
  recipient_entities_override?: ModuleRequestMap["us_14117"]["recipient_entities"];
  access_persons_override?: NonNullable<ModuleRequestMap["us_14117"]["access_persons"]>;
  security_measures_override?: NonNullable<ModuleRequestMap["us_14117"]["security_measures"]>;
  company_name: string;
  project_name: string;
  transaction_description: string;
  transaction_type: string;
  data_item_name: string;
  data_description: string;
  doj_data_category: string;
  us_person_count: number;
  entity_name: string;
  country_of_registration: string;
  government_control: boolean;
  entity_role: string;
  onward_transfer: boolean;
  onward_transfer_description: string;
  security_measures_summary: string;
  review_focus: string;
};

export type CpraFieldType = "text" | "textarea" | "checkbox";

export type CpraFieldConfig = {
  name: keyof CpraFormValues;
  label: string;
  type: CpraFieldType;
};

export type CpraStepConfig = {
  title: string;
  fields: CpraFieldConfig[];
};

export type CpraFormValues = {
  company_name: string;
  dba_name: string;
  cpra_applicability_selfcheck: string;
  business_model: string;
  data_lifecycle: string;
  data_categories: string;
  notice_and_consent: string;
  privacy_policy_url: string;
  consumer_rights_process: string;
  identity_verification_method: string;
  rights_sla: string;
  opt_out_and_sale_sharing: string;
  spi_usage_summary: string;
  vendor_management: string;
  ui_dark_pattern_check: string;
  review_focus: string;
};
import type { ModuleRequestMap } from "../../api/api-contract";
