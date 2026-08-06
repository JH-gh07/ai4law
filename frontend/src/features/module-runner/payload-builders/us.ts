import type { ModuleRequestMap } from "../../../api/api-contract";
import type { Us14117FormValues } from "../model";
import { requireAllowedValue, requireFileExtensions, requireText } from "./common";

const US_14117_TRANSACTION_TYPES = [
  "vendor_agreement",
  "employment_agreement",
  "investment_agreement",
  "data_brokerage",
  "cooperative_research",
  "cloud_remote_access",
  "onward_transfer",
  "other",
] as const;
const US_14117_FILE_EXTENSIONS = ["txt", "md", "json", "csv", "pdf", "docx"] as const;

export function buildUs14117Payload(
  values: Us14117FormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["us_14117"] {
  requireText(values.company_name, "company_name");
  requireText(values.project_name, "project_name");
  requireText(values.transaction_description, "transaction_description");
  requireText(values.data_item_name, "data_item_name");
  requireText(values.entity_name, "entity_name");
  requireText(values.country_of_registration, "country_of_registration");
  requireAllowedValue(values.transaction_type, "transaction_type", US_14117_TRANSACTION_TYPES);
  requireFileExtensions(resolvedFilePaths, US_14117_FILE_EXTENSIONS);

  return {
    company_name: values.company_name.trim(),
    project_name: values.project_name.trim(),
    transaction_description: values.transaction_description.trim(),
    transaction_type: values.transaction_type,
    attachments: [...resolvedFilePaths],
    data_items: [{
      data_item_name: values.data_item_name.trim(),
      data_description: values.data_description.trim(),
      doj_data_category: values.doj_data_category,
      us_person_count: Math.max(0, values.us_person_count),
    }],
    recipient_entities: [{
      entity_name: values.entity_name.trim(),
      country_of_registration: values.country_of_registration.trim(),
      government_control: values.government_control,
      entity_role: values.entity_role,
    }],
    security_measures: values.security_measures_summary.trim()
      ? [{
        measure_name: values.security_measures_summary.trim().slice(0, 80),
        category: "access_control",
        status: "implemented",
        description: values.security_measures_summary.trim(),
      }]
      : [],
    onward_transfer: values.onward_transfer,
    onward_transfer_description: values.onward_transfer_description.trim(),
  };
}
