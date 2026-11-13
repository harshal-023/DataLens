import React from 'react';

export const LoadingSkeleton: React.FC<{ className?: string }> = ({ className = 'h-4 w-full' }) => {
  return (
    <div className={`animate-pulse bg-[#EEF3F6] rounded-lg ${className}`} />
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 space-y-3">
      <div className="flex justify-between items-center">
        <LoadingSkeleton className="h-5 w-1/3" />
        <LoadingSkeleton className="h-4 w-12 rounded-full" />
      </div>
      <LoadingSkeleton className="h-8 w-2/5" />
      <LoadingSkeleton className="h-3 w-4/5" />
    </div>
  );
};
