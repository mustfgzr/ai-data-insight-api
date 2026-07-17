import { BarChart3, FileSpreadsheet, FileText, LayoutDashboard, LogOut, Upload, X } from "lucide-react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import type { ChartPayload } from "./types";

export function AppShell() {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const nav = [
    { to: "/upload", label: "Yukle", icon: Upload },
    { to: "/datasets", label: "Veri setleri", icon: FileSpreadsheet },
    { to: "/analyses", label: "Analizler", icon: BarChart3 },
    { to: "/reports", label: "Raporlar", icon: FileText },
  ];

  return <div className="app-frame">
    <aside className="sidebar">
      <Link className="brand" to="/datasets"><LayoutDashboard size={23} /><span>Data Insight</span></Link>
      <nav aria-label="Ana menu">
        {nav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          <Icon size={18} /><span>{label}</span>
        </NavLink>)}
      </nav>
      <div className="sidebar-footer">
        <span className="account-email" title={user?.email}>{user?.email}</span>
        <button className="icon-button" onClick={signOut} title="Cikis yap" aria-label="Cikis yap"><LogOut size={18} /></button>
      </div>
    </aside>
    <main className="content-area" key={location.pathname}><Outlet /></main>
  </div>;
}

export function RequireAuth() {
  const { token, ready } = useAuth();
  if (!ready) return <div className="loading-screen">Oturum kontrol ediliyor...</div>;
  return token ? <AppShell /> : <Navigate to="/login" replace />;
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
