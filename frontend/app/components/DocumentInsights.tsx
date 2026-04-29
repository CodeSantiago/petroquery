"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { FileText, Lightbulb, ListChecks, ChevronDown, ChevronUp, Sparkles } from "lucide-react";

interface SectionOld {
  name: string;
  page?: number;
}

interface SectionNew {
  name: string;
  topics?: string[];
  important_points?: string[];
  questions?: string[];
}

interface DocumentInsightsProps {
  insights: {
    summary?: string;
    sections?: string[] | SectionOld[] | SectionNew[];
    questions?: string[];
  } | null;
  onAskQuestion?: (question: string) => void;
}

export default function DocumentInsights({ insights, onAskQuestion }: DocumentInsightsProps) {
  const [expanded, setExpanded] = useState(true);

  if (!insights || (!insights.summary && !insights.sections?.length && !insights.questions?.length)) {
    return null;
  }

  const displaySections = insights.sections?.map((s) => (typeof s === "string" ? s : s.name)) ?? [];

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-petro-light/50 hover:bg-petro-light transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-petro-blue" />
          <span className="text-sm font-semibold text-petro-blue">Resumen del documento</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-4 py-3 space-y-4">
          {/* Summary */}
          {insights.summary && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <FileText className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Resumen técnico</span>
              </div>
              <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-petro-gray rounded-lg p-3">
                {insights.summary}
              </div>
            </div>
          )}

          {/* Sections */}
          {displaySections.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <ListChecks className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Secciones detectadas</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {displaySections.map((section, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 rounded-full text-xs font-medium bg-petro-light text-petro-blue border border-petro-blue/10"
                  >
                    {section}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Questions */}
          {insights.questions && insights.questions.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Preguntas sugeridas</span>
              </div>
              <div className="space-y-2">
                {insights.questions.map((question, i) => (
                  <button
                    key={i}
                    onClick={() => onAskQuestion?.(question)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg text-sm",
                      "bg-white border border-gray-200 hover:border-petro-blue/30 hover:bg-petro-light/30",
                      "transition-colors duration-200"
                    )}
                  >
                    <span className="text-petro-blue font-medium mr-2">{i + 1}.</span>
                    <span className="text-gray-700">{question}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
