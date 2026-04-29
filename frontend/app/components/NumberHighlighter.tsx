"use client";

import { cn } from "@/lib/utils";

interface NumberHighlighterProps {
  text: string;
  className?: string;
}

// Pattern: number + technical unit (case insensitive)
const TECH_NUMBER_REGEX = /(\d[\d,\.]*)\s*(bar|psi|kPa|MPa|atm|°C|°F|K|m|ft|km|ppg|g\/cm³|kg\/m³|ppm|ppb|%|bbl|gal|l\/min|m³\/d|bbl\/d)/gi;

export default function NumberHighlighter({ text, className }: NumberHighlighterProps) {
  if (!text) return null;

  const parts: (string | { type: "number"; value: string; unit: string })[] = [];
  let lastIndex = 0;
  let match;

  const regex = new RegExp(TECH_NUMBER_REGEX.source, TECH_NUMBER_REGEX.flags);
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push({ type: "number", value: match[1], unit: match[2] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return (
    <span className={className}>
      {parts.map((part, i) => {
        if (typeof part === "string") {
          return <span key={i}>{part}</span>;
        }
        return (
          <span
            key={i}
            className={cn(
              "inline font-mono text-xs px-1 py-0.5 rounded",
              "bg-yellow-50 text-yellow-900 border border-yellow-200/60"
            )}
            title={`Valor técnico: ${part.value} ${part.unit}`}
          >
            {part.value} {part.unit}
          </span>
        );
      })}
    </span>
  );
}
