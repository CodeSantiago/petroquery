"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login, register } from "@/lib/api";
import { Loader2, UserPlus, LogIn, ArrowLeft } from "lucide-react";
import Link from "next/link";

function AuthContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLogin, setIsLogin] = useState(searchParams.get("mode") !== "register");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    setIsLogin(searchParams.get("mode") !== "register");
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      if (isLogin) {
        await login(username, password);
      } else {
        await register({ email, username, password, full_name: fullName || undefined });
        await login(username, password);
      }
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ocurrió un error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 flex items-center justify-center p-4">
      
      <div className="fixed inset-0 mesh-gradient opacity-40 pointer-events-none" />
      
      <div className="relative w-full max-w-md p-8 glass-card rounded-3xl">
        <Link 
          href="/"
          className="absolute top-4 left-4 p-2 rounded-full hover:bg-orange-100 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-slate-500" />
        </Link>
        
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center mx-auto mb-4 shadow-lg">
            <UserPlus className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-700">
            {isLogin ? "Bienvenido de nuevo" : "Crear cuenta"}
          </h1>
          <p className="text-slate-500 mt-2">
            {isLogin ? "Inicia sesión para continuar" : "Comienza tu viaje con Brain-API"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                className="w-full px-4 py-3 bg-white/60 bg-white/60 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
                required={!isLogin}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Usuario</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="tu_usuario"
              className="w-full px-4 py-3 bg-white/60 bg-white/60 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
              required
            />
          </div>

          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Nombre completo (opcional)</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Tu nombre"
                className="w-full px-4 py-3 bg-white/60 bg-white/60 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-white/60 bg-white/60 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
              required
              minLength={8}
            />
          </div>

          {error && (
            <div className="p-3 rounded-2xl bg-red-50 border border-red-100 text-red-500 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-2xl text-white font-semibold transition-all duration-300 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                {isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
                {isLogin ? "Iniciar Sesión" : "Crear Cuenta"}
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setIsLogin(!isLogin); setError(""); }}
            className="text-sm text-orange-600 hover:text-orange-700 font-medium transition-colors"
          >
            {isLogin ? "¿No tienes cuenta? Regístrate" : "¿Ya tienes cuenta? Inicia sesión"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 flex items-center justify-center"><div className="w-10 h-10 border-4 border-orange-300/30 border-t-orange-400 rounded-full animate-spin" /></div>}>
      <AuthContent />
    </Suspense>
  );
}