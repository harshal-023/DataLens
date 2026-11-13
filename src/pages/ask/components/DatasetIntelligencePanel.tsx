import React, { useState } from 'react';
import {
  Database,
  ChevronDown,
  CheckCircle2,
  Calendar,
  Layers,
  FileSpreadsheet,
  ChevronRight,
  TrendingUp,
  Hash,
  Type,
  Coins,
} from 'lucide-react';
import { Dataset } from '../../../types';

interface DatasetIntelligencePanelProps {
  datasets: Dataset[];
  selectedDataset?: Dataset;
  onSelectDataset: (dataset: Dataset) => void;
  onSelectQuestion: (question: string) => void;
  suggestedQuestions: string[];
}

export const DatasetIntelligencePanel: React.FC<DatasetIntelligencePanelProps> = ({
  datasets,
  selectedDataset,
  onSelectDataset,
  onSelectQuestion,
  suggestedQuestions,
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const getColumnIcon = (type: string) => {
    switch (type) {
      case 'number':
        return <Hash className="w-3 h-3 text-[#009F98]" />;
      case 'currency':
        return <Coins className="w-3 h-3 text-[#009F98]" />;
      case 'date':
        return <Calendar className="w-3 h-3 text-[#39C3B8]" />;
      default:
        return <Type className="w-3 h-3 text-[#52616C]" />;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle h-full flex flex-col justify-between select-none">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2 pb-3 border-b border-[#EEF3F6]">
          <Database className="w-4 h-4 text-[#009F98]" />
          <h3 className="text-sm font-bold text-[#102C46]">Dataset Intelligence</h3>
        </div>

        {/* Dataset Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between p-2.5 rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] hover:bg-white hover:border-[#009F98] transition-all cursor-pointer text-left shadow-2xs"
          >
            <div className="flex items-center gap-2 min-w-0">
              <FileSpreadsheet className="w-4 h-4 text-[#009F98] shrink-0" />
              <div className="min-w-0">
                <span className="text-xs font-bold text-[#102C46] truncate block">
                  {selectedDataset ? selectedDataset.name : 'Select a dataset'}
                </span>
                {selectedDataset && (
                  <span className="text-[10px] text-[#52616C] block">
                    {selectedDataset.rowCount.toLocaleString()} rows · {selectedDataset.columnCount} columns
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0 ml-1">
              {selectedDataset && (
                <span className="text-[10px] font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-[#216548]" />
                  Verified
                </span>
              )}
              <ChevronDown className="w-3.5 h-3.5 text-[#52616C]" />
            </div>
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute left-0 right-0 top-12 bg-white rounded-xl shadow-elevated border border-[#DCE5EB] py-1.5 z-40 space-y-1">
              {datasets.map((d) => (
                <button
                  key={d.id}
                  onClick={() => {
                    onSelectDataset(d);
                    setIsDropdownOpen(false);
                  }}
                  className={`w-full px-3 py-2 flex items-center justify-between text-left text-xs transition-colors cursor-pointer ${
                    selectedDataset?.id === d.id ? 'bg-[#EDF7FA] font-bold text-[#009F98]' : 'hover:bg-[#F5F8FA] text-[#102C46]'
                  }`}
                >
                  <div className="truncate">
                    <p className="font-semibold">{d.name}</p>
                    <p className="text-[10px] text-[#52616C]">
                      {d.rowCount.toLocaleString()} rows · {d.columnCount} columns
                    </p>
                  </div>
                  {selectedDataset?.id === d.id && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#009F98]" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected Dataset Details or Empty State */}
        {!selectedDataset ? (
          /* Empty State matching reference image */
          <div className="py-12 px-2 text-center flex flex-col items-center justify-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#009F98] shadow-2xs mb-1">
              <Database className="w-6 h-6 text-[#009F98]" />
            </div>
            <h4 className="text-xs font-bold text-[#102C46]">No dataset selected</h4>
            <p className="text-[11px] text-[#52616C] max-w-[200px] leading-relaxed">
              Choose a dataset to view its summary, key columns, and suggested questions.
            </p>
            <button
              onClick={() => setIsDropdownOpen(true)}
              className="mt-2 px-3 py-1.5 rounded-full bg-[#009F98] text-white text-xs font-semibold hover:bg-[#007D78] transition-colors cursor-pointer shadow-2xs"
            >
              Select Dataset
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Dataset Overview */}
            <div className="space-y-2">
              <h4 className="text-[11px] font-bold text-[#52616C] uppercase tracking-wider">
                Dataset Overview
              </h4>

              <div className="bg-[#F5F8FA] rounded-xl p-3 border border-[#DCE5EB] space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#52616C] flex items-center gap-1.5 text-[11px]">
                    <TrendingUp className="w-3.5 h-3.5 text-[#009F98]" />
                    {selectedDataset.id === 'ds-sales-2025' ? 'Total Revenue' : 'Primary Metric'}
                  </span>
                  <span className="font-bold text-[#102C46]">
                    {selectedDataset.id === 'ds-sales-2025' ? '₹ 3.42M' : selectedDataset.id === 'ds-ops-2025' ? '95.2% SLA' : '₹ 4.10M ARR'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#52616C] flex items-center gap-1.5 text-[11px]">
                    <Layers className="w-3.5 h-3.5 text-[#52616C]" />
                    Total Records
                  </span>
                  <span className="font-bold text-[#102C46]">
                    {selectedDataset.rowCount.toLocaleString()}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#52616C] flex items-center gap-1.5 text-[11px]">
                    <Hash className="w-3.5 h-3.5 text-[#52616C]" />
                    Total Columns
                  </span>
                  <span className="font-bold text-[#102C46]">{selectedDataset.columnCount}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#52616C] flex items-center gap-1.5 text-[11px]">
                    <Calendar className="w-3.5 h-3.5 text-[#52616C]" />
                    Period
                  </span>
                  <span className="font-bold text-[#102C46]">May - Oct 2025</span>
                </div>
              </div>
            </div>

            {/* Key Columns */}
            <div className="space-y-2">
              <h4 className="text-[11px] font-bold text-[#52616C] uppercase tracking-wider">
                Key Columns
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {(selectedDataset.columns || []).slice(0, 6).map((col) => (
                  <span
                    key={col.id}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#EDF7FA] border border-[#BBDCE8] text-[11px] font-medium text-[#102C46]"
                  >
                    {getColumnIcon(col.type)}
                    <span>{col.name}</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Suggested Questions */}
            <div className="space-y-2 pt-1">
              <h4 className="text-[11px] font-bold text-[#52616C] uppercase tracking-wider">
                Suggested Questions
              </h4>
              <div className="space-y-1.5">
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectQuestion(q)}
                    className="w-full p-2.5 rounded-xl border border-[#DCE5EB] bg-white hover:border-[#009F98] hover:bg-[#F5F8FA] text-left text-xs text-[#102C46] flex items-center justify-between group transition-all cursor-pointer shadow-2xs"
                  >
                    <span className="truncate pr-1 group-hover:text-[#009F98] transition-colors">
                      {q}
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 text-[#52616C] group-hover:text-[#009F98] group-hover:translate-x-0.5 transition-all shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

