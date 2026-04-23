"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getAuthToken, getCurrentUser } from "@/lib/api";
import { 
  Brain, 
  Search, 
  Shield, 
  FileText, 
  GraduationCap, 
  Briefcase, 
  BookOpen,
  Zap,
  ArrowRight,
  Sparkles,
  ChevronRight,
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "Análisis Inteligente",
    description: "Tu IA que comprende el contexto de tus documentos para respuestas precisas.",
    color: "from-orange-300 to-amber-300",
  },
  {
    icon: Shield,
    title: "Privacidad Total",
    description: "Tus datos están aislados. Solo tú tienes acceso a tu información.",
    color: "from-amber-300 to-yellow-300",
  },
  {
    icon: FileText,
    title: "Multiformato",
    description: "Procesa PDFs, apuntes, manuales y más en segundos.",
    color: "from-blue-300 to-cyan-300",
  },
];

const useCases = [
  {
    icon: GraduationCap,
    title: "Estudiantes",
    description: "Resume materias y prepárate para exámenes con un tutor 24/7.",
    color: "from-orange-300",
  },
  {
    icon: Briefcase,
    title: "Investigadores",
    description: "Cruza información entre fuentes sin perder el contexto.",
    color: "from-amber-300",
  },
  {
    icon: BookOpen,
    title: "Curiosos",
    description: "Explora temas nuevos preguntándole directamente a tus libros.",
    color: "from-pink-300",
  },
];

