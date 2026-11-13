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
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  if (!filters || (filters.length === 0 && !isEditMode)) {
    return null;
  }

  const activeCount = Object.keys(activeValues).filter(
    (k) => activeValues[k] !== undefined && activeValues[k] !== '' && activeValues[k] !== null
  ).length;

  return (
    <div className="bg-white rounded-xl border border-[#DCE5EB] p-3 shadow-2xs mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left side: Filter Label & Active Items */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#102C46] pr-2 border-r border-[#DCE5EB]">
            <FilterIcon className="w-3.5 h-3.5 text-[#009F98]" />
            <span>Filters</span>
            {activeCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-[#009F98] text-white text-[10px] flex items-center justify-center font-bold">
                {activeCount}
              </span>
            )}
          </div>

          {filters.map((f) => {
            const currentVal = activeValues[f.column_name];
            const hasVal = currentVal !== undefined && currentVal !== '' && currentVal !== null;

            return (
              <div key={f.id} className="relative inline-flex items-center">
                {/* 1. Date Range Filter */}
                {f.filter_type === 'date_range' && (
                  <div className="flex items-center gap-1 bg-[#F5F8FA] border border-[#DCE5EB] rounded-lg px-2.5 py-1 text-xs">
                    <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                    <span className="text-[#52616C] font-medium">{f.name}:</span>
                    <select
                      value={currentVal || 'all'}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === 'all') {
                          onFilterChange(f.column_name, 'gte', null);
                        } else {
                          onFilterChange(f.column_name, 'gte', val);
                        }
                      }}
                      className="bg-transparent text-[#102C46] font-semibold focus:outline-none cursor-pointer"
                    >
                      <option value="all">All Dates</option>
                      <option value="2025-01-01">2025 Onward</option>
                      <option value="2024-01-01">2024 Onward</option>
                      <option value="2023-01-01">2023 Onward</option>
                    </select>
                  </div>
                )}

                {/* 2. Dropdown Filter */}
                {f.filter_type === 'dropdown' && (
                  <div className="flex items-center gap-1 bg-[#F5F8FA] border border-[#DCE5EB] rounded-lg px-2.5 py-1 text-xs">
                    <span className="text-[#52616C] font-medium">{f.name}:</span>
                    <select
                      value={currentVal || ''}
                      onChange={(e) => {
                        const v = e.target.value;
                        onFilterChange(f.column_name, f.default_operator || 'eq', v || null);
                      }}
                      className="bg-transparent text-[#102C46] font-semibold focus:outline-none cursor-pointer max-w-[130px] truncate"
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

                {/* 3. Text Search Filter */}
                {f.filter_type === 'text' && (
                  <div className="flex items-center gap-1 bg-[#F5F8FA] border border-[#DCE5EB] rounded-lg px-2.5 py-1 text-xs">
                    <Search className="w-3.5 h-3.5 text-[#52616C]" />
                    <input
                      type="text"
                      placeholder={`Search ${f.name}...`}
                      value={currentVal || ''}
                      onChange={(e) =>
                        onFilterChange(f.column_name, 'contains', e.target.value || null)
                      }
                      className="bg-transparent text-[#102C46] font-medium focus:outline-none w-28 placeholder-[#52616C]/60"
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

                {/* 4. Numeric Range Filter */}
                {f.filter_type === 'numeric_range' && (
                  <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] rounded-lg px-2.5 py-1 text-xs">
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

                {/* Edit Mode Remove Filter Badge */}
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
          })}

          {/* Clear All Action */}
          {activeCount > 0 && (
            <button
              type="button"
              onClick={onClearFilters}
              className="text-xs text-[#009F98] hover:text-[#007D78] font-bold transition-colors cursor-pointer pl-1"
            >
              Reset all
            </button>
          )}
        </div>

        {/* Right side: Add Filter Button (Edit mode) */}
        {isEditMode && onAddFilter && (
          <button
            type="button"
            onClick={onAddFilter}
            className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#EDF7FA] text-[#007D78] hover:bg-[#DDF0F5] border border-[#BBDCE8] rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Filter
          </button>
        )}
      </div>
    </div>
  );
};

