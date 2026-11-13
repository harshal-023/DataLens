import React, { useState } from 'react';
import {
  Briefcase,
  Compass,
  CheckCircle,
  Edit2,
  Check,
  X,
  Target,
  Layers,
  Sparkles,
} from 'lucide-react';
import { BusinessContext, IntelligenceService } from '../../services/intelligenceService';

interface Props {
  datasetId: string;
  versionId: string;
  businessContext?: BusinessContext | null;
  onRefresh: () => void;
}

const DOMAINS = [
  'SALES',
  'FINANCE',
  'MARKETING',
  'CUSTOMER_ANALYTICS',
  'OPERATIONS',
  'INVENTORY',
  'HUMAN_RESOURCES',
  'LOGISTICS',
  'GENERAL_BUSINESS',
];

export const BusinessContextCard: React.FC<Props> = ({
  datasetId,
  versionId,
  businessContext,
  onRefresh,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [domain, setDomain] = useState(businessContext?.business_domain || 'GENERAL_BUSINESS');
  const [purpose, setPurpose] = useState(businessContext?.purpose || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await IntelligenceService.updateBusinessContext(
        datasetId,
        {
          business_domain: domain,
          purpose,
          is_user_confirmed: true,
        },
        versionId
      );
      setIsEditing(false);
      onRefresh();
    } catch (err) {
      console.error('Failed to update business context', err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!businessContext) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-center shadow-sm">
        <Briefcase className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-700">No Business Context Synthesized</h4>
        <p className="text-xs text-slate-500 mt-1">
          Run intelligence profiling on this dataset to automatically detect business domain, entities, and suggested KPIs.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-[#009F98]" />
          <h3 className="font-semibold text-slate-900 text-sm">Business Domain & Analytical Context</h3>
          {businessContext.is_user_confirmed ? (
            <span className="text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> User Confirmed
            </span>
          ) : (
            <span className="text-[10px] font-medium bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 rounded-full flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-[#009F98]" /> AI Inferred
            </span>
          )}
        </div>

        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" /> Edit Context
          </button>
        ) : (
          <div className="flex items-center gap-1">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-2.5 py-1 bg-[#009F98] hover:bg-[#008983] text-white rounded text-xs font-medium flex items-center gap-1"
            >
              <Check className="w-3.5 h-3.5" /> Save
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="p-1 text-slate-400 hover:bg-slate-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <div className="p-5 space-y-4">
        {/* Domain Badge & Purpose */}
        <div className="flex flex-col md:flex-row md:items-start gap-4">
          <div className="shrink-0">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              Business Domain
            </span>
            {isEditing ? (
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="text-xs px-2.5 py-1.5 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#009F98]"
              >
                {DOMAINS.map((d) => (
                  <option key={d} value={d}>
                    {d.replace('_', ' ')}
                  </option>
                ))}
              </select>
            ) : (
              <span className="inline-block px-3 py-1 bg-slate-900 text-white rounded-lg text-xs font-bold tracking-wide">
                {businessContext.business_domain.replace('_', ' ')}
              </span>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              Analytical Dataset Purpose
            </span>
            {isEditing ? (
              <textarea
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                rows={2}
                className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#009F98]"
              />
            ) : (
              <p className="text-xs text-slate-700 leading-relaxed">
                {businessContext.purpose || 'No analytical purpose recorded.'}
              </p>
            )}
          </div>
        </div>

        {/* Entities, Dimensions & Measures Badges */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-slate-100">
          <div>
            <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1.5 flex items-center gap-1">
              <Compass className="w-3 h-3" /> Core Entities
            </span>
            <div className="flex flex-wrap gap-1">
              {businessContext.important_entities?.length > 0 ? (
                businessContext.important_entities.map((e) => (
                  <span
                    key={e}
                    className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-[11px] font-medium"
                  >
                    {e}
                  </span>
                ))
              ) : (
                <span className="text-slate-400 text-xs italic">None identified</span>
              )}
            </div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1.5 flex items-center gap-1">
              <Layers className="w-3 h-3" /> Key Dimensions
            </span>
            <div className="flex flex-wrap gap-1">
              {businessContext.key_dimensions?.slice(0, 4).map((d) => (
                <span
                  key={d}
                  className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[11px]"
                >
                  {d}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1.5 flex items-center gap-1">
              <Target className="w-3 h-3" /> Important Measures
            </span>
            <div className="flex flex-wrap gap-1">
              {businessContext.important_measures?.slice(0, 4).map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded text-[11px] font-medium"
                >
                  {m}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Suggested Domain KPIs */}
        {businessContext.suggested_kpis?.length > 0 && (
          <div className="pt-3 border-t border-slate-100">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-2">
              Suggested Business KPIs
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {businessContext.suggested_kpis.map((kpi, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors"
                >
                  <div className="font-semibold text-slate-900 text-xs">{kpi.name}</div>
                  <div className="font-mono text-[11px] text-[#009F98] mt-0.5">{kpi.formula}</div>
                  <div className="text-[10px] text-slate-500 mt-1 line-clamp-1">
                    {kpi.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

