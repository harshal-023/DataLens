import React, { useState } from 'react';
import {
  Filter as FilterIcon,
  X,
  Plus,
  Calendar,
  ChevronDown,
  Search,
  SlidersHorizontal,
  Check,
} from 'lucide-react';
import { DashboardFilter } from '../../services/dashboardService';

export interface DashboardFilterBarProps {
  filters: DashboardFilter[];
  activeValues: Record<string, any>;
  onFilterChange: (column: string, operator: string, value: any) => void;
  onClearFilters: () => void;
  onAddFilter?: () => void;
  onDeleteFilter?: (filterId: string) => void;
  isEditMode?: boolean;
}

export const DashboardFilterBar: React.FC<DashboardFilterBarProps> = ({
  filters,
  activeValues,
  onFilterChange,
  onClearFilters,
  onAddFilter,
  onDeleteFilter,
  isEditMode = false,
}) => {
  const activeCount = Object.keys(activeValues).filter(
    (k) => activeValues[k] !== undefined && activeValues[k] !== '' && activeValues[k] !== null
  ).length;

  // Standard defaults when no custom filters have been created yet
  const hasCustomFilters = filters && filters.length > 0;

  return (
    <div className="bg-white rounded-2xl border border-[#DCE5EB] p-3 shadow-2xs mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left side: Filter Label & Active Items */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#102C46] pr-2 border-r border-[#DCE5EB]">
            <span>Filters:</span>
            {activeCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-[#009F98] text-white text-[10px] flex items-center justify-center font-bold">
                {activeCount}
              </span>
            )}
          </div>

          {hasCustomFilters ? (
            // Render custom user-created filters
            filters.map((f) => {
              const currentVal = activeValues[f.column_name];
              const hasVal = currentVal !== undefined && currentVal !== '' && currentVal !== null;

              return (
                <div key={f.id} className="relative inline-flex items-center">
                  {f.filter_type === 'date_range' && (
                    <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                      <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                      <span className="text-[#52616C] font-medium">{f.name}:</span>
                      <select
                        value={currentVal || 'all'}
                        onChange={(e) => {
                          const val = e.target.value;
                          onFilterChange(f.column_name, 'gte', val === 'all' ? null : val);
                        }}
                        className="bg-transparent text-[#102C46] font-bold focus:outline-none cursor-pointer"
                      >
                        <option value="all">Last 12 Months</option>
                        <option value="last_30_days">Last 30 Days</option>
                        <option value="last_quarter">Last Quarter</option>
                        <option value="ytd">Year to Date</option>
                      </select>
                    </div>
                  )}

                  {f.filter_type === 'dropdown' && (
                    <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                      <span className="text-[#52616C] font-medium">{f.name}:</span>
                      <select
                        value={currentVal || ''}
                        onChange={(e) => {
                          const v = e.target.value;
                          onFilterChange(f.column_name, f.default_operator || 'eq', v || null);
                        }}
                        className="bg-transparent text-[#102C46] font-bold focus:outline-none cursor-pointer max-w-[130px] truncate"
                      >
                        <option value="">All</option>
                        {(f.config?.options || [
                          { label: 'Option A', value: 'Option A' },
                          { label: 'Option B', value: 'Option B' },
                        ]).map((opt: any) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {f.filter_type === 'text' && (
                    <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                      <Search className="w-3.5 h-3.5 text-[#52616C]" />
                      <input
                        type="text"
                        placeholder={`Search ${f.name}...`}
                        value={currentVal || ''}
                        onChange={(e) =>
                          onFilterChange(f.column_name, 'contains', e.target.value || null)
                        }
                        className="bg-transparent text-[#102C46] font-semibold focus:outline-none w-28 placeholder-[#52616C]/60"
                      />
                      {hasVal && (
                        <button
                          type="button"
                          onClick={() => onFilterChange(f.column_name, 'contains', null)}
                          className="text-[#52616C] hover:text-[#102C46]"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}

                  {f.filter_type === 'numeric_range' && (
                    <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                      <SlidersHorizontal className="w-3.5 h-3.5 text-[#009F98]" />
                      <span className="text-[#52616C] font-medium">{f.name} &gt;=</span>
                      <input
                        type="number"
                        placeholder="Min"
                        value={currentVal || ''}
                        onChange={(e) =>
                          onFilterChange(f.column_name, 'gte', e.target.value ? Number(e.target.value) : null)
                        }
                        className="bg-transparent text-[#102C46] font-semibold w-16 focus:outline-none"
                      />
                    </div>
                  )}

                  {isEditMode && onDeleteFilter && (
                    <button
                      type="button"
                      onClick={() => onDeleteFilter(f.id)}
                      className="ml-1 text-[#52616C] hover:text-[#A63838] transition-colors p-0.5"
                      title={`Delete '${f.name}' filter`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })
          ) : (
            // Default PowerBI style filters matching reference image
            <>
              {/* Date Range Selector */}
              <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                <span className="text-[#52616C] font-medium">Date Range:</span>
                <select
                  value={activeValues['date_range']?.value || 'last_12_months'}
                  onChange={(e) =>
                    onFilterChange(
                      'date_range',
                      'eq',
                      e.target.value === 'all' ? null : e.target.value
                    )
                  }
                  className="bg-transparent text-[#102C46] font-bold focus:outline-none cursor-pointer"
                >
                  <option value="last_12_months">Last 12 Months</option>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="this_quarter">This Quarter</option>
                  <option value="all">All Dates</option>
                </select>
              </div>

              {/* Region Selector */}
              <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                <span className="text-[#52616C] font-medium">Region:</span>
                <select
                  value={activeValues['region']?.value || ''}
                  onChange={(e) =>
                    onFilterChange('region', 'eq', e.target.value || null)
                  }
                  className="bg-transparent text-[#102C46] font-bold focus:outline-none cursor-pointer"
                >
                  <option value="">All</option>
                  <option value="West">West</option>
                  <option value="North">North</option>
                  <option value="South">South</option>
                  <option value="East">East</option>
                </select>
              </div>

              {/* Product Selector */}
              <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-xl px-3 py-1.5 text-xs">
                <span className="text-[#52616C] font-medium">Product:</span>
                <select
                  value={activeValues['product']?.value || ''}
                  onChange={(e) =>
                    onFilterChange('product', 'eq', e.target.value || null)
                  }
                  className="bg-transparent text-[#102C46] font-bold focus:outline-none cursor-pointer"
                >
                  <option value="">All</option>
                  <option value="Enterprise">Enterprise</option>
                  <option value="Professional">Professional</option>
                  <option value="Standard">Standard</option>
                </select>
              </div>
            </>
          )}

          {/* Add Filter in Edit Mode */}
          {isEditMode && onAddFilter && (
            <button
              type="button"
              onClick={onAddFilter}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-[#EDF7FA] text-[#007D78] hover:bg-[#DDF0F5] border border-[#BBDCE8] rounded-xl text-xs font-bold transition-all cursor-pointer shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Filter
            </button>
          )}
        </div>

        {/* Right side: Clear All Action */}
        <div>
          <button
            type="button"
            onClick={onClearFilters}
            className="text-xs text-[#52616C] hover:text-[#102C46] font-bold transition-colors cursor-pointer"
          >
            Clear All
          </button>
        </div>
      </div>
    </div>
  );
};
