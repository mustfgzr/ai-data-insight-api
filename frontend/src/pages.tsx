import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { Download, FilePlus2, FileText, LoaderCircle, Plus, RefreshCw, Sparkles, UploadCloud } from "lucide-react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import { EmptyState, ErrorNotice, MiniBarChart, PageHeader, StatusPill } from "./components";
import type { AnalysisDetail, AnalysisListItem, DatasetDetail, DatasetListItem, DatasetRows, DatasetUpload, ReportDetail, ReportListItem } from "./types";

const formatDate = (value?: string) => value ? new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
const formatValue = (value: unknown) => value === null || value === undefined || value === "" ? "-" : typeof value === "object" ? JSON.stringify(value) : String(value);
const loadError = (error: unknown) => error instanceof Error ? error.message : "Veriler yuklenirken bir hata olustu.";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { token, signIn, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  if (token) return <Navigate to="/datasets" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setPending(true);
    try { mode === "login" ? await signIn(email, password) : await register(email, password); navigate("/datasets"); }
    catch (err) { setError(loadError(err)); }
    finally { setPending(false); }
  };
  const isLogin = mode === "login";
  return <div className="auth-layout"><section className="auth-intro"><div className="auth-mark">DI</div><h1>Data Insight</h1><p>Anket ve veri setlerinizi yukleyin, kalite sinyallerini gorun, analizleri tek yerde yonetin.</p><div className="intro-metrics"><span>CSV</span><span>XLSX</span><span>JWT</span><span>Gemini</span></div></section>
    <main className="auth-panel"><form className="auth-form" onSubmit={submit}><div><p className="eyebrow">{isLogin ? "HOS GELDINIZ" : "YENI HESAP"}</p><h2>{isLogin ? "Hesabiniza girin" : "Calisma alaninizi olusturun"}</h2><p>{isLogin ? "Yuklemelerinize ve raporlariniza devam edin." : "Veri analizlerinizi guvenli bir alanda yonetin."}</p></div>
      {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
      <label>E-posta<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>Sifre<input type="password" autoComplete={isLogin ? "current-password" : "new-password"} minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      <button className="primary-button full" disabled={pending}>{pending && <LoaderCircle className="spin" size={17} />}{isLogin ? "Giris yap" : "Kayit ol"}</button>
      <p className="form-switch">{isLogin ? "Hesabiniz yok mu?" : "Zaten hesabiniz var mi?"} <Link to={isLogin ? "/register" : "/login"}>{isLogin ? "Kayit olun" : "Giris yapin"}</Link></p>
    </form></main></div>;
}

export function UploadPage() {
  const { token } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DatasetUpload | null>(null);
  const navigate = useNavigate();
  const select = (candidate?: File) => {
    setError(""); setResult(null);
    if (!candidate) return;
    if (!/\.(csv|xlsx)$/i.test(candidate.name)) { setFile(null); setError("Yalnizca CSV veya XLSX dosyalari yuklenebilir."); return; }
    setFile(candidate);
  };
  const dropped = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); setDragging(false); select(event.dataTransfer.files[0]); };
  const submit = async () => {
    if (!file || !token) return; setPending(true); setError("");
    try { setResult(await api.uploadDataset(file, token)); }
    catch (err) { setError(loadError(err)); }
    finally { setPending(false); }
  };
  return <div className="page"><PageHeader title="Veri seti yukle" detail="CSV veya XLSX dosyanizi yukleyin. Kolonlar, kalite sinyalleri ve temel analiz otomatik olusturulur." />
    <section className="upload-layout"><div className="upload-main"><div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropped} onClick={() => input.current?.click()} role="button" tabIndex={0}>
      <UploadCloud size={38} strokeWidth={1.4} /><h2>{file ? file.name : "Dosyanizi buraya birakin"}</h2><p>{file ? `${(file.size / 1024).toFixed(1)} KB secildi` : "veya bilgisayarinizdan secin"}</p><span className="secondary-button">Dosya sec</span><input ref={input} type="file" accept=".csv,.xlsx" onChange={(e) => select(e.target.files?.[0])} hidden />
    </div>{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    <button className="primary-button upload-submit" disabled={!file || pending} onClick={submit}>{pending && <LoaderCircle className="spin" size={17} />}{pending ? "Isleniyor..." : "Analizi baslat"}</button></div>
      <aside className="upload-notes"><h2>Yukleme kapsami</h2><dl><div><dt>Desteklenen</dt><dd>CSV ve XLSX</dd></div><div><dt>Otomatik cikarim</dt><dd>Kolon, tip, eksik deger, ornek deger</dd></div><div><dt>Anket tanima</dt><dd>Soru, secenek ve dagilimlar</dd></div><div><dt>Sinirlar</dt><dd>20 MB, 10.000 satir, 300 kolon</dd></div></dl></aside>
    </section>
    {result && <section className="result-panel"><div><p className="eyebrow">YUKLEME TAMAMLANDI</p><h2>{result.filename}</h2><p>{result.summary}</p></div><div className="metric-grid"><Metric label="Satir" value={result.row_count} /><Metric label="Kolon" value={result.column_count} /><Metric label="Uyari" value={result.quality_issues.length} /></div><div className="result-actions"><button className="secondary-button" onClick={() => navigate(`/datasets/${result.dataset_id}`)}>Veri setini gor</button><button className="primary-button" onClick={() => navigate(`/analyses/${result.analysis_id}`)}>Analizi gor</button></div></section>}
  </div>;
}

