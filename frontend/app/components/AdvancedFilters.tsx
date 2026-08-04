"use client";

import { useState } from "react";
import { FilterParams } from "@/lib/types";
import { Filter, ChevronDown, ChevronUp, X } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface AdvancedFiltersProps {
  filters: FilterParams;
  onChange: (filters: FilterParams) => void;
}

export default function AdvancedFilters({ filters, onChange }: AdvancedFiltersProps) {
  const { t, language } = useLanguage();
  const [open, setOpen] = useState(false);

  const CUENCAS = [t("filters.all"), t("basin.vacaMuerta"), t("basin.neuquina"), t("basin.golfoSanJorge"), t("basin.cuyana")];
  const TIPOS_DOCUMENTO = [t("filters.allOptions"), t("docType.manual"), t("docType.regulation"), t("docType.report"), t("docType.specification")];
  const TIPOS_EQUIPO = [t("filters.allOptions"), t("equip.bop"), t("equip.casing"), t("equip.tubing"), t("equip.christmasTree"), t("equip.pumpjack")];
  const NORMATIVAS = [t("filters.allOptions"), t("reg.iapg"), t("reg.api14b"), t("reg.api14c"), t("reg.api75"), t("reg.asme")];

  const update = (key: keyof FilterParams, value: string) => {
    const allValue = language === "es" ? "Todas" : t("filters.all");
    const allOptionsValue = language === "es" ? "Todos" : t("filters.allOptions");
    onChange({
      ...filters,
      [key]: value === allValue || value === allOptionsValue ? undefined : value,
    });
  };

  const hasActive =
    filters.cuenca ||
    filters.tipo_documento ||
    filters.tipo_equipo ||
    filters.normativa_aplicable;

  const clear = () => {
    onChange({});
  };

  return (
    <div className="w-full">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-petro-blue hover:text-petro-dark font-medium transition-colors"
      >
        <Filter className="w-4 h-4" />
        {t("filters.title")}
        {hasActive && (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-petro-orange text-white text-[10px] font-bold">
            !
          </span>
        )}
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {open && (
        <div className="mt-3 p-4 bg-white border border-gray-200 rounded-xl shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in slide-in-from-top-1 duration-200">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              {t("filters.basin")}
            </label>
            <select
              value={filters.cuenca || t("filters.all")}
              onChange={(e) => update("cuenca", e.target.value)}
              className="w-full px-3 py-2 bg-petro-gray border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-petro-blue/30 focus:border-petro-blue"
            >
              {CUENCAS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              {t("filters.docType")}
            </label>
            <select
              value={filters.tipo_documento || t("filters.allOptions")}
              onChange={(e) => update("tipo_documento", e.target.value)}
              className="w-full px-3 py-2 bg-petro-gray border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-petro-blue/30 focus:border-petro-blue"
            >
              {TIPOS_DOCUMENTO.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              {t("filters.equipmentType")}
            </label>
            <select
              value={filters.tipo_equipo || t("filters.allOptions")}
              onChange={(e) => update("tipo_equipo", e.target.value)}
              className="w-full px-3 py-2 bg-petro-gray border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-petro-blue/30 focus:border-petro-blue"
            >
              {TIPOS_EQUIPO.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              {t("filters.regulation")}
            </label>
            <select
              value={filters.normativa_aplicable || t("filters.allOptions")}
              onChange={(e) => update("normativa_aplicable", e.target.value)}
              className="w-full px-3 py-2 bg-petro-gray border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-petro-blue/30 focus:border-petro-blue"
            >
              {NORMATIVAS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          {hasActive && (
            <div className="sm:col-span-2 lg:col-span-4 flex justify-end">
              <button
                onClick={clear}
                className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-700 font-medium"
              >
                <X className="w-3 h-3" /> {t("filters.clear")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
