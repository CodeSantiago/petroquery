"use client";

import { useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { login, getCurrentUser } from "@/lib/api";
import { Loader2, LogIn, Lock, ArrowLeft } from "lucide-react";
import Link from "next/link";

function AuthContent() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await login(username, password);
      const user = await getCurrentUser();
      if (user.role === "operator") {
        router.push("/projects");
      } else {
        router.push("/projects");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ocurrió un error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-petro-gray flex items-center justify-center p-4">
      
      <div className="fixed inset-0 mesh-gradient opacity-40 pointer-events-none" />
      
      <div className="relative w-full max-w-md p-8 bg-white border border-gray-200 rounded-2xl shadow-sm">
        <Link 
          href="/"
          className="absolute top-4 left-4 p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-petro-blue flex items-center justify-center mx-auto mb-4">
            <LogIn className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Iniciar Sesión
          </h1>
          <p className="text-gray-500 mt-2">
            Acceso corporativo - PetroQuery
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1.5">Usuario</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="tuusuario"
              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-petro-blue transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1.5">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-petro-blue transition-all"
              required
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-50 text-red-600 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3.5 bg-petro-blue hover:bg-petro-dark disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-white font-medium transition-all duration-200 flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
            Iniciar Sesión
          </button>
        </form>

        <div className="mt-6 space-y-3">
          <button
            disabled
            className="w-full py-3.5 bg-gray-100 text-gray-400 rounded-xl font-medium flex items-center justify-center gap-2 opacity-50 cursor-not-allowed"
          >
            <Lock className="w-4 h-4" />
            Ingresar con SSO Corporativo
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-petro-gray flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-200 border-t-petro-blue rounded-full animate-spin" />
      </div>
    }>
      <AuthContent />
    </Suspense>
  );
}