export function DatasetsPage() {
  const { token } = useAuth(); const [items, setItems] = useState<DatasetListItem[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const refresh = () => { if (!token) return; setLoading(true); api.datasets(token).then((result) => setItems(result.items)).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); };
  useEffect(refresh, [token]);
  return <div className="page"><PageHeader title="Veri setleri" detail="Yuklediginiz dosyalara, yapilarina ve kaynak dosyalarina buradan ulasin." actions={<Link className="primary-button" to="/upload"><FilePlus2 size={17} />Veri seti yukle</Link>} />
    {error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz veri seti yok" detail="Ilk CSV veya XLSX dosyanizi yukleyerek analize baslayin." action={<Link className="primary-button" to="/upload">Dosya yukle</Link>} /> : <section className="data-table-wrap"><table className="data-table"><thead><tr><th>Dosya</th><th>Tur</th><th>Yapi</th><th>Olusturulma</th><th></th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.original_filename}</strong><small>ID #{item.id}</small></td><td><span className="file-badge">{item.file_type.toUpperCase()}</span></td><td>{item.row_count} satir <span className="muted">/</span> {item.column_count} kolon</td><td>{formatDate(item.created_at)}</td><td><Link className="table-link" to={`/datasets/${item.id}`}>Ac</Link></td></tr>)}</tbody></table></section>}
  </div>;
}

export function DatasetDetailPage() {
  const { id } = useParams(); const datasetId = Number(id); const { token } = useAuth(); const [dataset, setDataset] = useState<DatasetDetail | null>(null); const [rows, setRows] = useState<DatasetRows | null>(null); const [error, setError] = useState("");
  const refresh = () => { if (!token || !datasetId) return; Promise.all([api.dataset(datasetId, token), api.datasetRows(datasetId, 0, token)]).then(([detail, page]) => { setDataset(detail); setRows(page); }).catch((err) => setError(loadError(err))); };
  useEffect(refresh, [token, datasetId]);
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to="/datasets">Listeye don</Link></div>;
  if (!dataset) return <Loading />;
  const headers = rows?.rows.length ? Object.keys(rows.rows[0]) : dataset.columns.map((column) => column.name);
  return <div className="page"><PageHeader title={dataset.original_filename} detail={`${dataset.row_count} satir, ${dataset.column_count} kolon, ${dataset.detected_format} formati`} actions={<div className="header-actions">{dataset.has_source_file && <a className="secondary-button" href={api.downloadUrl(dataset.id)} target="_blank" rel="noreferrer"><Download size={16} />Kaynak dosya</a>}{dataset.latest_analysis_id && <Link className="primary-button" to={`/analyses/${dataset.latest_analysis_id}`}>Analizi ac</Link>}</div>} />
    <section className="metric-grid top-metrics"><Metric label="Veri tipi" value={dataset.file_type.toUpperCase()} /><Metric label="Anket" value={dataset.survey_id ? "Algilandi" : "Genel veri"} /><Metric label="Satir" value={dataset.row_count} /><Metric label="Kolon" value={dataset.column_count} /></section>
    <section className="split-section"><div><h2>Kolon yapisi</h2><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Kolon</th><th>Tip</th><th>Anlam</th><th>Eksik</th><th>Benzersiz</th><th>Ornekler</th></tr></thead><tbody>{dataset.columns.map((column) => <tr key={column.name}><td><strong>{column.name}</strong></td><td>{column.dtype}</td><td>{column.semantic_type}</td><td>{column.missing_pct.toFixed(1)}%</td><td>{column.unique_count}</td><td className="sample-cell">{column.sample_values.slice(0, 3).map(formatValue).join(", ") || "-"}</td></tr>)}</tbody></table></div></div></section>
    <section><h2>Satir onizlemesi</h2>{rows?.rows.length ? <div className="data-table-wrap"><table className="data-table compact"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.rows.map((row, index) => <tr key={index}>{headers.map((header) => <td key={header}>{formatValue(row[header])}</td>)}</tr>)}</tbody></table></div> : <p className="muted">Gosterilecek satir yok.</p>}</section>
  </div>;
}

