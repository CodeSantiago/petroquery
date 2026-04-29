"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { FileText, BookOpen, ChevronDown, Lightbulb, ListChecks, Target, GripVertical } from "lucide-react";

interface SectionInsight {
  name: string;
  topics?: string[];
  important_points?: string[];
  questions?: string[];
}

interface DocumentOutlineProps {
  title: string;
  summary?: string;
  global_topics?: string[];
  global_questions?: string[];
  sections: SectionInsight[];
  onAskQuestion?: (question: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function DocumentOutline({
  title,
  summary,
  global_topics = [],
  global_questions = [],
  sections,
  onAskQuestion,
  isOpen,
  onClose,
}: DocumentOutlineProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const toggleSection = (sectionName: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionName)) {
        next.delete(sectionName);
      } else {
        next.add(sectionName);
      }
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <aside className="w-80 bg-white border-l border-gray-200 flex flex-col shadow-sm overflow-hidden">
      {/* Header - fixed */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-petro-blue" />
          <span className="text-sm font-semibold text-gray-900">Contenido</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Scrollable content - takes remaining height */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 overscroll-contain">
        {/* Document title */}
        <div className="flex items-start gap-2 pb-2 border-b border-gray-100">
          <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm font-medium text-gray-800 leading-tight">{title}</p>
        </div>

        {/* Summary - collapsible card */}
        {summary && (
          <details className="group rounded-lg border border-gray-200 overflow-hidden">
            <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 list-none">
              <ListChecks className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Resumen</span>
              <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-auto transition-transform group-open:rotate-180" />
            </summary>
            <div className="px-3 pb-3 pt-1">
              <p className="text-xs text-gray-600 leading-relaxed">{summary}</p>
            </div>
          </details>
        )}

        {/* Global Topics */}
        {global_topics.length > 0 && (
          <div className="rounded-lg border border-gray-200 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <ListChecks className="w-3.5 h-3.5 text-petro-blue" />
              <span className="text-xs font-medium text-petro-blue uppercase tracking-wide">Temas del documento</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {global_topics.map((topic, i) => (
                <span
                  key={i}
                  className="px-2 py-1 rounded-lg text-xs font-medium bg-petro-light text-petro-blue border border-petro-blue/20"
                >
                  {topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Chapters - main interactive section */}
        {sections.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Capítulos ({sections.length})
              </span>
            </div>

            <div className="space-y-1">
              {sections.map((section, i) => {
                const isExpanded = expandedSections.has(section.name);
                const hasContent = (section.topics?.length || 0) + (section.important_points?.length || 0) + (section.questions?.length || 0) > 0;

                return (
                  <div
                    key={i}
                    className={cn(
                      "rounded-lg border overflow-hidden transition-all",
                      activeSection === section.name
                        ? "border-petro-blue/50 bg-petro-light/30"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    )}
                  >
                    {/* Chapter header - always clickable */}
                    <button
                      onClick={() => {
                        setActiveSection(activeSection === section.name ? null : section.name);
                        toggleSection(section.name);
                      }}
                      className={cn(
                        "w-full flex items-center gap-2 px-3 py-2.5 text-sm text-left transition-colors",
                        isExpanded ? "bg-gray-50" : ""
                      )}
                    >
                      <GripVertical className="w-3 h-3 text-gray-300 flex-shrink-0" />
                      <span className="flex-1 font-semibold text-gray-700 truncate">
                        {i + 1}. {section.name}
                      </span>
                      <ChevronDown
                        className={cn(
                          "w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-200",
                          isExpanded ? "rotate-0" : "-rotate-90"
                        )}
                      />
                    </button>

                    {/* Expanded content */}
                    {isExpanded && (
                      <div className="px-3 pb-4 pt-2 space-y-4 border-t border-gray-100">
                        {/* Topics sub-section */}
                        {section.topics && section.topics.length > 0 && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-1.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Temas</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 pl-3">
                              {section.topics.map((topic, ti) => (
                                <span
                                  key={ti}
                                  className="px-2 py-1 rounded-md text-xs bg-blue-50 text-blue-800 border border-blue-100"
                                >
                                  {topic}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Important Points sub-section */}
                        {section.important_points && section.important_points.length > 0 && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-1.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                              <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Puntos clave</span>
                            </div>
                            <ul className="space-y-1.5 pl-3">
                              {section.important_points.map((point, pi) => (
                                <li
                                  key={pi}
                                  className="text-xs text-gray-600 leading-relaxed pl-2 py-1 bg-amber-50/50 rounded border-l-2 border-amber-400"
                                >
                                  {point}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Questions sub-section */}
                        {section.questions && section.questions.length > 0 && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-1.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                              <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">Preguntas sugeridas</span>
                            </div>
                            <div className="space-y-1 pl-3">
                              {section.questions.map((question, qi) => (
                                <button
                                  key={qi}
                                  onClick={() => onAskQuestion?.(question)}
                                  className={cn(
                                    "w-full text-left px-3 py-2 rounded-lg text-xs",
                                    "bg-purple-50 text-purple-800 border border-purple-100",
                                    "hover:bg-purple-100 transition-colors"
                                  )}
                                >
                                  <span className="font-medium mr-1.5">{qi + 1}.</span>
                                  {question}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Global Questions at bottom */}
        {global_questions.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <div className="flex items-center gap-1.5 mb-3">
              <Lightbulb className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Preguntas generales ({global_questions.length})
              </span>
            </div>
            <div className="space-y-2">
              {global_questions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => onAskQuestion?.(question)}
                  className={cn(
                    "w-full text-left px-3 py-2.5 rounded-lg text-xs",
                    "bg-gray-50 border border-gray-200 hover:border-petro-blue/30 hover:bg-petro-light/30",
                    "transition-colors text-gray-700 leading-relaxed"
                  )}
                >
                  <span className="text-petro-blue font-semibold mr-1.5">{i + 1}.</span>
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}