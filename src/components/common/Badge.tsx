import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'verified' | 'teal' | 'gold' | 'warning' | 'danger' | 'neutral' | 'info' | 'ice';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  icon,
  className = '',
}) => {
  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  const variantStyles = {
    verified: 'bg-[#E4F3EC] text-[#216548] border border-[#C3E7D5] font-semibold',
    teal: 'bg-[#EDF7FA] text-[#007D78] border border-[#BBDCE8] font-semibold',
    gold: 'bg-[#EDF7FA] text-[#007D78] border border-[#BBDCE8] font-semibold', // mapped to teal
    warning: 'bg-[#FFF3DF] text-[#98620D] border border-[#F9DFAC] font-semibold',
    danger: 'bg-[#FCE9E9] text-[#A63838] border border-[#F7C9C5] font-semibold',
    neutral: 'bg-[#EEF2F5] text-[#52616C] border border-[#DCE5EB] font-medium',
    info: 'bg-[#E6F2F8] text-[#285C78] border border-[#C8E0EE] font-medium',
    ice: 'bg-[#EDF7FA] text-[#356B83] border border-[#BBDCE8] font-medium',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full tracking-wide ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {icon && <span className="inline-flex shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