export function AnalysesPage() {
  const { token } = useAuth(); const [items, setItems] = useState<AnalysisListItem[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const [selected, setSelected] = useState<number[]>([]); const [title, setTitle] = useState(""); const [question, setQuestion] = useState(""); const [pending, setPending] = useState(false); const navigate = useNavigate();
  useEffect(() => { if (!token) return; api.analyses(token).then(setItems).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); }, [token]);
  const toggle = (analysisId: number) => setSelected((current) => current.includes(analysisId) ? current.filter((id) => id !== analysisId) : current.length < 5 ? [...current, analysisId] : current);
  const createReport = async () => { if (!token || selected.length === 0) return; setPending(true); setError(""); try { const report = await api.createReport({ analysis_ids: selected, title: title || undefined, question: question || undefined }, token); navigate(`/reports/${report.id}`); } catch (err) { setError(loadError(err)); } finally { setPending(false); } };
  return <div className="page"><PageHeader title="Analizler" detail="Kaydedilen analizleri inceleyin veya en fazla bes tanesini secerek ortak bir Gemini raporu olusturun." />{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz analiz yok" detail="Bir veri seti yuklediginizde temel analiz otomatik olusturulur." action={<Link className="primary-button" to="/upload">Veri seti yukle</Link>} /> : <><section className="report-builder"><div><p className="eyebrow">RAPOR OLUSTUR</p><h2>{selected.length} analiz secildi</h2><p>Secili analizlerin yapilandirilmis istatistikleri Gemini ile degerlendirilir.</p></div><div className="report-inputs"><input aria-label="Rapor basligi" placeholder="Rapor basligi (istege bagli)" value={title} onChange={(e) => setTitle(e.target.value)} /><input aria-label="Rapor sorusu" placeholder="Rapor sorusu veya odak noktasi" value={question} onChange={(e) => setQuestion(e.target.value)} /></div><button className="primary-button" disabled={!selected.length || pending} onClick={createReport}>{pending ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{pending ? "Olusturuluyor" : "Rapor olustur"}</button></section>
      <section className="analysis-list">{items.map((item) => <label className={`analysis-card ${selected.includes(item.id) ? "selected" : ""}`} key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} /><div><div className="analysis-title"><strong>{item.filename}</strong><StatusPill value={item.status} /></div><p>{item.summary || "Otomatik veri seti analizi"}</p><small>{item.row_count} satir, {item.column_count} kolon | {formatDate(item.created_at)}</small></div><Link className="table-link" to={`/analyses/${item.id}`} onClick={(event) => event.stopPropagation()}>Detay</Link></label>)}</section></>}
  </div>;
}

