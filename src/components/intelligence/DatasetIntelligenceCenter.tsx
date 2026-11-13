import React, { useState, useEffect } from 'react';
import {
  Brain,
  Sparkles,
  Layers,
  Link2,
  Briefcase,
  Calculator,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  CheckCircle,
} from 'lucide-react';
import {
  DatasetIntelligenceBundle,
  IntelligenceService,
} from '../../services/intelligenceService';
import { ColumnSemanticsTable } from './ColumnSemanticsTable';
import { RelationshipExplorer } from './RelationshipExplorer';
import { BusinessContextCard } from './BusinessContextCard';
import { MetricLibrary } from './MetricLibrary';

interface Props {
  datasetId: string;
  versionId?: string;
  datasetName: string;
}

export const DatasetIntelligenceCenter: React.FC<Props> = ({
  datasetId,
  versionId,
  datasetName,
}) => {
  const [bundle, setBundle] = useState<DatasetIntelligenceBundle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProfiling, setIsProfiling] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<'columns' | 'relationships' | 'context' | 'metrics'>('columns');
  const [error, setError] = useState<string | null>(null);

  const loadIntelligence = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await IntelligenceService.getIntelligenceBundle(datasetId, versionId);
      setBundle(data);
    } catch (err: any) {
      console.error('Failed to load dataset intelligence', err);
      setError(err?.message || 'Unable to load dataset intelligence bundle.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadIntelligence();
  }, [datasetId, versionId]);

  const handleRunProfiling = async () => {
    setIsProfiling(true);
    setError(null);
    try {
      const updated = await IntelligenceService.runProfiling(datasetId, versionId);
      setBundle(updated);
    } catch (err: any) {
      console.error('Profiling error', err);
      setError(err?.message || 'Profiling run failed. Check backend logs.');
    } finally {
      setIsProfiling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-sm">
        <RefreshCw className="w-8 h-8 text-[#009F98] animate-spin mx-auto mb-3" />
        <h4 className="text-sm font-semibold text-slate-800">Loading Dataset Intelligence...</h4>
        <p className="text-xs text-slate-500 mt-1">
          Retrieving column semantic layer, entity relationships, and metric definitions.
        </p>
      </div>
    );
  }

  const qualityScore = bundle?.profile?.quality_score ?? 100;
  const warnings = bundle?.profile?.warnings || [];

  return (
    <div className="space-y-4">
      {/* Top Intelligence Hero & Status Banner */}
      <div className="bg-gradient-to-r from-[#102C46] to-[#0d3f54] text-white p-5 rounded-2xl shadow-md border border-slate-700">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-white/10 rounded-xl backdrop-blur-sm border border-white/15">
              <Brain className="w-6 h-6 text-[#39C3B8]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight">Dataset Intelligence Center</h2>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#009F98] text-white">
                  Semantic Layer
                </span>
                {bundle?.version_number && (
                  <span className="text-xs font-mono text-slate-300 bg-white/10 px-2 py-0.5 rounded">
                    {bundle.version_number}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Business semantic layer, multi-signal column classification, and DuckDB analytical metrics.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quality Score Indicator */}
            <div className="bg-white/10 px-3.5 py-1.5 rounded-xl border border-white/15 text-center">
              <span className="text-[10px] uppercase tracking-wider text-slate-300 block font-semibold">
                Quality Score
              </span>
              <span
                className={`text-base font-bold ${
                  qualityScore >= 80 ? 'text-[#39C3B8]' : qualityScore >= 60 ? 'text-amber-300' : 'text-rose-300'
                }`}
              >
                {qualityScore}/100
              </span>
            </div>

            <button
              onClick={handleRunProfiling}
              disabled={isProfiling}
              className="px-4 py-2 bg-[#009F98] hover:bg-[#008983] text-white text-xs font-semibold rounded-xl flex items-center gap-2 shadow-sm transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${isProfiling ? 'animate-spin' : ''}`} />
              {isProfiling ? 'Running Intelligence Profiler...' : 'Run Intelligence Profiler'}
            </button>
          </div>
        </div>

        {/* Quality Warnings Pill Alert */}
        {warnings.length > 0 && (
          <div className="mt-4 pt-3 border-t border-white/10 flex items-center gap-2 text-xs text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>{warnings.length} data quality signal(s) detected:</strong>{' '}
              {warnings.map((w) => w.message).slice(0, 2).join('; ')}
              {warnings.length > 2 ? ` (+${warnings.length - 2} more)` : ''}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200">
        <button
          onClick={() => setActiveSubTab('columns')}
          className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
            activeSubTab === 'columns'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          Column Semantics ({bundle?.columns.length || 0})
        </button>

        <button
          onClick={() => setActiveSubTab('relationships')}
          className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
            activeSubTab === 'relationships'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Link2 className="w-4 h-4" />
          Relationships ({bundle?.relationships.length || 0})
        </button>

        <button
          onClick={() => setActiveSubTab('context')}
          className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
            activeSubTab === 'context'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          Business Context
        </button>

        <button
          onClick={() => setActiveSubTab('metrics')}
          className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
            activeSubTab === 'metrics'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Calculator className="w-4 h-4" />
          Metric Library ({bundle?.metrics.length || 0})
        </button>
      </div>

      {/* Tab Panels */}
      {activeSubTab === 'columns' && (
        <ColumnSemanticsTable
          datasetId={datasetId}
          versionId={bundle?.version_id || ''}
          columns={bundle?.columns || []}
          onRefresh={loadIntelligence}
        />
      )}

      {activeSubTab === 'relationships' && (
        <RelationshipExplorer
          datasetId={datasetId}
          relationships={bundle?.relationships || []}
          onRefresh={loadIntelligence}
        />
      )}

      {activeSubTab === 'context' && (
        <BusinessContextCard
          datasetId={datasetId}
          versionId={bundle?.version_id || ''}
          businessContext={bundle?.business_context}
          onRefresh={loadIntelligence}
        />
      )}

      {activeSubTab === 'metrics' && (
        <MetricLibrary
          datasetId={datasetId}
          metrics={bundle?.metrics || []}
          onRefresh={loadIntelligence}
        />
      )}
    </div>
  );
};

