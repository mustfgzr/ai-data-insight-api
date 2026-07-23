import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth";
import { DepartmentProvider } from "./department";
import { RequireAdmin, RequireAnalyst, RequireAuth } from "./components";
import { AdminPage, AnalysisDetailPage, AnalysesPage, AuthPage, DatasetDetailPage, DatasetsPage, LoginChoicePage, PasswordChangePage, ReportDetailPage, ReportsPage, SurveyResearchPage, UploadPage } from "./pages";

export default function App() {
  return <AuthProvider><DepartmentProvider><BrowserRouter><Routes>
    <Route path="/login" element={<LoginChoicePage />} />
    <Route path="/login/analyst" element={<AuthPage mode="login" entry="analyst" />} />
    <Route path="/login/admin" element={<AuthPage mode="login" entry="admin" />} />
    <Route path="/register" element={<AuthPage mode="register" />} />
    <Route path="/change-password" element={<PasswordChangePage />} />
    <Route element={<RequireAuth />}>
      <Route element={<RequireAnalyst />}>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/datasets/:id" element={<DatasetDetailPage />} />
        <Route path="/surveys/:id/research" element={<SurveyResearchPage />} />
        <Route path="/analyses" element={<AnalysesPage />} />
        <Route path="/analyses/:id" element={<AnalysisDetailPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:id" element={<ReportDetailPage />} />
      </Route>
      <Route element={<RequireAdmin />}><Route path="/admin" element={<AdminPage />} /></Route>
    </Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes></BrowserRouter></DepartmentProvider></AuthProvider>;
}
