import React from 'react';

interface DataLensLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showSubtitle?: boolean;
  centered?: boolean;
  theme?: 'dark' | 'light'; // dark = on deep navy background (white text); light = on white/light background (navy text)
  className?: string;
}

export const DataLensLogo: React.FC<DataLensLogoProps> = ({
  size = 'md',
  showSubtitle = true,
  centered = false,
  theme = 'dark',
  className = '',
}) => {
  const iconSizes = {
    sm: { b1: 'h-2.5 w-1.5', b2: 'h-3.5 w-1.5', b3: 'h-4.5 w-1.5', gap: 'gap-0.5' },
    md: { b1: 'h-3.5 w-1.5', b2: 'h-5 w-1.5', b3: 'h-7 w-1.5', gap: 'gap-1' },
    lg: { b1: 'h-4.5 w-2', b2: 'h-6.5 w-2', b3: 'h-9 w-2', gap: 'gap-1.5' },
    xl: { b1: 'h-5.5 w-2.5', b2: 'h-8 w-2.5', b3: 'h-11 w-2.5', gap: 'gap-2' },
  };

  const textSizes = {
    sm: 'text-sm',
    md: 'text-lg',
    lg: 'text-xl',
    xl: 'text-2xl',
  };

  const current = iconSizes[size];
  const isDark = theme === 'dark';

  return (
    <div className={`flex items-center gap-2.5 ${centered ? 'justify-center flex-col text-center' : ''} ${className}`}>
      {/* 3 ascending vertical pill bars with signature Peacock Teal gradient */}
      <div className={`flex items-end ${current.gap} shrink-0`}>
        <div className={`${current.b1} bg-gradient-to-t from-[#007D78] to-[#009F98] rounded-full`} />
        <div className={`${current.b2} bg-gradient-to-t from-[#009F98] to-[#39C3B8] rounded-full`} />
        <div className={`${current.b3} bg-gradient-to-t from-[#39C3B8] to-[#8BE5DE] rounded-full`} />
      </div>

      <div className={centered ? 'flex flex-col items-center' : 'flex flex-col'}>
        <span
          className={`font-bold tracking-tight font-sans leading-none ${
            isDark ? 'text-white' : 'text-[#102C46]'
          } ${textSizes[size]}`}
        >
          DataLens
        </span>
        {showSubtitle && (
          <span
            className={`text-[8px] font-semibold tracking-wide uppercase mt-1 leading-none ${
              isDark ? 'text-[#BBDCE8]' : 'text-[#52616C]'
            }`}
          >
            Business Intelligence & Report Generator
          </span>
        )}
      </div>
    </div>
  );
};
