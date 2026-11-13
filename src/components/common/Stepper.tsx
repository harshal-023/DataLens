import React from 'react';
import { Check } from 'lucide-react';

export interface StepItem {
  id: number;
  label: string;
  description?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number;
  onStepClick?: (stepId: number) => void;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  onStepClick,
  className = '',
}) => {
  return (
    <div className={`w-full py-3 ${className}`}>
      <div className="flex items-center justify-between relative">
        {/* Connecting line */}
        <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-[2px] bg-[#DCE5EB] -z-0" />
        <div
          className="absolute left-6 top-1/2 -translate-y-1/2 h-[2px] bg-[#009F98] transition-all duration-300 -z-0"
          style={{
            width: `${Math.min(100, Math.max(0, ((currentStep - 1) / (steps.length - 1)) * 100))}%`,
          }}
        />

        {steps.map((step) => {
          const isCompleted = step.id < currentStep;
          const isCurrent = step.id === currentStep;

          return (
            <div
              key={step.id}
              onClick={() => onStepClick && isCompleted && onStepClick(step.id)}
              className={`flex flex-col items-center relative z-10 ${
                onStepClick && isCompleted ? 'cursor-pointer group' : ''
              }`}
            >
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-200 border-2 ${
                  isCompleted
                    ? 'bg-[#102C46] border-[#102C46] text-white shadow-2xs'
                    : isCurrent
                    ? 'bg-white border-[#009F98] text-[#009F98] ring-4 ring-[#DDF0F5] shadow-2xs'
                    : 'bg-white border-[#DCE5EB] text-[#52616C]'
                }`}
              >
                {isCompleted ? <Check className="w-4 h-4 stroke-[2.5]" /> : step.id}
              </div>
              <span
                className={`mt-2 text-xs font-medium ${
                  isCurrent ? 'text-[#102C46] font-semibold' : isCompleted ? 'text-[#102C46]' : 'text-[#52616C]'
                }`}
              >
                {step.label}
              </span>
              {step.description && (
                <span className="text-[10px] text-[#52616C] mt-0.5 hidden sm:block">
                  {step.description}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
