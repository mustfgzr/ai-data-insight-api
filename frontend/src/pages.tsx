import { useEffect, useRef, useState, type DragEvent } from "react";
import { BarChart3, Download, FilePlus2, FileText, LoaderCircle, Plus, Sparkles, UploadCloud } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "./api";
import { useAuth } from "./auth";
import { useDepartment } from "./department";
import { EmptyState, ErrorNotice, MiniBarChart, PageHeader, StatusPill, SurveyResearchChart } from "./components";
import type { AdminAnalyst, AnalysisDetail, AnalysisListItem, DatasetDetail, DatasetListItem, DatasetRows, DatasetUpload, Department, ReportDetail, ReportListItem, SurveyGroupScore, SurveyListItem, SurveyResearch } from "./types";

const formatDate = (value?: string) => value ? new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
const formatValue = (value: unknown) => value === null || value === undefined || value === "" ? "-" : typeof value === "object" ? JSON.stringify(value) : String(value);
const formatScore = (value?: number | null) => value === null || value === undefined ? "-" : value.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
const loadError = (error: unknown) => error instanceof Error ? error.message : "Veriler yuklenirken bir hata olustu.";

export function LoginChoicePage() {
  return <div className="auth-layout"><section className="auth-intro"><div className="auth-mark">DI</div><h1>Data Insight</h1><p>Belediye hizmet anketlerini guvenli, mudurluk bazli calisma alanlarinda analiz edin.</p></section><main className="auth-panel"><div className="auth-form"><div><p className="eyebrow">GIRIS SECENEKLERI</p><h2>Calisma alaninizi secin</h2></div><Link className="primary-button full" to="/login/analyst">Veri Analisti Girisi</Link><Link className="secondary-button full" to="/login/admin">Yonetici Girisi</Link><p className="form-switch">Veri analisti hesabi mi gerekli? <Link to="/register">Kayit olun</Link></p></div></main></div>;
}

