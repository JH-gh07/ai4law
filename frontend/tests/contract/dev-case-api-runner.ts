import { readFile } from "node:fs/promises";
import { basename, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { ModuleDefinition } from "../../src/api/modules";
import type { DevTestCase } from "../../src/lib/dev-test-cases";

type JsonRecord = Record<string, unknown>;

export type DevCaseSubmissionResult = {
  status: number;
  body: unknown;
};

export type ContractState = {
  manager_count: number;
  submission_count: number;
  external_network_blocked: boolean;
};

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

const isRecord = (value: unknown): value is JsonRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text.trim()) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function postJson(
  baseUrl: string,
  path: string,
  body: unknown,
  token?: string,
): Promise<DevCaseSubmissionResult> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  return { status: response.status, body: await parseResponseBody(response) };
}

export async function registerContractUser(baseUrl: string): Promise<string> {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const result = await postJson(baseUrl, "/api/v1/auth/register", {
    username: `contract-${suffix}`,
    email: `contract-${suffix}@example.com`,
    password: "contract-test-password",
  });
  if (result.status < 200 || result.status >= 300 || !isRecord(result.body)) {
    throw new Error(`Contract user registration failed: HTTP ${result.status} ${JSON.stringify(result.body)}`);
  }
  const token = result.body.access_token;
  if (typeof token !== "string" || !token) {
    throw new Error(`Contract user registration returned no access token: ${JSON.stringify(result.body)}`);
  }
  return token;
}

export async function submitRawContractPayload(options: {
  baseUrl: string;
  endpoint: string;
  payload: unknown;
  token: string;
}): Promise<DevCaseSubmissionResult> {
  return postJson(options.baseUrl, options.endpoint, options.payload, options.token);
}

function mimeForPath(path: string): string {
  const extension = extname(path).toLowerCase();
  if (extension === ".md") return "text/markdown";
  if (extension === ".txt") return "text/plain";
  if (extension === ".csv") return "text/csv";
  if (extension === ".json") return "application/json";
  if (extension === ".pdf") return "application/pdf";
  if (extension === ".docx") {
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }
  return "application/octet-stream";
}

async function uploadReviewFiles(
  baseUrl: string,
  token: string,
  testCase: DevTestCase,
): Promise<string[]> {
  const paths = testCase.backendFilePaths ?? [];
  if (paths.length === 0) {
    throw new Error(`Review case has no backendFilePaths: ${testCase.name}`);
  }

  const uploadedPaths: string[] = [];
  for (const relativePath of paths) {
    const absolutePath = resolve(REPOSITORY_ROOT, relativePath);
    const bytes = await readFile(absolutePath);
    const formData = new FormData();
    formData.append(
      "file",
      new Blob([bytes], { type: mimeForPath(relativePath) }),
      basename(relativePath),
    );
    const response = await fetch(`${baseUrl}/api/v0/files/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    const body = await parseResponseBody(response);
    if (response.status < 200 || response.status >= 300 || !isRecord(body) || !isRecord(body.data)) {
      throw new Error(
        `Review fixture upload failed for ${relativePath}: HTTP ${response.status} ${JSON.stringify(body)}`,
      );
    }
    const storagePath = body.data.path;
    if (typeof storagePath !== "string" || !storagePath) {
      throw new Error(`Review fixture upload returned no storage path: ${JSON.stringify(body)}`);
    }
    uploadedPaths.push(storagePath);
  }
  return uploadedPaths;
}

function assertAcceptedResponse(definition: ModuleDefinition, result: DevCaseSubmissionResult): void {
  if (result.status < 200 || result.status >= 300 || !isRecord(result.body)) return;
  if (definition.asyncSubmitEndpoint) {
    if (typeof result.body.task_id !== "string" || typeof result.body.state !== "string") {
      throw new Error(
        `${definition.key} async endpoint returned an invalid accepted payload: ${JSON.stringify(result.body)}`,
      );
    }
    return;
  }
  if (!("result" in result.body)) {
    throw new Error(`${definition.key} sync endpoint returned no result: ${JSON.stringify(result.body)}`);
  }
}

export async function submitDevTestCase(options: {
  baseUrl: string;
  definition: ModuleDefinition;
  testCase: DevTestCase;
  token: string;
}): Promise<DevCaseSubmissionResult> {
  const { baseUrl, definition, testCase, token } = options;
  const endpoint = definition.asyncSubmitEndpoint ?? definition.syncEndpoint;
  const payload = definition.key === "review"
    ? {
        ...testCase.payload,
        uploaded_files: await uploadReviewFiles(baseUrl, token, testCase),
      }
    : testCase.payload;
  const result = await postJson(baseUrl, endpoint, payload, token);
  assertAcceptedResponse(definition, result);
  return result;
}

export async function fetchContractState(baseUrl: string): Promise<ContractState> {
  const response = await fetch(`${baseUrl}/__contract__/state`);
  const body = await parseResponseBody(response);
  if (response.status !== 200 || !isRecord(body)) {
    throw new Error(`Contract state request failed: HTTP ${response.status} ${JSON.stringify(body)}`);
  }
  if (
    typeof body.manager_count !== "number"
    || typeof body.submission_count !== "number"
    || typeof body.external_network_blocked !== "boolean"
  ) {
    throw new Error(`Contract state returned invalid data: ${JSON.stringify(body)}`);
  }
  return body as ContractState;
}
