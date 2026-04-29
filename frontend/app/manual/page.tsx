"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  BookOpen,
  ChevronRight,
  HelpCircle,
  Shield,
  Search,
  FileText,
  BarChart3,
  Droplets,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

interface Section {
  id: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function ManualPage() {
  const [activeSection, setActiveSection] = useState("intro");

  const sections: Section[] = [
    {
      id: "intro",
      title: "¿Qué es PetroQuery?",
      icon: <Droplets className="w-5 h-5" />,
      content: (
        <div className="space-y-4">
          <p className="text-gray-700 leading-relaxed">
            <strong>PetroQuery</strong> es un asistente técnico de inteligencia artificial
            especializado en operaciones <strong>Oil & Gas</strong>, con foco particular en la
            <strong> Cuenca Neuquina (Vaca Muerta)</strong>, Argentina.
          </p>
          <p className="text-gray-700 leading-relaxed">
            A diferencia de un buscador web o un chatbot genérico, PetroQuery responde
            <strong> exclusivamente sobre la documentación técnica que vos cargues</strong>:
            manuales de perforación, normativas IAPG, reportes de pozo, especificaciones de equipos, etc.
          </p>
          <div className="bg-petro-blue/5 border border-petro-blue/10 rounded-lg p-4">
            <h4 className="font-semibold text-petro-blue mb-2">Características principales</h4>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-petro-orange flex-shrink-0 mt-0.5" />
                <span><strong>Trazabilidad absoluta:</strong> cada respuesta indica el documento, página y sección exacta de donde extrajo la información.</span>
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-petro-orange flex-shrink-0 mt-0.5" />
                <span><strong>Respuestas estructuradas:</strong> formato técnico estandarizado con resumen, detalle, fuentes y advertencias.</span>
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-petro-orange flex-shrink-0 mt-0.5" />
                <span><strong>Procesamiento asíncrono:</strong> podés subir manuales de cientos de páginas sin bloquear el sistema.</span>
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-petro-orange flex-shrink-0 mt-0.5" />
                <span><strong>Filtros por metadatos:</strong> buscá por cuenca, tipo de equipo, normativa aplicable o tipo de documento.</span>
              </li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      id: "uso",
      title: "Cómo usar PetroQuery",
      icon: <BookOpen className="w-5 h-5" />,
      content: (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">1. Cargar documentos</h4>
          <p className="text-gray-700 text-sm leading-relaxed">
            Desde la pantalla de chat, hacé clic en el botón <strong>📎 Subir PDF</strong> o arrastrá un archivo directamente.
            Completá los campos de metadata (cuenca, tipo de documento, normativa) para mejorar la precisión de las búsquedas.
          </p>
          <p className="text-gray-700 text-sm leading-relaxed">
            El sistema procesará el PDF en segundo plano. Cuando aparezca <strong>"Completado"</strong>, ya podés consultar sobre su contenido.
          </p>

          <h4 className="font-semibold text-gray-900 mt-4">2. Hacer una consulta</h4>
          <p className="text-gray-700 text-sm leading-relaxed">
            Escribí tu pregunta en lenguaje natural. Sé específico: mencioná equipos, números de norma, o sectores geográficos.
          </p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
            <p className="text-gray-500 text-xs uppercase tracking-wide font-semibold">Ejemplos de buenas preguntas</p>
            <p className="text-green-700">✓ "¿Cuál es el límite de ppm de H2S que activa evacuación inmediata?"</p>
            <p className="text-green-700">✓ "Especificaciones del BOP Cameron U 13 5/8\" 10M"</p>
            <p className="text-green-700">✓ "Pasos del procedimiento de killing the well según IAPG-IRAM 301"</p>
          </div>

          <h4 className="font-semibold text-gray-900 mt-4">3. Usar filtros avanzados</h4>
          <p className="text-gray-700 text-sm leading-relaxed">
            Si tenés muchos documentos cargados, usá los <strong>filtros</strong> para restringir la búsqueda:
            cuenca (Vaca Muerta, Neuquina), tipo de documento (manual, normativa, reporte), tipo de equipo (BOP, Casing, Christmas Tree), o normativa aplicable.
          </p>

          <h4 className="font-semibold text-gray-900 mt-4">4. Revisar las fuentes</h4>
          <p className="text-gray-700 text-sm leading-relaxed">
            Cada respuesta incluye <strong>tarjetas de fuente</strong> que muestran el documento original, la página exacta, y el score de confianza.
            Hacé clic en <strong>"Ver en documento"</strong> para ver el detalle completo de la fuente.
          </p>
        </div>
      ),
    },
    {
      id: "confianza",
      title: "Entendiendo el Score de Confianza",
      icon: <BarChart3 className="w-5 h-5" />,
      content: (
        <div className="space-y-4">
          <p className="text-gray-700 leading-relaxed">
            El <strong>score de confianza</strong> indica qué tan seguro está PetroQuery de que la información recuperada es relevante y precisa para tu pregunta.
          </p>

          <div className="grid grid-cols-1 gap-3">
            <div className="flex items-start gap-3 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-sm">&gt;80%</span>
              </div>
              <div>
                <h5 className="font-semibold text-green-800">Alta confianza</h5>
                <p className="text-sm text-green-700">El chunk recuperado es muy relevante y probablemente contiene la respuesta correcta. Podés usar la información con seguridad.</p>
              </div>
            </div>

            <div className="flex items-start gap-3 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="w-10 h-10 rounded-full bg-yellow-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-sm">70-80%</span>
              </div>
              <div>
                <h5 className="font-semibold text-yellow-800">Confianza media</h5>
                <p className="text-sm text-yellow-700">El chunk es relevante pero puede haber ambigüedad. Se recomienda verificar con otra fuente antes de actuar.</p>
              </div>
            </div>

            <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-sm">&lt;70%</span>
              </div>
              <div>
                <h5 className="font-semibold text-red-800">Baja confianza — Revisión humana requerida</h5>
                <p className="text-sm text-red-700">La información es tangencial o el sistema no está seguro. <strong>No tomes decisiones operativas</strong> basadas solo en esta respuesta. Consultá con un ingeniero.</p>
              </div>
            </div>
          </div>

          <div className="bg-petro-blue/5 border border-petro-blue/10 rounded-lg p-4 mt-4">
            <h5 className="font-semibold text-petro-blue mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Advertencias de seguridad
            </h5>
            <p className="text-sm text-gray-700">
              Si tu consulta involucra <strong>H2S, blowout, pressure testing o cualquier procedimiento de seguridad</strong>,
              el sistema activa automáticamente <strong>"Revisión humana requerida"</strong>,
              independientemente del score. Esto es por diseño: nunca se debe tomar una decisión de seguridad basada 100% en una IA.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: "ejemplos",
      title: "Ejemplos de Consultas",
      icon: <Search className="w-5 h-5" />,
      content: (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">Seguridad y H2S</h4>
          <div className="space-y-1 text-sm">
            <p className="text-gray-700">• "¿Cuál es el límite de ppm de H2S que activa la evacuación inmediata?"</p>
            <p className="text-gray-700">• "Protocolo de emergencia por H2S en Vaca Muerta"</p>
            <p className="text-gray-700">• "¿Qué PPE es obligatorio en zonas con riesgo de H2S?"</p>
            <p className="text-gray-700">• "Checklist pre-operación para trabajo en superficie"</p>
          </div>

          <h4 className="font-semibold text-gray-900 mt-4">Equipos y Especificaciones</h4>
          <div className="space-y-1 text-sm">
            <p className="text-gray-700">• "Especificaciones del BOP Cameron U 13 5/8\" 10M"</p>
            <p className="text-gray-700">• "¿Cuál es el rating de presión del Christmas Tree?"</p>
            <p className="text-gray-700">• "Materiales resistentes a H2S según NACE MR0175"</p>
            <p className="text-gray-700">• "Intervalos de mantenimiento preventivo del pumpjack"</p>
          </div>

          <h4 className="font-semibold text-gray-900 mt-4">Perforación y Operaciones</h4>
          <div className="space-y-1 text-sm">
            <p className="text-gray-700">• "Casing de producción 7 pulgadas Vaca Muerta"</p>
            <p className="text-gray-700">• "Presión de fractura en Fortín de Piedra"</p>
            <p className="text-gray-700">• "Pasos del procedimiento de killing the well"</p>
            <p className="text-gray-700">• "Densidad del lodo de control para Vaca Muerta"</p>
          </div>

          <h4 className="font-semibold text-gray-900 mt-4">Normativa y Regulaciones</h4>
          <div className="space-y-1 text-sm">
            <p className="text-gray-700">• "¿Qué establece la Resolución SE 123/2018?"</p>
            <p className="text-gray-700">• "Normativa IAPG-IRAM 301 para perforación"</p>
            <p className="text-gray-700">• "Requisitos de monitoreo sísmico en fracturación"</p>
            <p className="text-gray-700">• "Ley 17.319 de hidrocarburos Argentina"</p>
          </div>
        </div>
      ),
    },
    {
      id: "glosario",
      title: "Glosario Técnico",
      icon: <FileText className="w-5 h-5" />,
      content: (
        <div className="space-y-3">
          {[
            { term: "BOP", def: "Blowout Preventer. Sistema de válvulas preventoras de pozo para controlar presiones inesperadas." },
            { term: "Casing", def: "Tubería de revestimiento que se cementa en el pozo para mantener la integridad del hoyo." },
            { term: "Christmas Tree", def: "Árbol de navidad. Conjunto de válvulas y accesorios en cabeza de pozo para controlar producción." },
            { term: "EEBA", def: "Emergency Escape Breathing Apparatus. Equipo de escape de emergencia con duración de 10-15 minutos." },
            { term: "SCBA", def: "Self-Contained Breathing Apparatus. Equipo de respiración autónomo para atmósferas IDLH." },
            { term: "Fracking", def: "Fracturación hidráulica. Técnica de estimulación para aumentar la permeabilidad de la formación." },
            { term: "H2S", def: "Ácido sulfhídrico. Gas altamente tóxico presente en yacimientos de Vaca Muerta." },
            { term: "IDLH", def: "Immediately Dangerous to Life or Health. Atmósfera que representa peligro inmediato para la vida." },
            { term: "IAPG", def: "Instituto Argentino del Petróleo y del Gas. Entidad que emite normativas técnicas para la industria." },
            { term: "Killing the well", def: "Procedimiento para controlar un pozo mediante circulación de fluido de mayor densidad." },
            { term: "Liner", def: "Tubería de revestimiento que no llega a superficie, suspendida dentro del casing anterior." },
            { term: "Muster Point", def: "Punto de reunión de emergencia ubicado a favor del viento, a 100m del wellhead." },
            { term: "PPE", def: "Personal Protective Equipment. Equipos de protección personal (cascos, guantes, respiradores)." },
            { term: "Proppant", def: "Material (arena o cerámica) inyectado en fracturas para mantenerlas abiertas." },
            { term: "ROP", def: "Rate of Penetration. Velocidad de penetración de la broca, medida en m/hora." },
            { term: "SCBA", def: "Self-Contained Breathing Apparatus. Equipo autónomo de respiración para ambientes peligrosos." },
            { term: "TVD", def: "True Vertical Depth. Profundidad vertical verdadera del pozo." },
            { term: "WOB", def: "Weight on Bit. Peso sobre la broca durante la perforación." },
          ].map((item, idx) => (
            <div key={idx} className="border-b border-gray-100 pb-2 last:border-0">
              <dt className="font-semibold text-petro-blue text-sm">{item.term}</dt>
              <dd className="text-sm text-gray-600 mt-0.5">{item.def}</dd>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: "faq",
      title: "Preguntas Frecuentes",
      icon: <HelpCircle className="w-5 h-5" />,
      content: (
        <div className="space-y-4">
          {[
            {
              q: "¿PetroQuery tiene conocimiento propio o necesito cargar documentos?",
              a: "PetroQuery NO tiene conocimiento propio. Responde exclusivamente sobre los PDFs que vos cargues. Si no hay documentos cargados, no podrá responder.",
            },
            {
              q: "¿Puedo subir documentos en inglés?",
              a: "Sí, el sistema soporta español e inglés. Sin embargo, las respuestas siempre se generan en español técnico para mantener consistencia con el sector en Argentina.",
            },
            {
              q: "¿Cuántos PDFs puedo cargar?",
              a: "No hay límite técnico estricto. El sistema procesa cada PDF en background, así que podés subir múltiples documentos simultáneamente.",
            },
            {
              q: "¿Qué pasa si el sistema no encuentra la respuesta?",
              a: "Indicará claramente: \"La información no está disponible en los documentos cargados.\" Nunca inventa datos. Siempre te dirá que consultes al departamento de ingeniería correspondiente.",
            },
            {
              q: "¿Por qué aparece 'Revisión humana requerida' en algunas respuestas?",
              a: "Aparece automáticamente cuando: (1) el score de confianza es menor a 70%, o (2) la consulta es sobre seguridad (H2S, blowout, etc.). Es una medida de seguridad obligatoria.",
            },
            {
              q: "¿Los documentos que subo son privados?",
              a: "Sí. Cada usuario solo puede ver y consultar sus propios documentos. El sistema filtra por user_id en todas las búsquedas.",
            },
            {
              q: "¿Puedo descargar o compartir una conversación?",
              a: "Actualmente no hay función de exportación, pero está planeado para futuras versiones. Por ahora podés copiar y pegar la respuesta.",
            },
          ].map((faq, idx) => (
            <div key={idx} className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-semibold text-gray-900 text-sm mb-1">{faq.q}</h5>
              <p className="text-sm text-gray-600 leading-relaxed">{faq.a}</p>
            </div>
          ))}
        </div>
      ),
    },
  ];

  const activeContent = sections.find((s) => s.id === activeSection);

  return (
    <div className="min-h-screen bg-petro-gray">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-petro-blue flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Manual de Usuario</h1>
              <p className="text-xs text-gray-500">PetroQuery — Guía de referencia</p>
            </div>
          </div>
          <Link
            href="/chat"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-petro-blue text-white text-sm font-medium hover:bg-petro-dark transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver al chat
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8 flex gap-8">
        {/* Sidebar */}
        <aside className="w-72 flex-shrink-0">
          <nav className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900 text-sm">Contenido</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left text-sm transition-colors",
                    activeSection === section.id
                      ? "bg-petro-light text-petro-blue font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  )}
                >
                  <span
                    className={cn(
                      "flex-shrink-0",
                      activeSection === section.id ? "text-petro-blue" : "text-gray-400"
                    )}
                  >
                    {section.icon}
                  </span>
                  <span>{section.title}</span>
                  <ChevronRight
                    className={cn(
                      "w-4 h-4 ml-auto flex-shrink-0 transition-transform",
                      activeSection === section.id ? "rotate-90 text-petro-blue" : "text-gray-300"
                    )}
                  />
                </button>
              ))}
            </div>
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-6 py-5 border-b border-gray-200">
              <h2 className="text-lg font-bold text-gray-900">
                {activeContent?.title}
              </h2>
            </div>
            <div className="px-6 py-6">{activeContent?.content}</div>
          </div>
        </main>
      </div>
    </div>
  );
}
