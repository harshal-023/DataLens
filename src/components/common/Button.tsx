import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'teal-soft' | 'gold-soft';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer select-none';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-xs sm:text-sm px-4 py-2 gap-2',
    lg: 'text-sm sm:text-base px-5 py-2.5 gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-[#009F98] hover:bg-[#007D78] active:bg-[#086E73] text-white shadow-[0_2px_10px_rgba(0,159,152,0.3)] focus:ring-[#009F98]',
    'teal-soft':
      'bg-[#EDF7FA] hover:bg-[#DDF0F5] text-[#007D78] border border-[#BBDCE8] focus:ring-[#39C3B8]',
    'gold-soft':
      'bg-[#EDF7FA] hover:bg-[#DDF0F5] text-[#007D78] border border-[#BBDCE8] focus:ring-[#39C3B8]', // backward compatibility
    secondary:
      'bg-white hover:bg-[#EEF3F6] text-[#102C46] border border-[#DCE5EB] shadow-2xs focus:ring-[#102C46]',
    outline:
      'bg-white hover:bg-[#F5F8FA] text-[#102C46] border border-[#DCE5EB] shadow-2xs focus:ring-[#009F98]',
    ghost:
      'bg-transparent hover:bg-[#EEF3F6] text-[#52616C] hover:text-[#102C46] focus:ring-[#009F98]',
    danger:
      'bg-[#FCE9E9] hover:bg-[#F9D6D6] text-[#A63838] border border-[#F7C9C5] focus:ring-red-400',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : (
        leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
    </button>
  );
};
