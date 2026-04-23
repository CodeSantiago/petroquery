"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getAuthToken, getCurrentUser } from "@/lib/api";
import {
  Users,
  FileText,
  Database,
  Zap,
  RefreshCw,
  UserX,
  AlertCircle,
  LogOut,
  ChevronRight,
} from "lucide-react";

interface Telemetry {
  total_users: number;
  total_documents: number;
  total_chunks: number;
  estimated_tokens: number;
}

interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  document_count: number;
}

interface Activity {
  date: string;
  count: number;
}

export default function AdminPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);

  const fetchData = useCallback(async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      router.push("/auth");
      return;
    }

    try {
      const user = await getCurrentUser();
      setCurrentUser(user);

      if (user.role !== "admin") {
        router.push("/chat");
        return;
      }

      const headers = { Authorization: `Bearer ${token}` };

      const [telRes, usersRes, actRes] = await Promise.all([
        fetch("http://localhost:8000/api/v1/admin/telemetry", { headers }),
        fetch("http://localhost:8000/api/v1/admin/users", { headers }),
        fetch("http://localhost:8000/api/v1/admin/activity", { headers }),
      ]);

      if (telRes.ok) setTelemetry(await telRes.json());
      if (usersRes.ok) setUsers(await usersRes.json());
      if (actRes.ok) setActivity(await actRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSuspend = async (userId: number) => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    const res = await fetch(
      `http://localhost:8000/api/v1/admin/users/${userId}/suspend`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (res.ok) {
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, is_active: !u.is_active } : u
        )
      );
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    router.push("/auth");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-orange-300/30 border-t-orange-400 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 text-slate-700 font-sans">
      <div className="fixed inset-0 mesh-gradient opacity-30 pointer-events-none" />

      <nav className="relative z-10 flex items-center justify-between px-6 py-4 glass rounded-2xl mx-4 mt-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl">Admin Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">{currentUser?.username}</span>
          <button
            onClick={handleLogout}
            className="p-2 rounded-full hover:bg-orange-100 transition-colors"
          >
            <LogOut className="w-5 h-5 text-slate-500" />
          </button>
        </div>
      </nav>

      <main className="relative z-10 p-6 max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            icon={Users}
            label="Total Usuarios"
            value={telemetry?.total_users || 0}
            color="from-orange-400 to-amber-400"
          />
          <KPICard
            icon={FileText}
            label="Documentos"
            value={telemetry?.total_documents || 0}
            color="from-amber-400 to-yellow-400"
          />
          <KPICard
            icon={Database}
            label="Chunks"
            value={telemetry?.total_chunks || 0}
            color="from-orange-300 to-amber-300"
          />
          <KPICard
            icon={Zap}
            label="Tokens Est."
            value={telemetry?.estimated_tokens || 0}
            color="from-yellow-400 to-orange-300"
          />
        </div>

        <div className="glass-card rounded-3xl p-6">
          <h2 className="text-lg font-bold mb-4">Actividad (Últimos 7 días)</h2>
          <div className="h-64">
            <ActivityChart data={activity} />
          </div>
        </div>

        <div className="glass-card rounded-3xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold">Usuarios</h2>
            <button
              onClick={fetchData}
              className="p-2 rounded-full hover:bg-orange-100 transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-slate-500" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-slate-500 border-b border-orange-100">
                  <th className="pb-3">Usuario</th>
                  <th className="pb-3">Email</th>
                  <th className="pb-3">Registrado</th>
                  <th className="pb-3">Docs</th>
                  <th className="pb-3">Estado</th>
                  <th className="pb-3">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-orange-50 last:border-0"
                  >
                    <td className="py-3 font-medium">{user.username}</td>
                    <td className="py-3 text-slate-500">{user.email}</td>
                    <td className="py-3 text-slate-500 text-sm">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3">{user.document_count}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.is_active
                            ? "bg-amber-100 text-amber-600"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {user.is_active ? "Activo" : "Suspendido"}
                      </span>
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => handleSuspend(user.id)}
                        className="p-2 rounded-full hover:bg-orange-100 transition-colors"
                        title={user.is_active ? "Suspender" : "Activar"}
                      >
                        <UserX className="w-4 h-4 text-slate-500" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-card rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-bold">Logs de Error</h2>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            <div className="p-3 rounded-xl bg-orange-50 text-sm">
              <span className="text-orange-500 font-mono">[2024-01-01 00:00:00]</span> System operational
            </div>
            <div className="p-3 rounded-xl bg-orange-50 text-sm">
              <span className="text-orange-500 font-mono">[2024-01-01 00:00:00]</span> Database connection active
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function KPICard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: any;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="glass-card rounded-3xl p-6">
      <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center mb-4`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <p className="text-3xl font-bold text-slate-700">{value.toLocaleString()}</p>
      <p className="text-sm text-slate-500 mt-1">{label}</p>
    </div>
  );
}

function ActivityChart({ data }: { data: Activity[] }) {
  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="flex items-end gap-2 h-full">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-2">
          <div
            className="w-full bg-gradient-to-t from-orange-400 to-amber-300 rounded-t-lg"
            style={{ height: `${(d.count / max) * 100}%` }}
          />
          <span className="text-xs text-slate-400">
            {new Date(d.date).toLocaleDateString("es", { weekday: "short" })}
          </span>
        </div>
      ))}
      {data.length === 0 && (
        <div className="flex-1 text-center text-slate-400 py-8">
          Sin datos disponibles
        </div>
      )}
    </div>
  );
}