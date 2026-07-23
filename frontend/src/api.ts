import type {
  AnalysisDetail,
  AnalysisListItem,
  AdminAnalyst,
  Department,
  DatasetDetail,
  DatasetListItem,
  DatasetRows,
  DatasetUpload,
  Paged,
  ReportDetail,
  ReportListItem,
  SurveyDetection,
  SurveyListItem,
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
  register: (full_name: string, email: string, password: string) =>
    request<User>("/register", { method: "POST", body: JSON.stringify({ full_name, email, password }) }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<User>("/users/me", {}, token),
  changePassword: (current_password: string, new_password: string, token: string) =>
    request<User>("/users/me/password", { method: "POST", body: JSON.stringify({ current_password, new_password }) }, token),
  departments: (token: string) => request<Paged<Department>>("/departments?offset=0&limit=100", {}, token),
  createDepartment: (name: string, token: string) => request<Department & { created: boolean }>("/departments", { method: "POST", body: JSON.stringify({ name }) }, token),
  uploadDataset: (file: File, departmentId: number, token: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("department_id", String(departmentId));
    return request<DatasetUpload>("/datasets/upload", { method: "POST", body: form }, token);
  },
  datasets: (departmentId: number, token: string) => request<Paged<DatasetListItem>>(`/datasets?department_id=${departmentId}&offset=0&limit=50`, {}, token),
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
  analyses: (departmentId: number, token: string) => request<Paged<AnalysisListItem>>(`/analyses?department_id=${departmentId}&offset=0&limit=50`, {}, token),
  analysis: (id: number, token: string) => request<AnalysisDetail>(`/analyses/${id}`, {}, token),
  reports: (departmentId: number, token: string) => request<Paged<ReportListItem>>(`/reports?department_id=${departmentId}&offset=0&limit=50`, {}, token),
  report: (id: number, token: string) => request<ReportDetail>(`/reports/${id}`, {}, token),
  createReport: (payload: { analysis_ids: number[]; department_id: number; title?: string; question?: string }, token: string) =>
    request<ReportDetail>("/reports", { method: "POST", body: JSON.stringify(payload) }, token),
  adminAnalysts: (token: string) => request<Paged<AdminAnalyst>>("/admin/analysts?offset=0&limit=100", {}, token),
  adminAnalyst: (id: number, token: string) => request<AdminAnalyst>(`/admin/analysts/${id}`, {}, token),
  adminDepartments: (id: number, token: string) => request<Paged<Department>>(`/admin/analysts/${id}/departments?offset=0&limit=100`, {}, token),
  adminDatasets: (id: number, departmentId: number, token: string) => request<Paged<DatasetListItem>>(`/admin/analysts/${id}/datasets?department_id=${departmentId}&offset=0&limit=50`, {}, token),
  adminAnalyses: (id: number, departmentId: number, token: string) => request<Paged<AnalysisListItem>>(`/admin/analysts/${id}/analyses?department_id=${departmentId}&offset=0&limit=50`, {}, token),
  adminReports: (id: number, departmentId: number, token: string) => request<Paged<ReportListItem>>(`/admin/analysts/${id}/reports?department_id=${departmentId}&offset=0&limit=50`, {}, token),
  adminSurveys: (id: number, departmentId: number, token: string) => request<Paged<SurveyListItem>>(`/admin/analysts/${id}/surveys?department_id=${departmentId}&offset=0&limit=50`, {}, token),
};
