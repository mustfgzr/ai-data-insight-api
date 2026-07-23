import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Department } from "./types";

type DepartmentContextValue = { departments: Department[]; selected: Department | null; loading: boolean; select: (department: Department | null) => void; refresh: () => Promise<void> };
const DepartmentContext = createContext<DepartmentContextValue | null>(null);

export function DepartmentProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const key = user ? `data-insight-department-${user.id}` : "data-insight-department";
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(() => Number(sessionStorage.getItem(key)) || null);
  const [loading, setLoading] = useState(false);
  const refresh = async () => {
    if (!token || user?.role !== "analyst") { setDepartments([]); return; }
    setLoading(true);
    try { setDepartments((await api.departments(token)).items); } finally { setLoading(false); }
  };
  useEffect(() => { setSelectedId(Number(sessionStorage.getItem(key)) || null); refresh().catch(() => setDepartments([])); }, [token, user?.id, user?.role]);
  const selected = departments.find((item) => item.id === selectedId) ?? null;
  const select = (department: Department | null) => { setSelectedId(department?.id ?? null); if (department) sessionStorage.setItem(key, String(department.id)); else sessionStorage.removeItem(key); };
  const value = useMemo(() => ({ departments, selected, loading, select, refresh }), [departments, selected, loading]);
  return <DepartmentContext.Provider value={value}>{children}</DepartmentContext.Provider>;
}

export function useDepartment() {
  const context = useContext(DepartmentContext);
  if (!context) throw new Error("useDepartment must be used inside DepartmentProvider");
  return context;
}
