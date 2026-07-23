import { BarChart3, FileSpreadsheet, FileText, LayoutDashboard, LogOut, Upload, Users, X } from "lucide-react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { useDepartment } from "./department";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPayload, SurveyResearchChart } from "./types";

const CHART_COLORS = ["#168a7a", "#447fba", "#e0a13d", "#c9665c", "#8a6cb5", "#5d9d69", "#b56d91"];

export function AppShell() {
  const { user, signOut } = useAuth();
  const { selected, departments, select } = useDepartment();
  const location = useLocation();
  const analystNav = [
    { to: "/upload", label: "Yukle", icon: Upload },
    { to: "/datasets", label: "Veri setleri", icon: FileSpreadsheet },
    { to: "/analyses", label: "Analizler", icon: BarChart3 },
    { to: "/reports", label: "Raporlar", icon: FileText },
  ];
  const nav = user?.role === "admin" ? [{ to: "/admin", label: "Veri analistleri", icon: Users }] : analystNav;

  return <div className="app-frame">
    <aside className="sidebar">
      <Link className="brand" to={user?.role === "admin" ? "/admin" : "/datasets"}><LayoutDashboard size={23} /><span>Data Insight</span></Link>
      <nav aria-label="Ana menu">
        {nav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          <Icon size={18} /><span>{label}</span>
        </NavLink>)}
      </nav>
      {user?.role === "analyst" && <label className="department-switcher">Mudurluk<select value={selected?.id ?? ""} onChange={(event) => select(departments.find((item) => item.id === Number(event.target.value)) ?? null)}><option value="">Secin</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}
      <div className="sidebar-footer">
        <span className="account-email" title={user?.email}>{user?.email}</span>
        <button className="icon-button" onClick={signOut} title="Cikis yap" aria-label="Cikis yap"><LogOut size={18} /></button>
      </div>
    </aside>
    <main className="content-area" key={location.pathname}><Outlet /></main>
  </div>;
}

export function RequireAuth() {
  const { token, ready, user } = useAuth();
  if (!ready) return <div className="loading-screen">Oturum kontrol ediliyor...</div>;
  if (!token) return <Navigate to="/login" replace />;
  if (user?.role === "admin" && user.must_change_password) return <Navigate to="/change-password" replace />;
  return <AppShell />;
}

export function RequireAnalyst() {
  const { user } = useAuth();
  return user?.role === "analyst" ? <Outlet /> : <Navigate to="/admin" replace />;
}

export function RequireAdmin() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Outlet /> : <Navigate to="/datasets" replace />;
}

export function PageHeader({ title, detail, actions }: { title: string; detail: string; actions?: React.ReactNode }) {
  return <header className="page-header"><div><h1>{title}</h1><p>{detail}</p></div>{actions && <div className="header-actions">{actions}</div>}</header>;
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: React.ReactNode }) {
  return <div className="empty-state"><FileSpreadsheet size={30} strokeWidth={1.5} /><h2>{title}</h2><p>{detail}</p>{action}</div>;
}

export function ErrorNotice({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return <div className="notice error"><span>{message}</span>{onDismiss && <button className="icon-button small" onClick={onDismiss} title="Mesaji kapat" aria-label="Mesaji kapat"><X size={16} /></button>}</div>;
}

export function StatusPill({ value }: { value?: string | null }) {
  const status = value ?? "bilinmiyor";
  return <span className={`status-pill ${status}`}>{status}</span>;
}

export function MiniBarChart({ chart }: { chart: ChartPayload }) {
  const pairs = chart.data?.map((item) => ({ label: item.label ?? "-", value: Number(item.value ?? 0) }))
    ?? (chart.labels ?? []).map((label, index) => ({ label, value: Number(chart.values?.[index] ?? 0) }));
  const visible = pairs.slice(0, 8);
  const max = Math.max(...visible.map((item) => item.value), 1);
  if (visible.length === 0) return null;
  return <section className="chart-panel"><h3>{chart.title ?? "Dagilim"}</h3><div className="mini-chart">
    {visible.map((item) => <div className="chart-row" key={item.label}>
      <span title={item.label}>{item.label}</span><div className="chart-track"><i style={{ width: `${Math.max((item.value / max) * 100, 2)}%` }} /></div><b>{item.value}</b>
    </div>)}
  </div></section>;
}

export function SurveyResearchChart({ chart }: { chart: SurveyResearchChart }) {
  const data = chart.data.filter((item) => typeof item.value === "number");
  if (data.length === 0) return null;
  const valueLabel = chart.unit === "score_100" ? "Skor" : "Katilimci";
  return <section className="research-chart"><h3>{chart.title}</h3><p>{chart.unit === "score_100" ? "100 uzerinden memnuniyet skoru" : "Katilimci dagilimi"}</p><div className="research-chart-canvas">
    <ResponsiveContainer width="100%" height={250}>
      {chart.type === "donut" ? <PieChart><Pie data={data} dataKey="value" nameKey="label" innerRadius={52} outerRadius={82} paddingAngle={2}>{data.map((item, index) => <Cell key={item.label} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
        : <BarChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 18 }}><XAxis dataKey="label" interval={0} angle={data.length > 5 ? -22 : 0} textAnchor={data.length > 5 ? "end" : "middle"} height={data.length > 5 ? 55 : 30} tick={{ fontSize: 11 }} /><YAxis domain={chart.unit === "score_100" ? [0, 100] : [0, "auto"]} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="value" name={valueLabel} fill="#168a7a" radius={[3, 3, 0, 0]} /></BarChart>}
    </ResponsiveContainer>
  </div></section>;
}
