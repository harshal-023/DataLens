import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hoverable = false,
  ...props
}) => {
  return (
    <div
      className={`bg-white rounded-2xl border border-[#DCE5EB] shadow-subtle ${
        hoverable ? 'hover:shadow-elevated hover:border-[#009F98]/50 transition-all duration-200' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  intensity?: 'subtle' | 'medium' | 'high';
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className = '',
  intensity = 'medium',
  ...props
}) => {
  const intensityMap = {
    subtle: 'bg-white/75 backdrop-blur-sm border-[#DCE5EB]',
    medium: 'bg-white/90 backdrop-blur-md border-[#DCE5EB] shadow-subtle',
    high: 'bg-white/95 backdrop-blur-lg border-[#DCE5EB] shadow-elevated',
  };

  return (
    <div
      className={`rounded-2xl border ${intensityMap[intensity]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
