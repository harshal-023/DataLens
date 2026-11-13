import React, { useState } from 'react';
import { Filter, Save, X } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { DashboardFilter } from '../../services/dashboardService';

export interface FilterConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (filterData: Partial<DashboardFilter>) => Promise<void>;
  initialFilter?: DashboardFilter | null;
}

export const FilterConfigModal: React.FC<FilterConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialFilter,
}) => {
  const [name, setName] = useState<string>(initialFilter?.name || '');
  const [columnName, setColumnName] = useState<string>(initialFilter?.column_name || '');
  const [filterType, setFilterType] = useState<string>(initialFilter?.filter_type || 'dropdown');
  const [optionsStr, setOptionsStr] = useState<string>(
    initialFilter?.config?.options
      ? initialFilter.config.options.map((o: any) => o.value).join(', ')
      : ''
  );
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !columnName.trim()) {
      setError('Please provide both filter name and dataset column name.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const parsedOptions = optionsStr
        ? optionsStr
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
            .map((s) => ({ label: s, value: s }))
        : [];

      await onSave({
        name: name.trim(),
        column_name: columnName.trim(),
        filter_type: filterType as any,
        default_operator: filterType === 'numeric_range' ? 'gte' : filterType === 'text' ? 'contains' : 'eq',
        config: {
          options: parsedOptions,
        },
      });

      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to save filter.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialFilter ? 'Configure Filter' : 'Add Dashboard Filter'}
      subtitle="Interactive filters synchronize across all compatible widgets connected to the column."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {error && (
          <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838]">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-bold text-[#102C46] mb-1">
            Filter Label <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Sales Region, Order Date"
            className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-[#102C46] mb-1">
            Target Column Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={columnName}
            onChange={(e) => setColumnName(e.target.value)}
            placeholder="e.g. region, order_date, category"
            className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] font-mono focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
          />
          <span className="text-[10px] text-[#52616C] mt-0.5 block">
            Exact column name in your dataset schema.
          </span>
        </div>

        <div>
          <label className="block text-xs font-bold text-[#102C46] mb-1">Filter Control Type</label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-medium focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
          >
            <option value="dropdown">Dropdown Selection (Single)</option>
            <option value="date_range">Date Range Picker</option>
            <option value="numeric_range">Numeric Threshold / Range (&gt;=)</option>
            <option value="text">Text Search Filter</option>
          </select>
        </div>

        {filterType === 'dropdown' && (
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Dropdown Options (comma separated)
            </label>
            <input
              type="text"
              value={optionsStr}
              onChange={(e) => setOptionsStr(e.target.value)}
              placeholder="e.g. North, South, East, West"
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none"
            />
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#DCE5EB]">
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={saving}
            leftIcon={<Save className="w-4 h-4" />}
          >
            Save Filter
          </Button>
        </div>
      </form>
    </Modal>
  );
};

