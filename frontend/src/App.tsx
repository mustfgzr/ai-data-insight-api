import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth";
import { RequireAuth } from "./components";
import { AnalysisDetailPage, AnalysesPage, AuthPage, DatasetDetailPage, DatasetsPage, ReportDetailPage, ReportsPage, UploadPage } from "./pages";

export default function App() {
  return <AuthProvider><BrowserRouter><Routes>
    <Route path="/login" element={<AuthPage mode="login" />} />
    <Route path="/register" element={<AuthPage mode="register" />} />
    <Route element={<RequireAuth />}>
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/datasets" element={<DatasetsPage />} />
      <Route path="/datasets/:id" element={<DatasetDetailPage />} />
      <Route path="/analyses" element={<AnalysesPage />} />
      <Route path="/analyses/:id" element={<AnalysisDetailPage />} />
      <Route path="/reports" element={<ReportsPage />} />
      <Route path="/reports/:id" element={<ReportDetailPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/datasets" replace />} />
  </Routes></BrowserRouter></AuthProvider>;
}
