export type User = { id: number; email: string };

export type ColumnMetadata = {
  name: string;
  dtype: string;
  semantic_type: string;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  sample_values: unknown[];
  code_map: Record<string, unknown>;
};

export type DatasetListItem = {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  detected_format: string;
  row_count: number;
  column_count: number;
  created_at?: string;
};

export type DatasetDetail = DatasetListItem & {
  columns: ColumnMetadata[];
  preview_rows: Record<string, unknown>[];
  survey_id?: number | null;
  latest_analysis_id?: number | null;
  has_source_file: boolean;
};

export type DatasetRows = {
  dataset_id: number;
  offset: number;
  limit: number;
  total: number;
  rows: Record<string, unknown>[];
};

export type SurveyDetection = {
  dataset_id: number;
  detected: boolean;
  status: "detected" | "already_detected" | "not_survey";
  survey_id?: number | null;
  message?: string | null;
};

export type SurveyQuestionScore = {
  question_id: number;
  question_no?: string | null;
  label: string;
  question_text: string;
  score_100?: number | null;
  response_count: number;
  missing_count: number;
  missing_pct: number;
  distribution: Array<{ value: string; label: string; count: number; pct: number }>;
};

export type SurveyGroupScore = {
  label: string;
  score_100?: number | null;
  respondent_count: number;
  low_sample: boolean;
};

export type SurveyResearchChart = {
  id: string;
  type: "bar" | "donut" | string;
  title: string;
  unit: "count" | "score_100" | string;
  data: Array<{ label: string; value: number | null; respondent_count?: number; low_sample?: boolean }>;
};

export type SurveyResearch = {
  survey_id: number;
  report_id: number;
  title: string;
  status: string;
  response_count: number;
  scored_response_count: number;
  likert_question_count: number;
  overall_score_100?: number | null;
  question_scores: SurveyQuestionScore[];
  gender_scores: SurveyGroupScore[];
  age_scores: SurveyGroupScore[];
  neighborhood_scores: SurveyGroupScore[];
  charts: SurveyResearchChart[];
  quality_issues: QualityIssue[];
  ai_report?: string | null;
  ai_report_status: "not_requested" | "completed" | "skipped" | "failed" | string;
  ai_report_warning?: string | null;
  created_at?: string;
};

export type DatasetUpload = {
  dataset_id: number;
  analysis_id: number;
  survey_id?: number | null;
  filename: string;
  detected_format: string;
  row_count: number;
  column_count: number;
  columns: ColumnMetadata[];
  statistics: Record<string, unknown>;
  charts: ChartPayload[];
  quality_issues: QualityIssue[];
  summary: string;
};

export type ChartPayload = {
  title?: string;
  type?: string;
  labels?: string[];
  values?: number[];
  data?: Array<{ label?: string; value?: number }>;
};

export type QualityIssue = {
  severity?: string;
  title?: string;
  message?: string;
  column?: string;
  [key: string]: unknown;
};

export type AnalysisListItem = {
  id: number;
  filename: string;
  template: string;
  row_count: number;
  column_count: number;
  dataset_id?: number | null;
  analysis_type?: string | null;
  status?: string | null;
  summary?: string | null;
  question?: string | null;
  created_at?: string;
};

export type AnalysisDetail = AnalysisListItem & {
  columns_info: ColumnMetadata[];
  statistics: Record<string, unknown>;
  ai_report: string | null;
  ai_report_status: "completed" | "skipped" | "failed";
  ai_report_warning?: string | null;
  chart_data: ChartPayload[];
  quality_issues: QualityIssue[];
};

export type ReportListItem = {
  id: number;
  title: string;
  status: string;
  analysis_ids: number[];
  created_at?: string;
};

export type ReportDetail = ReportListItem & {
  content?: string | null;
  error_message?: string | null;
  model_name?: string | null;
};
