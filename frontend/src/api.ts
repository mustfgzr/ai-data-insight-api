import type {
  AnalysisDetail,
  AnalysisListItem,
  DatasetDetail,
  DatasetListItem,
  DatasetRows,
  DatasetUpload,
  ReportDetail,
  ReportListItem,
  SurveyDetection,
  SurveyResearch,
  User,
} from "./types";

const API_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = "Bir istek hatasi olustu.";
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // The API did not return a JSON error payload.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<User>("/users/me", {}, token),
  uploadDataset: (file: File, token: string) => {
    const form = new FormData();
    form.append("file", file);
    return request<DatasetUpload>("/datasets/upload", { method: "POST", body: form }, token);
  },
  datasets: (token: string) => request<{ items: DatasetListItem[]; total: number }>("/datasets", {}, token),
  dataset: (id: number, token: string) => request<DatasetDetail>(`/datasets/${id}`, {}, token),
  datasetRows: (id: number, offset: number, token: string) =>
    request<DatasetRows>(`/datasets/${id}/rows?offset=${offset}&limit=50`, {}, token),
  downloadUrl: (id: number) => `${API_URL}/datasets/${id}/download`,
  analyzeDataset: (id: number, token: string, payload: { template?: string; question?: string } = {}) =>
    request<AnalysisDetail>(`/datasets/${id}/analyses`, { method: "POST", body: JSON.stringify(payload) }, token),
  detectSurvey: (id: number, token: string) =>
    request<SurveyDetection>(`/datasets/${id}/detect-survey`, { method: "POST" }, token),
  surveyResearch: (id: number, token: string) => request<SurveyResearch>(`/surveys/${id}/research`, {}, token),
  refreshSurveyResearch: (id: number, token: string) =>
    request<SurveyResearch>(`/surveys/${id}/research/refresh`, { method: "POST" }, token),
  createSurveyAiSummary: (id: number, token: string) =>
    request<SurveyResearch>(`/surveys/${id}/research/ai-summary`, { method: "POST" }, token),
  analyses: (token: string) => request<AnalysisListItem[]>("/analyses", {}, token),
  analysis: (id: number, token: string) => request<AnalysisDetail>(`/analyses/${id}`, {}, token),
  reports: (token: string) => request<ReportListItem[]>("/reports", {}, token),
  report: (id: number, token: string) => request<ReportDetail>(`/reports/${id}`, {}, token),
  createReport: (payload: { analysis_ids: number[]; title?: string; question?: string }, token: string) =>
    request<ReportDetail>("/reports", { method: "POST", body: JSON.stringify(payload) }, token),
};
