"use client";

import { cn } from "@/lib/utils";
import { Message, OGTechnicalAnswer } from "@/lib/types";
import SafetyBanner from "./SafetyBanner";
import ConfidenceBadge from "./ConfidenceBadge";
import SourceCard from "./SourceCard";
import NumberHighlighter from "./NumberHighlighter";
import { User, Bot, AlertTriangle, FileBadge } from "lucide-react";

interface ChatMessageProps {
  message: Message;
}

function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-2" />;
        if (trimmed.startsWith("# ")) {
          return (
            <h1 key={i} className="text-lg font-bold text-gray-900 mt-2">
              {trimmed.replace("# ", "")}
            </h1>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h2 key={i} className="text-base font-bold text-gray-800 mt-2">
              {trimmed.replace("## ", "")}
            </h2>
          );
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={i} className="text-sm font-bold text-gray-700 mt-1">
              {trimmed.replace("### ", "")}
            </h3>
          );
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <li key={i} className="ml-4 list-disc text-sm text-gray-700">
              {renderInline(trimmed.replace(/^[-*] /, ""))}
            </li>
          );
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return (
            <li key={i} className="ml-4 list-decimal text-sm text-gray-700">
              {renderInline(trimmed.replace(/^\d+\.\s/, ""))}
            </li>
          );
        }
        return (
          <p key={i} className="text-sm text-gray-700 leading-relaxed">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-gray-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <NumberHighlighter key={i} text={part} />;
  });
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  // Prefer local answer_data, fall back to structured_response from API
  const answer: OGTechnicalAnswer | undefined = message.answer_data || message.structured_response;

  return (
    <div
      className={cn(
        "flex gap-4 max-w-5xl",
        isUser ? "ml-auto flex-row-reverse" : ""
      )}
    >
      <div
        className={cn(
          "w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm",
          isUser ? "bg-petro-blue" : "bg-petro-orange"
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      <div className={cn("flex-1 space-y-3", isUser ? "text-right" : "")}>
        <div
          className={cn(
            "inline-block px-5 py-4 rounded-2xl max-w-[85%] shadow-sm",
            isUser
              ? "bg-petro-blue text-white"
              : "bg-white text-gray-900 border border-gray-200"
          )}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : answer ? (
            <div className="space-y-3">
              {answer.advertencia_seguridad && (
                <SafetyBanner warning={answer.advertencia_seguridad} />
              )}

              <SimpleMarkdown text={answer.respuesta_tecnica} />

              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100">
                <ConfidenceBadge score={answer.score_global_confianza} />
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-petro-light text-petro-blue border border-petro-blue/10 uppercase tracking-wide">
                  <FileBadge className="w-3 h-3" />
                  {answer.tipo_consulta}
                </span>
              </div>

              {answer.necesita_revision_humana && (
                <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700 font-medium">
                    Esta respuesta requiere revisión humana antes de su aplicación operativa.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          )}
        </div>

        {!isUser && answer && answer.fuentes.length > 0 && (
          <div className="space-y-2 max-w-[85%]">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Fuentes consultadas
            </p>
            {answer.fuentes.map((fuente, idx) => (
              <SourceCard key={idx} source={fuente} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