export function AnalysisDetailPage() {
  const { id } = useParams(); const analysisId = Number(id); const { token } = useAuth(); const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (!token || !analysisId) return; api.analysis(analysisId, token).then(setAnalysis).catch((err) => setError(loadError(err))); }, [token, analysisId]);
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to="/analyses">Listeye don</Link></div>;
  if (!analysis) return <Loading />;
  return <div className="page"><PageHeader title={`Analiz #${analysis.id}`} detail={analysis.filename} actions={analysis.dataset_id ? <Link className="secondary-button" to={`/datasets/${analysis.dataset_id}`}>Veri setine git</Link> : undefined} />
    <section className="metric-grid top-metrics"><Metric label="Satir" value={analysis.row_count} /><Metric label="Kolon" value={analysis.column_count} /><Metric label="Durum" value={analysis.status || "tamamlandi"} /><Metric label="Uyari" value={analysis.quality_issues.length} /></section>
    <section className="summary-block"><h2>Otomatik ozet</h2><p>{analysis.summary || "Bu analiz icin ozet bulunamadi."}</p></section>
    {analysis.quality_issues.length > 0 && <section><h2>Veri kalite uyarilari</h2><div className="issue-grid">{analysis.quality_issues.map((issue, index) => <article className="issue-card" key={index}><StatusPill value={issue.severity} /><h3>{String(issue.title ?? issue.column ?? "Kontrol")}</h3><p>{String(issue.message ?? JSON.stringify(issue))}</p></article>)}</div></section>}
    {analysis.chart_data.length > 0 && <section><h2>Grafik verileri</h2><div className="chart-grid">{analysis.chart_data.map((chart, index) => <MiniBarChart key={index} chart={chart} />)}</div></section>}
    <section><h2>Kolon metadatasi</h2><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Kolon</th><th>Tip</th><th>Anlam</th><th>Eksik</th><th>Benzersiz</th></tr></thead><tbody>{analysis.columns_info.map((column) => <tr key={column.name}><td><strong>{column.name}</strong></td><td>{column.dtype}</td><td>{column.semantic_type}</td><td>{column.missing_pct?.toFixed?.(1) ?? 0}%</td><td>{column.unique_count}</td></tr>)}</tbody></table></div></section>
  </div>;
}

export function ReportsPage() {
  const { token } = useAuth(); const [items, setItems] = useState<ReportListItem[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!token) return; api.reports(token).then(setItems).catch((err) => setError(loadError(err))).finally(() => setLoading(false)); }, [token]);
  return <div className="page"><PageHeader title="Raporlar" detail="Bir veya birden fazla kayitli analizden olusturulan Gemini raporlarini goruntuleyin." actions={<Link className="primary-button" to="/analyses"><Plus size={17} />Yeni rapor</Link>} />{error && <ErrorNotice message={error} onDismiss={() => setError("")} />}
    {loading ? <Loading /> : items.length === 0 ? <EmptyState title="Henuz rapor yok" detail="Analizler ekranindan analiz secip rapor olusturabilirsiniz." action={<Link className="primary-button" to="/analyses">Analizlere git</Link>} /> : <section className="report-list">{items.map((item) => <Link className="report-card" key={item.id} to={`/reports/${item.id}`}><FileText size={22} /><div><div className="analysis-title"><strong>{item.title}</strong><StatusPill value={item.status} /></div><p>{item.analysis_ids.length} analiz kullanildi</p><small>{formatDate(item.created_at)}</small></div></Link>)}</section>}
  </div>;
}

export function ReportDetailPage() {
  const { id } = useParams(); const reportId = Number(id); const { token } = useAuth(); const [report, setReport] = useState<ReportDetail | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (!token || !reportId) return; api.report(reportId, token).then(setReport).catch((err) => setError(loadError(err))); }, [token, reportId]);
  if (error) return <div className="page"><ErrorNotice message={error} /><Link className="secondary-button" to="/reports">Listeye don</Link></div>;
  if (!report) return <Loading />;
  return <div className="page"><PageHeader title={report.title} detail={`${report.analysis_ids.length} analizden olusturuldu | ${formatDate(report.created_at)}`} actions={<StatusPill value={report.status} />} />
    {report.status === "failed" ? <ErrorNotice message={report.error_message || "Rapor olusturulamadi."} /> : <article className="report-content">{(report.content || "Rapor icerigi bulunamadi.").split("\n").map((line, index) => line.trim() ? <p key={index}>{line}</p> : <br key={index} />)}</article>}
    <section className="report-meta"><span>Analizler: {report.analysis_ids.map((analysisId) => <Link key={analysisId} to={`/analyses/${analysisId}`}>#{analysisId} </Link>)}</span>{report.model_name && <span>Model: {report.model_name}</span>}</section>
  </div>;
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
function Loading() { return <div className="loading-state"><LoaderCircle className="spin" size={24} />Yukleniyor...</div>; }
