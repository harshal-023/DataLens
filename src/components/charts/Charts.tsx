import React, { useState } from 'react';

// Custom lightweight responsive SVG charts strictly adhering to Deep Navy & Peacock Teal identity

export interface BarChartProps {
  title?: string;
  labels: string[];
  values: number[];
  unit?: string;
  height?: number;
  barColor?: string;
}

export const BarChart: React.FC<BarChartProps> = ({
  title,
  labels,
  values,
  unit = '',
  height = 200,
  barColor = '#009F98',
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const maxValue = Math.max(...values, 0);

  return (
    <div className="w-full">
      {title && <h4 className="text-xs font-bold text-[#102C46] mb-3 uppercase tracking-wider">{title}</h4>}
      <div className="relative" style={{ height: `${height}px` }}>
        {/* Subtle grid lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-40">
          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
          <div className="border-b border-[#DCE5EB] w-full" />
        </div>

        {/* Bars Container */}
        <div className="relative h-full flex items-end justify-around gap-2 pt-6 pb-6">
          {labels.map((label, index) => {
            const val = values[index];
            const isNegative = val < 0;
            const barHeightPct = Math.max(8, (Math.abs(val) / (maxValue || 1)) * 75);

            return (
              <div
                key={label}
                className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {/* Tooltip */}
                {hoveredIndex === index && (
                  <div className="absolute -top-7 bg-[#102C46] text-white text-[11px] px-2 py-1 rounded-lg shadow-elevated whitespace-nowrap z-30 pointer-events-none animate-in fade-in duration-150">
                    <span className="font-semibold">{label}: </span>
                    <span>
                      {val > 0 ? '+' : ''}
                      {val} {unit}
                    </span>
                  </div>
                )}

                {/* Bar */}
                <div
                  className={`w-full max-w-[42px] rounded-t-lg transition-all duration-200 ${
                    hoveredIndex === index ? 'opacity-100 ring-2 ring-[#009F98]/40' : 'opacity-90'
                  }`}
                  style={{
                    height: `${barHeightPct}%`,
                    backgroundColor: isNegative ? '#A63838' : barColor,
                  }}
                />

                {/* X-axis label */}
                <span className="text-[11px] text-[#52616C] mt-2 truncate w-full text-center font-medium">
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export interface MultiBarComparisonProps {
  categories: string[];
  series: {
    name: string;
    color: string;
    values: number[];
  }[];
  height?: number;
  unit?: string;
}

export const MultiBarComparison: React.FC<MultiBarComparisonProps> = ({
  categories,
  series,
  height = 240,
  unit = '',
}) => {
  const [hoveredCell, setHoveredCell] = useState<{ catIdx: number; seriesIdx: number } | null>(null);

  // Find max value across all series
  const allValues = series.flatMap((s) => s.values);
  const maxVal = Math.max(...allValues, 100);

  return (
    <div className="w-full">
      {/* Legend matching reference: Baseline (ice), Structured (teal-300), Few-Shot (teal) */}
      <div className="flex flex-wrap items-center justify-center gap-5 mb-4 text-xs">
        {series.map((s) => (
          <div key={s.name} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: s.color }} />
            <span className="font-medium text-[#102C46]">{s.name}</span>
          </div>
        ))}
      </div>

      <div className="relative" style={{ height: `${height}px` }}>
        {/* Grid lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-40 pb-7">
          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
          <div className="border-b border-[#DCE5EB] w-full" />
        </div>

        {/* Grouped Bars */}
        <div className="relative h-full flex items-end justify-around gap-4 pt-6 pb-7">
          {categories.map((cat, catIdx) => (
            <div key={cat} className="flex-1 flex flex-col items-center h-full justify-end">
              <div className="flex items-end justify-center gap-1.5 w-full h-full pb-2">
                {series.map((s, seriesIdx) => {
                  const val = s.values[catIdx] ?? 0;
                  const barHeightPct = Math.max(6, (val / maxVal) * 80);
                  const isHovered =
                    hoveredCell?.catIdx === catIdx && hoveredCell?.seriesIdx === seriesIdx;

                  return (
                    <div
                      key={s.name}
                      className="flex-1 max-w-[28px] h-full flex items-end relative group cursor-pointer"
                      onMouseEnter={() => setHoveredCell({ catIdx, seriesIdx })}
                      onMouseLeave={() => setHoveredCell(null)}
                    >
                      {/* Tooltip */}
                      {isHovered && (
                        <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[#102C46] text-white text-[11px] px-2 py-0.5 rounded shadow-elevated whitespace-nowrap z-30 pointer-events-none">
                          <span className="font-medium">{s.name}: </span>
                          <span className="font-bold">
                            {val}
                            {unit}
                          </span>
                        </div>
                      )}
                      <div
                        className={`w-full rounded-t-md transition-all duration-150 ${
                          isHovered ? 'brightness-110 ring-2 ring-[#009F98]' : ''
                        }`}
                        style={{
                          height: `${barHeightPct}%`,
                          backgroundColor: s.color,
                        }}
                      />
                    </div>
                  );
                })}
              </div>
              <span className="text-[11px] text-[#52616C] truncate w-full text-center font-medium">
                {cat}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export interface DonutChartProps {
  title?: string;
  labels: string[];
  values: number[];
  colors?: string[];
  size?: number;
  centerLabel?: string;
  centerValue?: string;
}

export const DonutChart: React.FC<DonutChartProps> = ({
  title,
  labels,
  values,
  colors = ['#102C46', '#009F98', '#39C3B8', '#1D4664'],
  size = 160,
  centerLabel,
  centerValue,
}) => {
  const total = values.reduce((a, b) => a + b, 0) || 1;
  let accumulatedPct = 0;

  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      {/* SVG Donut */}
      <div
        className="relative flex items-center justify-center shrink-0"
        style={{ width: size, height: size }}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="rotate-[-90deg]"
        >
          {values.map((val, idx) => {
            const pct = val / total;
            const strokeDasharray = `${pct * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedPct * circumference;
            accumulatedPct += pct;
            const color = colors[idx % colors.length];

            return (
              <circle
                key={labels[idx]}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-300 hover:opacity-90"
              />
            );
          })}
        </svg>

        {/* Center Text */}
        {(centerLabel || centerValue) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
            {centerValue && (
              <span className="text-base font-bold text-[#102C46] leading-tight">
                {centerValue}
              </span>
            )}
            {centerLabel && (
              <span className="text-[10px] text-[#52616C] uppercase font-semibold tracking-wider mt-0.5">
                {centerLabel}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-2 w-full">
        {title && (
          <h5 className="text-xs font-bold text-[#102C46] uppercase tracking-wider mb-1">
            {title}
          </h5>
        )}
        {labels.map((label, idx) => {
          const val = values[idx];
          const pct = Math.round((val / total) * 100);
          return (
            <div key={label} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: colors[idx % colors.length] }}
                />
                <span className="text-[#52616C] font-medium">{label}</span>
              </div>
              <span className="font-bold text-[#102C46]">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