function CustomCursorX() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState(false);

  useEffect(() => {
    const cursor = cursorRef.current;
    if (!cursor) return;

    const onMouseMove = (e: MouseEvent) => {
      cursor.style.transform = `translate3d(${e.clientX - 10}px, ${e.clientY - 10}px, 0)`;
    };

const onMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const isHover = target.tagName === 'A' || target.tagName === 'BUTTON' || !!target.closest('a') || !!target.closest('button');
      setHover(isHover);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseover', onMouseOver);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseover', onMouseOver);
    };
  }, []);

  return (
    <div 
      ref={cursorRef}
      className={`cursor fixed pointer-events-none z-[9999] rounded-full will-change-transform ${hover ? 'scale-150' : ''}`}
      style={{ 
        width: 20,
        height: 20,
        border: '2px solid hsl(25 80% 65%)',
        background: hover ? 'hsla(35,80%,75%,0.5)' : 'hsla(25,80%,65%,0.3)',
        transform: 'translate3d(-10px, -10px, 0)',
      }}
    />
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = getAuthToken();
      if (token) {
        try {
          await getCurrentUser();
          router.push("/chat");
        } catch (e) {
          // Token inválido
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, [router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-orange-300/30 border-t-orange-400 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 text-slate-700 font-sans overflow-x-hidden">
      
      <div className="fixed inset-0 mesh-gradient opacity-60 pointer-events-none" />
      
      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-4 glass rounded-2xl mx-4 mt-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center shadow-lg">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl text-slate-700">Brain-API</span>
        </div>
        <div className="flex items-center gap-3">
          <Link 
            href="/auth?mode=login"
            className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:text-orange-600 transition-colors rounded-full hover:bg-orange-50"
          >
            Iniciar Sesión
          </Link>
          <Link 
            href="/auth?mode=register"
            className="px-6 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-orange-400 to-pink-400 rounded-full hover:shadow-lg hover:scale-105 transition-all duration-300"
          >
            Empezar Gratis
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 px-6 py-24 md:py-32 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-100 text-orange-600 text-sm font-medium mb-8 shadow-sm">
            <Zap className="w-4 h-4" />
            <span>Potenciado por IA de última generación</span>
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold text-slate-700 mb-6 leading-tight">
            Tu segundo cerebro,{" "}
            <span className="bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 bg-clip-text text-transparent">
              potenciado por IA
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-500 mb-10 max-w-2xl mx-auto">
            No pierdas tiempo buscando en cientos de páginas. 
            Sube tus documentos y obtén respuestas precisas al instante.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link 
              href="/auth?mode=register"
              className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 text-white font-semibold rounded-full hover:shadow-xl hover:scale-105 transition-all duration-300 flex items-center justify-center gap-2"
            >
              Empezar Ahora — Gratis
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link 
              href="/auth?mode=login"
              className="w-full sm:w-auto px-8 py-3.5 bg-white/60 bg-white/60 text-slate-600 font-medium rounded-full hover:bg-white transition-all duration-300 border border-orange-100 shadow-sm hover:shadow-md"
            >
              Ya tengo cuenta
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 px-6 py-20">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-700 text-center mb-16">
            ¿Por qué Brain-API?
          </h2>
          
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="group p-6 rounded-3xl bg-white/60 bg-white/60 border border-white/50 hover:border-orange-200 hover:shadow-xl hover:scale-105 transition-all duration-300"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-lg font-bold text-slate-700 mb-2">{feature.title}</h3>
                <p className="text-slate-500 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="relative z-10 px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-700 mb-4">
            ¿Cómo funciona?
          </h2>
          <p className="text-slate-500 mb-12">
            Tres pasos simples para desbloquear el poder de tus documentos
          </p>
          
          <div className="flex flex-col md:flex-row items-center justify-center gap-6">
            <div className="flex flex-col items-center p-6 rounded-3xl bg-white/60 bg-white/60 border border-orange-100 shadow-md">
              <div className="w-16 h-16 rounded-2xl bg-orange-200 flex items-center justify-center mb-3">
                <span className="text-2xl font-bold text-orange-600">1</span>
              </div>
              <p className="font-semibold text-slate-700">Sube tu archivo</p>
              <p className="text-slate-400 text-sm">PDF, texto o manual</p>
            </div>
            
            <ChevronRight className="w-6 h-6 text-orange-300 hidden md:block" />
            
            <div className="flex flex-col items-center p-6 rounded-3xl bg-white/60 bg-white/60 border border-amber-100 shadow-md">
              <div className="w-16 h-16 rounded-2xl bg-amber-200 flex items-center justify-center mb-3">
                <span className="text-2xl font-bold text-amber-600">2</span>
              </div>
              <p className="font-semibold text-slate-700">Procesamiento IA</p>
              <p className="text-slate-400 text-sm">Vectores y embeddings</p>
            </div>
            
            <ChevronRight className="w-6 h-6 text-amber-300 hidden md:block" />
            
            <div className="flex flex-col items-center p-6 rounded-3xl bg-white/60 bg-white/60 border border-pink-100 shadow-md">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-200 to-pink-200 flex items-center justify-center mb-3">
                <Search className="w-7 h-7 text-orange-600" />
              </div>
              <p className="font-semibold text-slate-700">Pregunta</p>
              <p className="text-slate-400 text-sm">Chat con contexto</p>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="relative z-10 px-6 py-20">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-700 text-center mb-4">
            Diseñado para ti
          </h2>
          <p className="text-slate-500 text-center mb-12">
            Estudiando, investigando o simplemente explorando
          </p>
          
          <div className="grid md:grid-cols-3 gap-6">
            {useCases.map((useCase, index) => (
              <div 
                key={index}
                className="p-6 rounded-3xl bg-gradient-to-br from-white/80 to-orange-50/50 border border-white/50 hover:shadow-xl hover:scale-105 transition-all duration-300"
              >
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${useCase.color} to-pink-200 flex items-center justify-center mb-4`}>
                  <useCase.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-bold text-slate-700 mb-2">{useCase.title}</h3>
                <p className="text-slate-500 text-sm">{useCase.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 px-6 py-20">
        <div className="max-w-2xl mx-auto text-center">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center mx-auto mb-6 shadow-xl">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
          
          <h2 className="text-2xl md:text-3xl font-bold text-slate-700 mb-4">
            ¿Listo para transformar tu manera de aprender?
          </h2>
          
          <p className="text-slate-500 mb-8">
            Únete a miles de usuarios que ya están usando Brain-API.
          </p>
          
          <Link 
            href="/auth?mode=register"
            className="inline-flex items-center gap-2 px-10 py-4 bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 text-white font-semibold rounded-full hover:shadow-2xl hover:scale-105 transition-all duration-300"
          >
            Crear mi cuenta gratis
            <ArrowRight className="w-5 h-5" />
          </Link>
          
          <p className="text-xs text-slate-400 mt-6">
            Sin tarjeta de crédito • Configuración en 30 segundos
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 px-6 py-8 border-t border-orange-100/50">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center">
              <Brain className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm text-slate-500">Brain-API</span>
          </div>
          <p className="text-xs text-slate-400">© 2024 Brain-API. Todos los derechos reservados.</p>
        </div>
      </footer>
    </div>
  );
}