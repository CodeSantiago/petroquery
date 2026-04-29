"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getAuthToken, getCurrentUser, inviteUser } from "@/lib/api";
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
  ArrowLeft,
  UserPlus,
  Mail,
  CheckCircle2,
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

interface Project {
  id: number;
  name: string;
  description?: string;
  company_id: string;
  cuenca?: string;
  ubicacion?: string;
  created_at: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviteRole, setInviteRole] = useState("operator");
  const [inviteProjectId, setInviteProjectId] = useState<number | "">("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteSuccess, setInviteSuccess] = useState("");
  const [inviteError, setInviteError] = useState("");

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
        router.push("/projects");
        return;
      }

      const headers = { Authorization: `Bearer ${token}` };

      const [telRes, usersRes, actRes, projRes] = await Promise.all([
        fetch("http://localhost:8000/api/v1/admin/telemetry", { headers }),
        fetch("http://localhost:8000/api/v1/admin/users", { headers }),
        fetch("http://localhost:8000/api/v1/admin/activity", { headers }),
        fetch("http://localhost:8000/api/v1/projects", { headers }),
      ]);

      if (telRes.ok) setTelemetry(await telRes.json());
      if (usersRes.ok) setUsers(await usersRes.json());
      if (actRes.ok) setActivity(await actRes.json());
      if (projRes.ok) setProjects(await projRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteLoading(true);
    setInviteSuccess("");
    setInviteError("");

    try {
      await inviteUser({
        email: inviteEmail,
        username: inviteUsername,
        role: inviteRole,
        project_id: Number(inviteProjectId),
      });
      setInviteSuccess("Invitación enviada exitosamente");
      setInviteEmail("");
      setInviteUsername("");
      setInviteRole("operator");
      setInviteProjectId("");
      fetchData();
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : "Error al enviar invitación");
    } finally {
      setInviteLoading(false);
    }
  };

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
      <div className="min-h-screen bg-[#fafafa] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fafafa] text-[#1e1e23] font-sans">
      <div className="fixed inset-0 mesh-gradient opacity-30 pointer-events-none" />

      <nav className="relative z-10 flex items-center justify-between px-6 py-4 glass rounded-none mx-4 mt-4 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#23232d] flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-xl">Admin Dashboard</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/chat")}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Volver al Chat"
          >
            <ArrowLeft className="w-5 h-5 text-[#5e5e68]" />
          </button>
          <span className="text-sm text-[#8e8e98]">{currentUser?.username}</span>
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <LogOut className="w-5 h-5 text-[#5e5e68]" />
          </button>
        </div>
      </nav>

      <main className="relative z-10 p-6 max-w-7xl mx-auto space-y-6">
        {/* Invite User Section */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="w-5 h-5 text-petro-blue" />
            <h2 className="text-lg font-semibold">Invitar Usuario</h2>
          </div>

          <form onSubmit={handleInvite} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="usuario@empresa.com"
                  className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-petro-blue transition-all text-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Usuario</label>
              <input
                type="text"
                value={inviteUsername}
                onChange={(e) => setInviteUsername(e.target.value)}
                placeholder="nombre_usuario"
                className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-petro-blue transition-all text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Rol</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 focus:outline-none focus:border-petro-blue transition-all text-sm"
                required
              >
                <option value="operator">Operator</option>
                <option value="engineer">Engineer</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Proyecto</label>
              <select
                value={inviteProjectId}
                onChange={(e) => setInviteProjectId(Number(e.target.value))}
                className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 focus:outline-none focus:border-petro-blue transition-all text-sm"
                required
              >
                <option value="">Seleccionar proyecto</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={inviteLoading}
              className="w-full py-2.5 bg-petro-blue hover:bg-petro-dark disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-white font-medium transition-all duration-200 flex items-center justify-center gap-2 text-sm"
            >
              {inviteLoading ? <LoaderIcon /> : <UserPlus className="w-4 h-4" />}
              Enviar Invitación
            </button>
          </form>

          {inviteSuccess && (
            <div className="mt-4 p-3 rounded-xl bg-green-50 text-green-700 text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              {inviteSuccess}
            </div>
          )}
          {inviteError && (
            <div className="mt-4 p-3 rounded-xl bg-red-50 text-red-600 text-sm">
              {inviteError}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            icon={Users}
            label="Total Usuarios"
            value={telemetry?.total_users || 0}
            color="bg-gray-100"
          />
          <KPICard
            icon={FileText}
            label="Documentos"
            value={telemetry?.total_documents || 0}
            color="bg-gray-100"
          />
          <KPICard
            icon={Database}
            label="Chunks"
            value={telemetry?.total_chunks || 0}
            color="bg-gray-100"
          />
          <KPICard
            icon={Zap}
            label="Tokens Est."
            value={telemetry?.estimated_tokens || 0}
            color="bg-gray-100"
          />
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Actividad (Últimos 7 días)</h2>
          <div className="h-64">
            <ActivityChart data={activity} />
          </div>
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Usuarios</h2>
            <button
              onClick={fetchData}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-[#5e5e68]" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-[#8e8e98] border-b border-gray-100">
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
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="py-3 font-medium">{user.username}</td>
                    <td className="py-3 text-[#8e8e98]">{user.email}</td>
                    <td className="py-3 text-[#8e8e98] text-sm">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3">{user.document_count}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-1 rounded-lg text-xs ${
                          user.is_active
                            ? "bg-gray-100 text-[#5e5e68]"
                            : "bg-gray-50 text-[#8e8e98]"
                        }`}
                      >
                        {user.is_active ? "Activo" : "Suspendido"}
                      </span>
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => handleSuspend(user.id)}
                        className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                        title={user.is_active ? "Suspender" : "Activar"}
                      >
                        <UserX className="w-4 h-4 text-[#8e8e68]" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-[#5e5e68]" />
            <h2 className="text-lg font-semibold">Logs de Error</h2>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            <div className="p-3 rounded-xl bg-gray-50 text-sm text-[#5e5e68]">
              <span className="text-[#8e8e98] font-mono">[2024-01-01 00:00:00]</span> System operational
            </div>
            <div className="p-3 rounded-xl bg-gray-50 text-sm text-[#5e5e68]">
              <span className="text-[#8e8e98] font-mono">[2024-01-01 00:00:00]</span> Database connection active
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
    <div className="bg-white border border-gray-100 rounded-2xl p-6">
      <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center mb-4`}>
        <Icon className="w-6 h-6 text-[#5e5e68]" />
      </div>
      <p className="text-3xl font-semibold text-[#1e1e23]">{value.toLocaleString()}</p>
      <p className="text-sm text-[#8e8e98] mt-1">{label}</p>
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
            className="w-full bg-[#23232d] rounded-t-md"
            style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count > 0 ? '4px' : '0' }}
          />
          <span className="text-xs text-[#8e8e98]">
            {new Date(d.date).toLocaleDateString("es", { weekday: "short" })}
          </span>
        </div>
      ))}
      {data.length === 0 && (
        <div className="flex-1 text-center text-[#8e8e98] py-8">
          Sin datos disponibles
        </div>
      )}
    </div>
  );
}

function LoaderIcon() {
  return (
    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}
