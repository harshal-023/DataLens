import React, { useState } from 'react';
import {
  Link2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { DatasetRelationship, IntelligenceService } from '../../services/intelligenceService';

interface Props {
  datasetId: string;
  relationships: DatasetRelationship[];
  onRefresh: () => void;
}

export const RelationshipExplorer: React.FC<Props> = ({
  datasetId,
  relationships,
  onRefresh,
}) => {
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleDiscover = async () => {
    setIsDiscovering(true);
    try {
      await IntelligenceService.discoverRelationships(datasetId);
      onRefresh();
    } catch (err) {
      console.error('Failed to discover relationships', err);
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleUpdateStatus = async (
    relId: string,
    newStatus: 'CONFIRMED' | 'REJECTED'
  ) => {
    setUpdatingId(relId);
    try {
      await IntelligenceService.updateRelationship(datasetId, relId, newStatus);
      onRefresh();
    } catch (err) {
      console.error('Failed to update relationship status', err);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
            <Link2 className="w-4 h-4 text-[#009F98]" />
            <span>Dataset Relationship Intelligence</span>
            <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-normal">
              {relationships.length} links
            </span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-table referential relationships, key uniqueness, and join cardinality warnings.
          </p>
        </div>
        <div>
          <button
            onClick={handleDiscover}
            disabled={isDiscovering}
            className="px-3 py-1.5 bg-[#009F98] hover:bg-[#008983] text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {isDiscovering ? 'Discovering...' : 'Auto-Discover Relationships'}
          </button>
        </div>
      </div>

      <div className="p-4">
        {relationships.length === 0 ? (
          <div className="text-center py-10 px-4">
            <Link2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-slate-700">No Relationships Discovered</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
              Click 'Auto-Discover' to automatically detect joins with other datasets in this workspace based on key overlap and semantic matching.
            </p>
            <button
              onClick={handleDiscover}
              disabled={isDiscovering}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors"
            >
              Scan Workspace for Matching Tables
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {relationships.map((rel) => {
              const isUpdating = updatingId === rel.id;
              const isConfirmed = rel.status === 'CONFIRMED';
              const isRejected = rel.status === 'REJECTED';
              const isManyToMany = rel.relationship_type === 'MANY_TO_MANY';

              return (
                <div
                  key={rel.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isRejected
                      ? 'border-slate-200 bg-slate-50/50 opacity-60'
                      : isConfirmed
                      ? 'border-emerald-200 bg-emerald-50/20'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        rel.relationship_type === 'ONE_TO_ONE'
                          ? 'bg-blue-100 text-blue-800'
                          : rel.relationship_type === 'MANY_TO_ONE'
                          ? 'bg-purple-100 text-purple-800'
                          : rel.relationship_type === 'ONE_TO_MANY'
                          ? 'bg-indigo-100 text-indigo-800'
                          : 'bg-amber-100 text-amber-800 border border-amber-300'
                      }`}
                    >
                      {rel.relationship_type.replace(/_/g, ' ')}
                    </span>

                    <span className="text-[11px] text-slate-500 font-mono">
                      Confidence: {Math.round(rel.confidence_score * 100)}%
                    </span>
                  </div>

                  {/* Visual Join Path */}
                  <div className="flex items-center gap-2 py-3 px-3 bg-slate-50 rounded-lg border border-slate-100 my-2">
                    <div className="flex-1 min-w-0">
                      <span className="text-[10px] uppercase text-slate-400 block font-semibold">
                        Source Column
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-800 truncate block">
                        {rel.source_column}
                      </span>
                    </div>

                    <ArrowRight className="w-4 h-4 text-slate-400 shrink-0" />

                    <div className="flex-1 min-w-0 text-right">
                      <span className="text-[10px] uppercase text-slate-400 block font-semibold">
                        Target Column
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-800 truncate block">
                        {rel.target_column}
                      </span>
                    </div>
                  </div>

                  {/* Join Cardinality Warnings */}
                  {rel.join_warning && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 text-[11px] text-amber-800 my-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <span>{rel.join_warning}</span>
                    </div>
                  )}

                  {/* Actions & Confirmation Status */}
                  <div className="flex items-center justify-between pt-2 mt-2 border-t border-slate-100 text-xs">
                    <div>
                      {isConfirmed ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-medium text-[11px]">
                          <CheckCircle className="w-3.5 h-3.5" /> Confirmed Link
                        </span>
                      ) : isRejected ? (
                        <span className="inline-flex items-center gap-1 text-slate-500 text-[11px]">
                          <XCircle className="w-3.5 h-3.5" /> Rejected
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-teal-700 text-[11px] font-medium">
                          <HelpCircle className="w-3.5 h-3.5 text-[#009F98]" /> Suggested by AI
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {!isConfirmed && (
                        <button
                          onClick={() => handleUpdateStatus(rel.id, 'CONFIRMED')}
                          disabled={isUpdating}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-medium transition-colors"
                        >
                          Confirm
                        </button>
                      )}
                      {!isRejected && (
                        <button
                          onClick={() => handleUpdateStatus(rel.id, 'REJECTED')}
                          disabled={isUpdating}
                          className="px-2 py-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded text-[11px] transition-colors"
                        >
                          Reject
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