export function AuthPage({ mode, entry }: { mode: "login" | "register"; entry?: "analyst" | "admin" }) {
  const { token, signIn, register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  if (token) return <Navigate to="/datasets" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setPending(true);
    try { const user = mode === "login" ? await signIn(email, password) : await register(fullName, email, password); navigate(user.role === "admin" ? (user.must_change_password ? "/change-password" : "/admin") : "/datasets"); }
    catch (err) { setError(loadError(err)); }
    finally { setPending(false); }
  };
  const isLogin = mode === "login";
  return <div className="auth-layout"><section className="auth-intro"><div className="auth-mark">DI</div><h1>Data Insight</h1><p>Anket ve veri setlerinizi yukleyin, kalite sinyallerini gorun, analizleri tek yerde yonetin.</p><div className="intro-metrics"><span>CSV</span><span>XLSX</span><span>JWT</span><span>Gemini</span></div></section>
    <main className="auth-panel"><form className="auth-form" onSubmit={submit}><div><p className="eyebrow">{isLogin ? entry === "admin" ? "YONETICI GIRISI" : "VERI ANALISTI GIRISI" : "YENI ANALIST HESABI"}</p><h2>{isLogin ? "Hesabiniza girin" : "Calisma alaninizi olusturun"}</h2><p>{isLogin ? "Rolunuz dogrulanarak uygun calisma alanina yonlendirileceksiniz." : "Veri analizlerinizi guvenli bir alanda yonetin."}</p></div>
      {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
      {!isLogin && <label>Ad soyad<input value={fullName} onChange={(e) => setFullName(e.target.value)} required /></label>}
      <label>E-posta<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>Sifre<input type="password" autoComplete={isLogin ? "current-password" : "new-password"} minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      <button className="primary-button full" disabled={pending}>{pending && <LoaderCircle className="spin" size={17} />}{isLogin ? "Giris yap" : "Kayit ol"}</button>
      <p className="form-switch">{isLogin ? "Hesabiniz yok mu?" : "Zaten hesabiniz var mi?"} <Link to={isLogin ? "/register" : "/login"}>{isLogin ? "Kayit olun" : "Giris secenekleri"}</Link></p>
    </form></main></div>;
}

export function UploadPage() {
  const { token } = useAuth();
  const { departments, selected, select: selectDepartment, refresh } = useDepartment();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DatasetUpload | null>(null);
  const [newDepartment, setNewDepartment] = useState("");
  const navigate = useNavigate();
  const selectFile = (candidate?: File) => {
    setError(""); setResult(null);
    if (!candidate) return;
    if (!/\.(csv|xlsx)$/i.test(candidate.name)) { setFile(null); setError("Yalnizca CSV veya XLSX dosyalari yuklenebilir."); return; }
    setFile(candidate);
  };
  const dropped = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]); };
  const submit = async () => {
    if (!file || !token || !selected) return; setPending(true); setError("");
    try { setResult(await api.uploadDataset(file, selected.id, token)); }
    catch (err) { setError(loadError(err)); }
    finally { setPending(false); }
  };
  const createDepartment = async () => { if (!token || !newDepartment.trim()) return; setPending(true); try { const department = await api.createDepartment(newDepartment, token); await refresh(); selectDepartment(department); setNewDepartment(""); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  return <div className="page"><PageHeader title="Veri seti yukle" detail="CSV veya XLSX dosyanizi yukleyin. Kolonlar, kalite sinyalleri ve temel analiz otomatik olusturulur." />
    <section className="upload-layout"><div className="upload-main"><div className="department-control"><label>Mudurluk<select value={selected?.id ?? ""} onChange={(e) => selectDepartment(departments.find((item) => item.id === Number(e.target.value)) ?? null)} required><option value="">Mudurluk secin</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label><div><input aria-label="Yeni mudurluk" placeholder="Yeni mudurluk adi" value={newDepartment} onChange={(e) => setNewDepartment(e.target.value)} /><button className="secondary-button" onClick={createDepartment} disabled={pending || !newDepartment.trim()}>Ekle</button></div></div><div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropped} onClick={() => input.current?.click()} role="button" tabIndex={0}>
      <UploadCloud size={38} strokeWidth={1.4} /><h2>{file ? file.name : "Dosyanizi buraya birakin"}</h2><p>{file ? `${(file.size / 1024).toFixed(1)} KB secildi` : "veya bilgisayarinizdan secin"}</p><span className="secondary-button">Dosya sec</span><input ref={input} type="file" accept=".csv,.xlsx" onChange={(e) => selectFile(e.target.files?.[0])} hidden />
    </div>{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    <button className="primary-button upload-submit" disabled={!file || !selected || pending} onClick={submit}>{pending && <LoaderCircle className="spin" size={17} />}{pending ? "Isleniyor..." : "Analizi baslat"}</button></div>
      <aside className="upload-notes"><h2>Yukleme kapsami</h2><dl><div><dt>Desteklenen</dt><dd>CSV ve XLSX</dd></div><div><dt>Otomatik cikarim</dt><dd>Kolon, tip, eksik deger, ornek deger</dd></div><div><dt>Anket tanima</dt><dd>Soru, secenek ve dagilimlar</dd></div><div><dt>Sinirlar</dt><dd>20 MB, 10.000 satir, 300 kolon</dd></div></dl></aside>
    </section>
    {result && <section className="result-panel"><div><p className="eyebrow">YUKLEME TAMAMLANDI</p><h2>{result.filename}</h2><p>{result.summary}</p></div><div className="metric-grid"><Metric label="Satir" value={result.row_count} /><Metric label="Kolon" value={result.column_count} /><Metric label="Uyari" value={result.quality_issues.length} /></div><div className="result-actions"><button className="secondary-button" onClick={() => navigate(`/datasets/${result.dataset_id}`)}>Veri setini gor</button>{result.survey_id ? <button className="primary-button" onClick={() => navigate(`/surveys/${result.survey_id}/research`)}>Anket arastirmasi</button> : <button className="primary-button" onClick={() => navigate(`/analyses/${result.analysis_id}`)}>Analizi gor</button>}</div></section>}
  </div>;
}

export function DatasetsPage() {
  const { token } = useAuth(); const { selected } = useDepartment(); const [items, setItems] = useState<DatasetListItem[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const refresh = () => { if (!token || !selected) return; setLoading(true); api.datasets(selected.id, token).then((result) => setItems(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); };
  useEffect(refresh, [token, selected?.id]);
  if (!selected) return <DepartmentGate title="Veri setleri" detail="Once calisacaginiz mudurlugu secin." />;
  return <div className="page"><PageHeader title="Veri setleri" detail="Yuklediginiz dosyalara, yapilarina ve kaynak dosyalarina buradan ulasin." actions={<Link className="primary-button" to="/upload"><FilePlus2 size={17} />Veri seti yukle</Link>} />
    {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz veri seti yok" detail="Ilk CSV veya XLSX dosyanizi yukleyerek analize baslayin." action={<Link className="primary-button" to="/upload">Dosya yukle</Link>} /> : <section className="data-table-wrap"><table className="data-table"><thead><tr><th>Dosya</th><th>Tur</th><th>Yapi</th><th>Olusturulma</th><th></th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.original_filename}</strong><small>ID #{item.id}</small></td><td><span className="file-badge">{item.file_type.toUpperCase()}</span></td><td>{item.row_count} satir <span className="muted">/</span> {item.column_count} kolon</td><td>{formatDate(item.created_at)}</td><td><Link className="table-link" to={`/datasets/${item.id}`}>Ac</Link></td></tr>)}</tbody></table></section>}
  </div>;
}

export function DatasetDetailPage() {
  const { id } = useParams(); const datasetId = Number(id); const { token, user } = useAuth(); const location = useLocation(); const adminReturn = (location.state as { adminReturn?: string } | null)?.adminReturn ?? "/admin"; const isAdmin = user?.role === "admin"; const [dataset, setDataset] = useState<DatasetDetail | null>(null); const [rows, setRows] = useState<DatasetRows | null>(null); const [error, setError] = useState(""); const [actionError, setActionError] = useState(""); const [actionMessage, setActionMessage] = useState(""); const [actionPending, setActionPending] = useState(false); const navigate = useNavigate();
  const refresh = () => { if (!token || !datasetId) return; Promise.all([api.dataset(datasetId, token), api.datasetRows(datasetId, 0, token)]).then(([detail, page]) => { setDataset(detail); setRows(page); }).catch((err) => setError(loadError(err))); };
  useEffect(refresh, [token, datasetId]);
  const createAnalysis = async () => { if (!token) return; setActionPending(true); setActionError(""); try { const analysis = await api.analyzeDataset(datasetId, token); navigate(`/analyses/${analysis.id}`); } catch (err) { setActionError(loadError(err)); } finally { setActionPending(false); } };
  const detectSurvey = async () => { if (!token) return; setActionPending(true); setActionError(""); try { const result = await api.detectSurvey(datasetId, token); setActionMessage(result.message || (result.detected ? "Anket algilandi." : "Anket yapisi bulunamadi.")); refresh(); } catch (err) { setActionError(loadError(err)); } finally { setActionPending(false); } };
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to={isAdmin ? adminReturn : "/datasets"}>Listeye don</Link></div>;
  if (!dataset) return <Loading />;
  const headers = rows?.rows.length ? Object.keys(rows.rows[0]) : dataset.columns.map((column) => column.name);
  return <div className="page"><PageHeader title={dataset.original_filename} detail={`${dataset.row_count} satir, ${dataset.column_count} kolon, ${dataset.detected_format} formati`} actions={<div className="header-actions">{isAdmin && <Link className="secondary-button" to={adminReturn}>Yonetici alanina don</Link>}{dataset.has_source_file && <a className="secondary-button" href={api.downloadUrl(dataset.id)} target="_blank" rel="noreferrer"><Download size={16} />Kaynak dosya</a>}{dataset.survey_id && <Link className="primary-button" to={`/surveys/${dataset.survey_id}/research`} state={isAdmin ? { adminReturn } : undefined}><BarChart3 size={16} />Anket arastirmasi</Link>}{dataset.latest_analysis_id && <Link className="secondary-button" to={`/analyses/${dataset.latest_analysis_id}`} state={isAdmin ? { adminReturn } : undefined}>Son analiz</Link>}{!isAdmin && !dataset.survey_id && <button className="secondary-button" onClick={detectSurvey} disabled={actionPending}>Anket algila</button>}{!isAdmin && <button className="secondary-button" onClick={createAnalysis} disabled={actionPending}>{actionPending && <LoaderCircle className="spin" size={16} />}Yeni analiz</button>}</div>} />
    {actionError && <ErrorNotice message={actionError} onDismiss={() => setActionError("")} />}{actionMessage && <p className="muted">{actionMessage}</p>}
    <section className="metric-grid top-metrics"><Metric label="Veri tipi" value={dataset.file_type.toUpperCase()} /><Metric label="Anket" value={dataset.survey_id ? "Algilandi" : "Genel veri"} /><Metric label="Satir" value={dataset.row_count} /><Metric label="Kolon" value={dataset.column_count} /></section>
    <section className="split-section"><div><h2>Kolon yapisi</h2><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Kolon</th><th>Tip</th><th>Anlam</th><th>Eksik</th><th>Benzersiz</th><th>Ornekler</th></tr></thead><tbody>{dataset.columns.map((column) => <tr key={column.name}><td><strong>{column.name}</strong></td><td>{column.dtype}</td><td>{column.semantic_type}</td><td>{column.missing_pct.toFixed(1)}%</td><td>{column.unique_count}</td><td className="sample-cell">{column.sample_values.slice(0, 3).map(formatValue).join(", ") || "-"}</td></tr>)}</tbody></table></div></div></section>
    <section><h2>Satir onizlemesi</h2>{rows?.rows.length ? <div className="data-table-wrap"><table className="data-table compact"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.rows.map((row, index) => <tr key={index}>{headers.map((header) => <td key={header}>{formatValue(row[header])}</td>)}</tr>)}</tbody></table></div> : <p className="muted">Gosterilecek satir yok.</p>}</section>
  </div>;
}

export function SurveyResearchPage() {
  const { id } = useParams(); const surveyId = Number(id); const { token, user } = useAuth(); const location = useLocation(); const adminReturn = (location.state as { adminReturn?: string } | null)?.adminReturn ?? "/admin"; const isAdmin = user?.role === "admin"; const [research, setResearch] = useState<SurveyResearch | null>(null); const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  const load = () => { if (!token || !surveyId) return; api.surveyResearch(surveyId, token).then(setResearch).catch((err) => setError(loadError(err))); };
  useEffect(load, [token, surveyId]);
  const refresh = async () => { if (!token) return; setPending(true); setError(""); try { setResearch(await api.refreshSurveyResearch(surveyId, token)); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  const createAiSummary = async () => { if (!token) return; setPending(true); setError(""); try { setResearch(await api.createSurveyAiSummary(surveyId, token)); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  if (error && !research) return <div className="page"><PageHeader title="Anket arastirmasi" detail="Kayitli anket verilerinden sayisal bulgular." actions={!isAdmin ? <button className="primary-button" onClick={refresh} disabled={pending}>{pending && <LoaderCircle className="spin" size={16} />}Arastirmayi hazirla</button> : undefined} /><ErrorNotice message={error} /><Link className="secondary-button" to={isAdmin ? adminReturn : "/datasets"}>Listeye don</Link></div>;
  if (!research) return <Loading />;
  return <div className="page"><PageHeader title={research.title} detail="Sayisal anket arastirmasi. AI ozeti istege bagli ve bu hesaplamalardan ayri tutulur." actions={<div className="header-actions">{isAdmin ? <Link className="secondary-button" to={adminReturn}>Yonetici alanina don</Link> : <><button className="secondary-button" onClick={refresh} disabled={pending}>{pending && <LoaderCircle className="spin" size={16} />}Yenile</button><button className="primary-button" onClick={createAiSummary} disabled={pending}>{pending && <LoaderCircle className="spin" size={16} />}<Sparkles size={16} />AI ozeti olustur</button></>}</div>} />
    {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    <SurveyResearchContent research={research} />
  </div>;
}

export function AnalysesPage() {
  const { token } = useAuth(); const { selected: department } = useDepartment(); const [items, setItems] = useState<AnalysisListItem[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const [selected, setSelected] = useState<number[]>([]); const [title, setTitle] = useState(""); const [question, setQuestion] = useState(""); const [pending, setPending] = useState(false); const navigate = useNavigate();
  useEffect(() => { if (!token || !department) return; api.analyses(department.id, token).then((result) => setItems(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); }, [token, department?.id]);
  const toggle = (analysisId: number) => setSelected((current) => current.includes(analysisId) ? current.filter((id) => id !== analysisId) : current.length < 5 ? [...current, analysisId] : current);
  const createReport = async () => { if (!token || !department || selected.length === 0) return; setPending(true); setError(""); try { const report = await api.createReport({ analysis_ids: selected, department_id: department.id, title: title || undefined, question: question || undefined }, token); navigate(`/reports/${report.id}`); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  if (!department) return <DepartmentGate title="Analizler" detail="Once calisacaginiz mudurlugu secin." />;
  return <div className="page"><PageHeader title="Analizler" detail="Kaydedilen analizleri inceleyin veya en fazla bes tanesini secerek ortak bir Gemini raporu olusturun." />{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz analiz yok" detail="Bir veri seti yuklediginizde temel analiz otomatik olusturulur." action={<Link className="primary-button" to="/upload">Veri seti yukle</Link>} /> : <><section className="report-builder"><div><p className="eyebrow">RAPOR OLUSTUR</p><h2>{selected.length} analiz secildi</h2><p>Secili analizlerin yapilandirilmis istatistikleri Gemini ile degerlendirilir.</p></div><div className="report-inputs"><input aria-label="Rapor basligi" placeholder="Rapor basligi (istege bagli)" value={title} onChange={(e) => setTitle(e.target.value)} /><input aria-label="Rapor sorusu" placeholder="Rapor sorusu veya odak noktasi" value={question} onChange={(e) => setQuestion(e.target.value)} /></div><button className="primary-button" disabled={!selected.length || pending} onClick={createReport}>{pending ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{pending ? "Olusturuluyor" : "Rapor olustur"}</button></section>
      <section className="analysis-list">{items.map((item) => <label className={`analysis-card ${selected.includes(item.id) ? "selected" : ""}`} key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} /><div><div className="analysis-title"><strong>{item.filename}</strong><StatusPill value={item.status} /></div><p>{item.summary || "Otomatik veri seti analizi"}</p><small>{item.row_count} satir, {item.column_count} kolon | {formatDate(item.created_at)}</small></div><Link className="table-link" to={`/analyses/${item.id}`} onClick={(event) => event.stopPropagation()}>Detay</Link></label>)}</section></>}
  </div>;
}

export function AnalysisDetailPage() {
  const { id } = useParams(); const analysisId = Number(id); const { token, user } = useAuth(); const location = useLocation(); const adminReturn = (location.state as { adminReturn?: string } | null)?.adminReturn ?? "/admin"; const isAdmin = user?.role === "admin"; const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null); const [error, setError] = useState(""); const [surveyId, setSurveyId] = useState<number | null>(null); const [research, setResearch] = useState<SurveyResearch | null>(null); const [researchError, setResearchError] = useState(""); const [researchLoading, setResearchLoading] = useState(false);
  useEffect(() => { if (!token || !analysisId) return; api.analysis(analysisId, token).then(setAnalysis).catch((err) => setError(loadError(err))); }, [token, analysisId]);
  useEffect(() => {
    if (!token || !analysis) return;
    if (!analysis.dataset_id) {
      setSurveyId(null); setResearch(null); setResearchError(""); setResearchLoading(false);
      return;
    }
    let active = true;
    setSurveyId(null); setResearch(null); setResearchError(""); setResearchLoading(true);
    api.dataset(analysis.dataset_id, token)
      .then((dataset) => {
        if (!active) return null;
        setSurveyId(dataset.survey_id ?? null);
        return dataset.survey_id ? api.surveyResearch(dataset.survey_id, token) : null;
      })
      .then((result) => { if (active && result) setResearch(result); })
      .catch((err) => { if (active) setResearchError(loadError(err)); })
      .finally(() => { if (active) setResearchLoading(false); });
    return () => { active = false; };
  }, [token, analysis?.dataset_id]);
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to={isAdmin ? adminReturn : "/analyses"}>Listeye don</Link></div>;
  if (!analysis) return <Loading />;
  const showGenericCharts = !analysis.dataset_id || (!researchLoading && surveyId === null);
  return <div className="page"><PageHeader title={`Analiz #${analysis.id}`} detail={analysis.filename} actions={<div className="header-actions">{isAdmin && <Link className="secondary-button" to={adminReturn}>Yonetici alanina don</Link>}{surveyId && <Link className="primary-button" to={`/surveys/${surveyId}/research`} state={isAdmin ? { adminReturn } : undefined}><BarChart3 size={16} />Tam arastirmayi ac</Link>}{analysis.dataset_id && <Link className="secondary-button" to={`/datasets/${analysis.dataset_id}`} state={isAdmin ? { adminReturn } : undefined}>Veri setine git</Link>}</div>} />
    <section className="metric-grid top-metrics"><Metric label="Satir" value={analysis.row_count} /><Metric label="Kolon" value={analysis.column_count} /><Metric label="Durum" value={analysis.status || "tamamlandi"} /><Metric label="Uyari" value={analysis.quality_issues.length} /></section>
    <section className="summary-block"><h2>Otomatik ozet</h2><p>{analysis.summary || "Bu analiz icin ozet bulunamadi."}</p></section>
    {surveyId && <section><h2>Anket arastirmasi</h2>{researchLoading ? <Loading /> : research ? <SurveyResearchContent research={research} /> : <div className="summary-block"><p>{researchError || "Bu anket icin arastirma sonucu bulunamadi."}</p><Link className="secondary-button" to={`/surveys/${surveyId}/research`}>Arastirma sayfasini ac</Link></div>}</section>}
    {analysis.quality_issues.length > 0 && <section><h2>Veri kalite uyarilari</h2><div className="issue-grid">{analysis.quality_issues.map((issue, index) => <article className="issue-card" key={index}><StatusPill value={issue.severity} /><h3>{String(issue.title ?? issue.column ?? "Kontrol")}</h3><p>{String(issue.message ?? JSON.stringify(issue))}</p></article>)}</div></section>}
    {showGenericCharts && analysis.chart_data.length > 0 && <section><h2>Grafik verileri</h2><div className="chart-grid">{analysis.chart_data.map((chart, index) => <MiniBarChart key={index} chart={chart} />)}</div></section>}
    <section><h2>Kolon metadatasi</h2><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Kolon</th><th>Tip</th><th>Anlam</th><th>Eksik</th><th>Benzersiz</th></tr></thead><tbody>{analysis.columns_info.map((column) => <tr key={column.name}><td><strong>{column.name}</strong></td><td>{column.dtype}</td><td>{column.semantic_type}</td><td>{column.missing_pct?.toFixed?.(1) ?? 0}%</td><td>{column.unique_count}</td></tr>)}</tbody></table></div></section>
  </div>;
}

function SurveyResearchContent({ research }: { research: SurveyResearch }) {
  return <>
    <section className="metric-grid top-metrics"><Metric label="Toplam yanit" value={research.response_count} /><Metric label="Puanlanabilir" value={research.scored_response_count} /><Metric label="Likert sorusu" value={research.likert_question_count} /><Metric label="Genel skor" value={research.overall_score_100 === null || research.overall_score_100 === undefined ? "-" : `${formatScore(research.overall_score_100)} / 100`} /></section>
    <section><h2>Soru bazli memnuniyet</h2>{research.question_scores.length ? <div className="data-table-wrap"><table className="data-table research-table"><thead><tr><th>Soru</th><th>100 uzerinden skor</th><th>Yanit</th><th>Eksik</th></tr></thead><tbody>{research.question_scores.map((question) => <tr key={question.question_id}><td><strong>{question.label}</strong>{question.label !== question.question_text && <small>{question.question_text}</small>}</td><td><strong>{formatScore(question.score_100)}</strong></td><td>{question.response_count}</td><td>{question.missing_count} <span className="muted">(%{formatScore(question.missing_pct)})</span></td></tr>)}</tbody></table></div> : <p className="muted">Bu ankette 100 uzerinden puanlanabilir Likert sorusu bulunamadi.</p>}</section>
    <section><h2>Sosyo-demografik bulgular</h2><div className="research-grid">{research.charts.filter((chart) => chart.id === "gender-distribution" || chart.id === "gender-satisfaction" || chart.id === "age-distribution" || chart.id === "age-satisfaction").map((chart) => <SurveyResearchChart key={chart.id} chart={chart} />)}</div></section>
    <section className="split-section"><div><h2>Cinsiyet bazli memnuniyet</h2><GroupScoreTable groups={research.gender_scores} /></div><div><h2>Yas bazli memnuniyet</h2><GroupScoreTable groups={research.age_scores} /></div></section>
    <section><h2>Mahalle bazli memnuniyet</h2><div className="research-grid">{research.charts.filter((chart) => chart.id === "neighborhood-satisfaction").map((chart) => <SurveyResearchChart key={chart.id} chart={chart} />)}</div><GroupScoreTable groups={research.neighborhood_scores} /></section>
    {research.quality_issues.length > 0 && <section><h2>Veri kalite notlari</h2><div className="issue-grid">{research.quality_issues.map((issue, index) => <article className="issue-card" key={index}><StatusPill value={issue.severity} /><p>{String(issue.message ?? JSON.stringify(issue))}</p></article>)}</div></section>}
    <section><h2>AI ozeti</h2>{research.ai_report ? <article className="report-content">{research.ai_report.split("\n").map((line, index) => line.trim() ? <p key={index}>{line}</p> : <br key={index} />)}</article> : <div className="summary-block"><p>{research.ai_report_warning || "AI ozeti henuz istenmedi. Sayisal arastirma analizi yukarida kullanima hazirdir."}</p></div>}</section>
  </>;
}

export function ReportsPage() {
  const { token } = useAuth(); const { selected: department } = useDepartment(); const [items, setItems] = useState<ReportListItem[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!token || !department) return; api.reports(department.id, token).then((result) => setItems(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); }, [token, department?.id]);
  if (!department) return <DepartmentGate title="Raporlar" detail="Once calisacaginiz mudurlugu secin." />;
  return <div className="page"><PageHeader title="Raporlar" detail="Bir veya birden fazla kayitli analizden olusturulan Gemini raporlarini goruntuleyin." actions={<Link className="primary-button" to="/analyses"><Plus size={17} />Yeni rapor</Link>} />{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz rapor yok" detail="Analizler ekranindan analiz secip rapor olusturabilirsiniz." action={<Link className="primary-button" to="/analyses">Analizlere git</Link>} /> : <section className="report-list">{items.map((item) => <Link className="report-card" key={item.id} to={`/reports/${item.id}`}><FileText size={22} /><div><div className="analysis-title"><strong>{item.title}</strong><StatusPill value={item.status} /></div><p>{item.analysis_ids.length} analiz kullanildi</p><small>{formatDate(item.created_at)}</small></div></Link>)}</section>}
  </div>;
}

export function PasswordChangePage() {
  const { token, signOut, updateUser } = useAuth(); const [currentPassword, setCurrentPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [error, setError] = useState(""); const [pending, setPending] = useState(false); const navigate = useNavigate();
  const submit = async (event: React.FormEvent) => { event.preventDefault(); if (!token) return; setPending(true); setError(""); try { updateUser(await api.changePassword(currentPassword, newPassword, token)); navigate("/admin"); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  return <div className="auth-layout"><section className="auth-intro"><div className="auth-mark">DI</div><h1>Yonetici guvenligi</h1><p>Ilk girisinizden once baslangic sifrenizi degistirin.</p></section><main className="auth-panel"><form className="auth-form" onSubmit={submit}><h2>Yeni sifre belirleyin</h2>{error && <ErrorNotice message={error} />}<label>Mevcut sifre<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label><label>Yeni sifre<input type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label><button className="primary-button full" disabled={pending}>{pending ? "Guncelleniyor" : "Sifreyi guncelle"}</button><button className="secondary-button full" type="button" onClick={signOut}>Cikis yap</button></form></main></div>;
}

type AdminTab = "datasets" | "analyses" | "reports" | "surveys";
type AdminResource = DatasetListItem | AnalysisListItem | ReportListItem | SurveyListItem;

const ADMIN_TABS: Array<{ id: AdminTab; label: string }> = [
  { id: "datasets", label: "Veri setleri" },
  { id: "analyses", label: "Analizler" },
  { id: "reports", label: "Raporlar" },
  { id: "surveys", label: "Anketler" },
];

export function AdminPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const analystId = Number(searchParams.get("analyst")) || null;
  const departmentId = Number(searchParams.get("department")) || null;
  const requestedTab = searchParams.get("tab");
  const tab: AdminTab = ADMIN_TABS.some((item) => item.id === requestedTab) ? requestedTab as AdminTab : "datasets";
  const [analysts, setAnalysts] = useState<AdminAnalyst[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [items, setItems] = useState<AdminResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const selectedAnalyst = analysts.find((item) => item.id === analystId) ?? null;
  const department = departments.find((item) => item.id === departmentId) ?? null;

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.adminAnalysts(token).then((result) => setAnalysts(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!token || !analystId) { setDepartments([]); setItems([]); return; }
    setLoading(true);
    api.adminDepartments(analystId, token).then((result) => setDepartments(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false));
  }, [token, analystId]);

  useEffect(() => {
    if (!token || !analystId || !departmentId) { setItems([]); return; }
    setLoading(true);
    const loader = tab === "datasets" ? api.adminDatasets(analystId, departmentId, token)
      : tab === "analyses" ? api.adminAnalyses(analystId, departmentId, token)
        : tab === "reports" ? api.adminReports(analystId, departmentId, token)
          : api.adminSurveys(analystId, departmentId, token);
    loader.then((result) => setItems(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false));
  }, [token, analystId, departmentId, tab]);

  const chooseAnalyst = (analyst: AdminAnalyst) => setSearchParams({ analyst: String(analyst.id) });
  const chooseDepartment = (item: Department) => setSearchParams({ analyst: String(analystId), department: String(item.id), tab });
  const chooseTab = (nextTab: AdminTab) => setSearchParams({ analyst: String(analystId), department: String(departmentId), tab: nextTab });
  const adminReturn = `/admin?${searchParams.toString()}`;
  const resourcePath = (item: AdminResource) => tab === "datasets" ? `/datasets/${item.id}` : tab === "analyses" ? `/analyses/${item.id}` : tab === "reports" ? `/reports/${item.id}` : `/surveys/${item.id}/research`;
  const resourceName = (item: AdminResource) => "original_filename" in item ? item.original_filename : "filename" in item ? item.filename : item.title;

  return <div className="page">
    <PageHeader title="Yonetici alani" detail="Veri analistlerinin mudurluk bazli calismalarini salt okunur olarak inceleyin." />
    {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {!analystId ? loading ? <Loading /> : <section className="analysis-list">{analysts.map((analyst) => <button className="analysis-card admin-card" key={analyst.id} onClick={() => chooseAnalyst(analyst)}><div><strong>{analyst.full_name || "Adi tanimlanmamis"}</strong><p>{analyst.email}</p></div></button>)}</section>
      : !selectedAnalyst ? <Loading /> : <>
        <button className="secondary-button" onClick={() => setSearchParams({})}>Analist listesine don</button>
        <section><h2>{selectedAnalyst.full_name || selectedAnalyst.email}</h2><div className="department-cards">{departments.map((item) => <button className={department?.id === item.id ? "department-card selected" : "department-card"} key={item.id} onClick={() => chooseDepartment(item)}>{item.name}</button>)}</div></section>
        {department && <section><div className="tab-row">{ADMIN_TABS.map((item) => <button className={tab === item.id ? "secondary-button active-tab" : "secondary-button"} key={item.id} onClick={() => chooseTab(item.id)}>{item.label}</button>)}</div>
          {loading ? <Loading /> : items.length === 0 ? <p className="muted">Bu mudurlukte kayit bulunamadi.</p> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Kayit</th><th>Durum</th><th></th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{resourceName(item)}</strong></td><td>{"status" in item ? item.status : tab === "surveys" ? "Anket" : "Kayitli"}</td><td><Link className="table-link" to={resourcePath(item)} state={{ adminReturn }}>Goruntule</Link></td></tr>)}</tbody></table></div>}
        </section>}
      </>}
  </div>;
}

export function ReportDetailPage() {
  const { id } = useParams(); const reportId = Number(id); const { token, user } = useAuth(); const location = useLocation(); const adminReturn = (location.state as { adminReturn?: string } | null)?.adminReturn ?? "/admin"; const isAdmin = user?.role === "admin"; const [report, setReport] = useState<ReportDetail | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (!token || !reportId) return; api.report(reportId, token).then(setReport).catch((err) => setError(loadError(err))); }, [token, reportId]);
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to={isAdmin ? adminReturn : "/reports"}>Listeye don</Link></div>;
  if (!report) return <Loading />;
  return <div className="page"><PageHeader title={report.title} detail={`${report.analysis_ids.length} analizden olusturuldu | ${formatDate(report.created_at)}`} actions={<div className="header-actions"><StatusPill value={report.status} />{isAdmin && <Link className="secondary-button" to={adminReturn}>Yonetici alanina don</Link>}</div>} />
    {report.status === "failed" ? <ErrorNotice message={report.error_message || "Rapor olusturulamadi."} /> : <article className="report-content">{(report.content || "Rapor icerigi bulunamadi.").split("\n").map((line, index) => line.trim() ? <p key={index}>{line}</p> : <br key={index} />)}</article>}
    <section className="report-meta"><span>Analizler: {report.analysis_ids.map((analysisId) => <Link key={analysisId} to={`/analyses/${analysisId}`} state={isAdmin ? { adminReturn } : undefined}>#{analysisId} </Link>)}</span>{report.model_name && <span>Model: {report.model_name}</span>}</section>
  </div>;
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
function DepartmentGate({ title, detail }: { title: string; detail: string }) { const { departments, select, loading } = useDepartment(); return <div className="page"><PageHeader title={title} detail={detail} />{loading ? <Loading /> : <section className="department-cards">{departments.map((department) => <button className="department-card" key={department.id} onClick={() => select(department)}>{department.name}</button>)}</section>}</div>; }
function GroupScoreTable({ groups }: { groups: SurveyGroupScore[] }) { return groups.length ? <div className="data-table-wrap"><table className="data-table compact research-table"><thead><tr><th>Grup</th><th>Skor</th><th>Katilimci</th></tr></thead><tbody>{groups.map((group) => <tr key={group.label}><td><strong>{group.label}</strong>{group.low_sample && <small>Az orneklem</small>}</td><td>{formatScore(group.score_100)}</td><td>{group.respondent_count}</td></tr>)}</tbody></table></div> : <p className="muted">Bu kirilim icin yeterli veri yok.</p>; }
function Loading() { return <div className="loading-state"><LoaderCircle className="spin" size={24} />Yukleniyor...</div>; }
