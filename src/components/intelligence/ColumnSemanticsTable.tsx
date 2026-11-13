import React, { useState } from 'react';
import {
  CheckCircle,
  Sparkles,
  HelpCircle,
  Tag,
  Hash,
  DollarSign,
  Percent,
  Calendar,
  Layers,
  Edit2,
  Check,
  X,
} from 'lucide-react';
import { ColumnSemantic, IntelligenceService } from '../../services/intelligenceService';

interface Props {
  datasetId: string;
  versionId: string;
  columns: ColumnSemantic[];
  onRefresh: () => void;
}

const SEMANTIC_ICONS: Record<string, React.ReactNode> = {
  currency: <DollarSign className="w-3.5 h-3.5 text-emerald-600" />,
  percentage: <Percent className="w-3.5 h-3.5 text-blue-600" />,
  quantity: <Hash className="w-3.5 h-3.5 text-purple-600" />,
  date: <Calendar className="w-3.5 h-3.5 text-amber-600" />,
  timestamp: <Calendar className="w-3.5 h-3.5 text-amber-600" />,
  status: <Tag className="w-3.5 h-3.5 text-teal-600" />,
  category: <Layers className="w-3.5 h-3.5 text-indigo-600" />,
};

export const ColumnSemanticsTable: React.FC<Props> = ({
  datasetId,
  versionId,
  columns,
  onRefresh,
}) => {
  const [editingCol, setEditingCol] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<ColumnSemantic>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = columns.filter(
    (c) =>
      c.column_name.toLowerCase().includes(search.toLowerCase()) ||
      c.business_name.toLowerCase().includes(search.toLowerCase()) ||
      c.semantic_type.toLowerCase().includes(search.toLowerCase())
  );

  const startEdit = (c: ColumnSemantic) => {
    setEditingCol(c.column_name);
    setEditForm({
      business_name: c.business_name,
      semantic_type: c.semantic_type,
      aggregation_method: c.aggregation_method,
      format_string: c.format_string,
      is_dimension: c.is_dimension,
      is_measure: c.is_measure,
    });
  };

  const handleSave = async (colName: string) => {
    setIsSaving(true);
    try {
      await IntelligenceService.updateColumnSemantics(
        datasetId,
        colName,
        { ...editForm, mapping_status: 'USER_CONFIRMED' },
        versionId
      );
      setEditingCol(null);
      onRefresh();
    } catch (err) {
      console.error('Failed to update column semantics', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleQuickConfirm = async (c: ColumnSemantic) => {
    try {
      await IntelligenceService.updateColumnSemantics(
        datasetId,
        c.column_name,
        { mapping_status: 'USER_CONFIRMED' },
        versionId
      );
      onRefresh();
    } catch (err) {
      console.error('Failed to confirm mapping', err);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
            <span>Column Semantic Layer & Business Glossary</span>
            <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-normal">
              {columns.length} columns
            </span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            AI-inferred business meanings, metric aggregations, and confirmed mappings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Filter columns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#009F98] w-48"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
            <tr>
              <th className="py-2.5 px-3">Physical Column</th>
              <th className="py-2.5 px-3">Business Name</th>
              <th className="py-2.5 px-3">Semantic Type</th>
              <th className="py-2.5 px-3">Role</th>
              <th className="py-2.5 px-3">Default Aggregation</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No columns matching criteria.
                </td>
              </tr>
            ) : (
              filtered.map((c) => {
                const isEditing = editingCol === c.column_name;
                const isConfirmed = c.mapping_status === 'USER_CONFIRMED';

                return (
                  <tr key={c.column_name} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-mono text-slate-700 font-medium">
                      {c.column_name}
                      <span className="ml-1.5 text-[10px] text-slate-400 uppercase">
                        {c.physical_type}
                      </span>
                    </td>

                    <td className="py-2.5 px-3">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.business_name || ''}
                          onChange={(e) =>
                            setEditForm({ ...editForm, business_name: e.target.value })
                          }
                          className="px-2 py-1 border border-slate-300 rounded text-xs w-full focus:ring-1 focus:ring-[#009F98]"
                        />
                      ) : (
                        <span className="font-semibold text-slate-900">{c.business_name}</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3">
                      {isEditing ? (
                        <select
                          value={editForm.semantic_type || c.semantic_type}
                          onChange={(e) =>
                            setEditForm({ ...editForm, semantic_type: e.target.value })
                          }
                          className="px-2 py-1 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#009F98]"
                        >
                          <option value="currency">Currency</option>
                          <option value="percentage">Percentage</option>
                          <option value="quantity">Quantity</option>
                          <option value="date">Date</option>
                          <option value="timestamp">Timestamp</option>
                          <option value="customer_identifier">Customer Identifier</option>
                          <option value="product_identifier">Product Identifier</option>
                          <option value="transaction_identifier">Transaction Identifier</option>
                          <option value="email">Email</option>
                          <option value="phone">Phone</option>
                          <option value="geographic_region">Geographic Region</option>
                          <option value="status">Status</option>
                          <option value="category">Category</option>
                          <option value="numeric">Numeric</option>
                          <option value="text">Text</option>
                        </select>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-800">
                          {SEMANTIC_ICONS[c.semantic_type] || (
                            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                          )}
                          <span className="capitalize">{c.semantic_type.replace('_', ' ')}</span>
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <label className="flex items-center gap-1 text-[11px]">
                            <input
                              type="checkbox"
                              checked={!!editForm.is_measure}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  is_measure: e.target.checked,
                                  is_dimension: !e.target.checked,
                                })
                              }
                            />
                            Measure
                          </label>
                        </div>
                      ) : (
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase ${
                            c.is_measure
                              ? 'bg-purple-50 text-purple-700 border border-purple-200'
                              : c.is_primary_key
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-blue-50 text-blue-700 border border-blue-200'
                          }`}
                        >
                          {c.is_primary_key ? 'Primary Key' : c.is_measure ? 'Measure' : 'Dimension'}
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3">
                      {isEditing ? (
                        <select
                          value={editForm.aggregation_method || c.aggregation_method}
                          onChange={(e) =>
                            setEditForm({ ...editForm, aggregation_method: e.target.value })
                          }
                          className="px-2 py-1 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#009F98]"
                        >
                          <option value="NONE">NONE</option>
                          <option value="SUM">SUM</option>
                          <option value="AVG">AVG</option>
                          <option value="COUNT">COUNT</option>
                          <option value="COUNT_DISTINCT">COUNT DISTINCT</option>
                          <option value="MIN">MIN</option>
                          <option value="MAX">MAX</option>
                        </select>
                      ) : (
                        <span className="font-mono text-slate-600 font-medium">
                          {c.aggregation_method}
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3">
                      {isConfirmed ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full text-[10px] font-medium border border-emerald-200">
                          <CheckCircle className="w-3 h-3" /> Confirmed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full text-[10px] font-medium border border-teal-200">
                          <Sparkles className="w-3 h-3 text-[#009F98]" /> AI Suggested
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleSave(c.column_name)}
                            disabled={isSaving}
                            className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                            title="Save changes"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingCol(null)}
                            className="p-1 text-slate-400 hover:bg-slate-100 rounded"
                            title="Cancel"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1.5">
                          {!isConfirmed && (
                            <button
                              onClick={() => handleQuickConfirm(c)}
                              className="px-2 py-1 bg-[#009F98]/10 hover:bg-[#009F98]/20 text-[#009F98] rounded text-[11px] font-medium flex items-center gap-1 transition-colors"
                              title="Confirm AI Mapping"
                            >
                              <Check className="w-3 h-3" /> Confirm
                            </button>
                          )}
                          <button
                            onClick={() => startEdit(c)}
                            className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors"
                            title="Edit Semantic Definition"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

