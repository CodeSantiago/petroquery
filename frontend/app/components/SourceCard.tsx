"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { SourceReference } from "@/lib/types";
import { FileText, ChevronDown, ChevronUp, ExternalLink, X, BookOpen } from "lucide-react";

interface SourceCardProps {
  source: SourceReference;
}

export default function SourceCard({ source }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const confidenceColor =
    source.score_confianza > 0.8
      ? "border-l-green-500"
      : source.score_confianza >= 0.7
      ? "border-l-yellow-500"
      : "border-l-red-500";

  const scoreBadgeColor =
    source.score_confianza > 0.8
      ? "bg-green-100 text-green-700"
      : source.score_confianza >= 0.7
      ? "bg-yellow-100 text-yellow-700"
      : "bg-red-100 text-red-700";

  return (
    <>
      <div
        className={cn(
          "rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden",
          "border-l-4",
          confidenceColor
        )}
      >
        <div className="p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 text-petro-blue flex-shrink-0" />
              <span className="font-semibold text-sm text-gray-900 truncate">
                {source.documento}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-petro-light text-petro-blue">
                Pág. {source.pagina}
              </span>
              <span
                className={cn(
                  "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                  scoreBadgeColor
                )}
              >
                {(source.score_confianza * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-2">
            {source.seccion && (
              <span className="text-xs text-gray-500">
                Sección: <span className="font-medium text-gray-700">{source.seccion}</span>
              </span>
            )}
            {source.tabla_referencia && (
              <span className="text-xs text-gray-500">
                Tabla: <span className="font-medium text-gray-700">{source.tabla_referencia}</span>
              </span>
            )}
            {source.figura_referencia && (
              <span className="text-xs text-gray-500">
                Figura: <span className="font-medium text-gray-700">{source.figura_referencia}</span>
              </span>
            )}
          </div>

          <div className="flex items-center justify-between mt-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-petro-blue hover:text-petro-dark font-medium flex items-center gap-1 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp className="w-3 h-3" /> Ocultar contenido
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" /> Ver contenido citado
                </>
              )}
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="text-xs text-petro-orange hover:text-petro-dark font-medium flex items-center gap-1 transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> Ver en documento
            </button>
          </div>
        </div>

        {expanded && (
          <div className="px-3 pb-3">
            <div className="bg-petro-gray rounded-md p-3 text-xs text-gray-700 leading-relaxed border border-gray-200">
              {source.contenido_citado}
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-petro-blue" />
                <h3 className="font-semibold text-gray-900">Detalle de fuente</h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* Document info */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-petro-gray rounded-lg p-3">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Documento</span>
                  <p className="font-medium text-gray-900 mt-1">{source.documento}</p>
                </div>
                <div className="bg-petro-gray rounded-lg p-3">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Página</span>
                  <p className="font-medium text-gray-900 mt-1">{source.pagina}</p>
                </div>
                {source.seccion && (
                  <div className="bg-petro-gray rounded-lg p-3">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Sección</span>
                    <p className="font-medium text-gray-900 mt-1">{source.seccion}</p>
                  </div>
                )}
                {source.tabla_referencia && (
                  <div className="bg-petro-gray rounded-lg p-3">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Tabla</span>
                    <p className="font-medium text-gray-900 mt-1">{source.tabla_referencia}</p>
                  </div>
                )}
                {source.figura_referencia && (
                  <div className="bg-petro-gray rounded-lg p-3">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Figura</span>
                    <p className="font-medium text-gray-900 mt-1">{source.figura_referencia}</p>
                  </div>
                )}
                <div className="bg-petro-gray rounded-lg p-3">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Score de confianza</span>
                  <p className={cn(
                    "font-medium mt-1",
                    source.score_confianza > 0.8 ? "text-green-700" :
                    source.score_confianza >= 0.7 ? "text-yellow-700" : "text-red-700"
                  )}>
                    {(source.score_confianza * 100).toFixed(1)}%
                  </p>
                </div>
                {source.cuenca && (
                  <div className="bg-petro-gray rounded-lg p-3">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Cuenca</span>
                    <p className="font-medium text-gray-900 mt-1">{source.cuenca}</p>
                  </div>
                )}
                {source.normativa_aplicable && (
                  <div className="bg-petro-gray rounded-lg p-3">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Normativa</span>
                    <p className="font-medium text-gray-900 mt-1">{source.normativa_aplicable}</p>
                  </div>
                )}
              </div>

              {/* Cited content */}
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wide font-semibold">
                  Contenido citado
                </span>
                <div className="mt-2 bg-petro-gray rounded-lg p-4 text-sm text-gray-700 leading-relaxed border border-gray-200 whitespace-pre-wrap">
                  {source.contenido_citado}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <p className="text-xs text-gray-500 text-center">
                Fuente consultada por PetroQuery con trazabilidad absoluta
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
