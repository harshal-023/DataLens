import React from 'react';
import { ArrowRight, Paperclip, Database } from 'lucide-react';
import { Dataset } from '../../../types';

interface ChatComposerProps {
  value: string;
  onChange: (val: string) => void;
  onSend: (text?: string) => void;
  isProcessing: boolean;
  selectedDataset?: Dataset;
  hasActiveMessages: boolean;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  value,
  onChange,
  onSend,
  isProcessing,
  selectedDataset,
  hasActiveMessages,
}) => {
  const isSendDisabled = !value.trim() || isProcessing || !selectedDataset;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isSendDisabled) {
      e.preventDefault();
      onSend();
    }
  };

  const placeholderText = !selectedDataset
    ? 'Select a dataset on the right to start asking questions...'
    : hasActiveMessages
    ? "Ask a follow-up question (e.g. 'Show the monthly trend for Premium Pro')..."
    : 'Ask a question about your data...';

  return (
    <div className="relative pt-2">
      <div className="relative flex items-center bg-white rounded-full border border-[#DCE5EB] focus-within:border-[#009F98] focus-within:ring-2 focus-within:ring-[#009F98]/20 shadow-2xs transition-all">
        {/* Attachment / Context Indicator */}
        <div className="pl-4 pr-1 text-[#52616C] flex items-center gap-1.5 shrink-0">
          {selectedDataset ? (
            <span
              className="inline-flex items-center gap-1 text-[11px] font-medium text-[#009F98] bg-[#E0F5F3] px-2 py-0.5 rounded-full"
              title={`Context: ${selectedDataset.name}`}
            >
              <Database className="w-3 h-3 text-[#009F98]" />
              <span className="hidden sm:inline truncate max-w-[100px]">
                {selectedDataset.name}
              </span>
            </span>
          ) : (
            <Paperclip className="w-4 h-4 text-[#52616C]" />
          )}
        </div>

        {/* Input Text Box */}
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
          placeholder={placeholderText}
          className="w-full px-3 py-3 text-xs text-[#102C46] placeholder:text-[#52616C] bg-transparent focus:outline-none"
        />

        {/* Send Button */}
        <div className="pr-1.5 shrink-0">
          <button
            onClick={() => onSend()}
            disabled={isSendDisabled}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
              isSendDisabled
                ? 'bg-[#DCE5EB] text-[#52616C] cursor-not-allowed opacity-60'
                : 'bg-[#009F98] hover:bg-[#007D78] text-white shadow-2xs cursor-pointer'
            }`}
            title={
              !selectedDataset
                ? 'Select a dataset first'
                : !value.trim()
                ? 'Type a question'
                : 'Send message'
            }
          >
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {!selectedDataset && (
        <p className="text-[11px] text-[#98620D] text-center mt-1.5 font-medium">
          ⚠️ Please select a dataset from the Dataset Intelligence panel on the right to begin.
        </p>
      )}
    </div>
  );
};

