"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  getAuthToken,
  getCurrentUser,
  logout as apiLogout,
  type User,
} from "@/lib/api";
import {
  Droplets,
  Plus,
  LogOut,
  ChevronRight,
  MapPin,
  Building2,
  FolderOpen,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: number;
  name: string;
  description?: string;
  company_id: string;
  cuenca?: string;
  ubicacion?: string;
  created_at: string;
}

interface Company {
  id: string;
  name: string;
  created_at: string;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
    cuenca: "Vaca Muerta",
    ubicacion: "",
  });

  const token = getAuthToken();

  const checkAuth = useCallback(async () => {
    if (!token) {
      router.push("/auth");
      return;
    }
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch (e) {
      apiLogout();
      router.push("/auth");
    }
  }, [router, token]);

  const loadProjects = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/projects", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (e) {
      console.error("Failed to load projects:", e);
    }
  }, [token]);

  const loadCompanies = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/projects/companies", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCompanies(data);
      }
    } catch (e) {
      console.error("Failed to load companies:", e);
    }
  }, [token]);

  useEffect(() => {
    checkAuth().then(() => {
      loadProjects();
      loadCompanies();
      setIsLoading(false);
    });
  }, [checkAuth, loadProjects, loadCompanies]);

  const handleCreateProject = async () => {
    if (!newProject.name.trim()) return;
    try {
      const res = await fetch("http://localhost:8000/api/v1/projects", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newProject),
      });
      if (res.ok) {
        setShowCreateModal(false);
        setNewProject({ name: "", description: "", cuenca: "Vaca Muerta", ubicacion: "" });
        loadProjects();
      }
    } catch (e) {
      console.error("Failed to create project:", e);
    }
  };

  const selectProject = (projectId: number) => {
    localStorage.setItem("petroquery_project_id", String(projectId));
    router.push("/chat");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-petro-gray flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-petro-blue" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-petro-gray">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-petro-blue flex items-center justify-center">
              <Droplets className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">PetroQuery</h1>
              <p className="text-xs text-gray-500">Selecciona un proyecto para continuar</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {currentUser && (
              <span className="text-sm text-gray-600">{currentUser.username}</span>
            )}
            <button
              onClick={() => { apiLogout(); router.push("/auth"); }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-600 hover:text-red-600 hover:bg-red-50 transition-colors text-sm"
            >
              <LogOut className="w-4 h-4" />
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Actions */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Mis Proyectos</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-petro-blue text-white rounded-lg hover:bg-petro-dark transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Nuevo Proyecto
          </button>
        </div>

        {/* Projects Grid */}
        {projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Sin proyectos aún</h3>
            <p className="text-gray-500 mb-6">Crea tu primer proyecto para empezar a cargar documentos técnicos.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-petro-blue text-white rounded-lg hover:bg-petro-dark transition-colors text-sm font-medium"
            >
              Crear Proyecto
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => selectProject(project.id)}
                className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-petro-blue hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-petro-light flex items-center justify-center">
                    <FolderOpen className="w-5 h-5 text-petro-blue" />
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-petro-blue transition-colors" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">{project.name}</h3>
                {project.description && (
                  <p className="text-sm text-gray-500 mb-3 line-clamp-2">{project.description}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  {project.cuenca && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-petro-light text-petro-blue">
                      <MapPin className="w-3 h-3" />
                      {project.cuenca}
                    </span>
                  )}
                  {project.company_id && companies.find(c => c.id === project.company_id)?.name && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
                      <Building2 className="w-3 h-3" />
                      {companies.find(c => c.id === project.company_id)?.name}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="px-5 py-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">Nuevo Proyecto</h3>
            </div>
            <div className="px-5 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre del Proyecto</label>
                <input
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="Ej: Yacimiento Loma Campana"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-petro-blue text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="Descripción del proyecto..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-petro-blue text-sm resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cuenca</label>
                <select
                  value={newProject.cuenca}
                  onChange={(e) => setNewProject({ ...newProject, cuenca: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-petro-blue text-sm"
                >
                  <option value="Vaca Muerta">Vaca Muerta</option>
                  <option value="Neuquina">Neuquina</option>
                  <option value="Golfo San Jorge">Golfo San Jorge</option>
                  <option value="Cuyana">Cuyana</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
                <input
                  value={newProject.ubicacion}
                  onChange={(e) => setNewProject({ ...newProject, ubicacion: e.target.value })}
                  placeholder="Ej: Neuquén, Argentina"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-petro-blue text-sm"
                />
              </div>
            </div>
            <div className="px-5 py-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateProject}
                className="px-4 py-2 bg-petro-blue text-white rounded-lg hover:bg-petro-dark text-sm font-medium"
              >
                Crear Proyecto
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
