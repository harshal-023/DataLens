import React, { useState } from 'react';
import { DonutChart, BarChart } from '../charts/Charts';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Hash,
  Table as TableIcon,
  ChevronRight,
  Filter,
  CheckCircle2,
  AlertCircle,
  Flame,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';

// Brand colors adhering to Deep Navy & Peacock Teal identity
const PRIMARY_TEAL = '#009F98';
const DEEP_NAVY = '#102C46';
const LIGHT_TEAL = '#39C3B8';
const LIGHT_CYAN = '#8BE5DE';
const MUTED_SLATE = '#52616C';
const DANGER_RED = '#A63838';

const PALETTE = [
  '#009F98', // Peacock Teal
  '#102C46', // Deep Navy
  '#39C3B8', // Light Teal
  '#1D4664', // Secondary Navy
  '#52616C', // Slate
  '#8BE5DE', // Cyan
  '#F59E0B', // Amber
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#10B981', // Emerald
];

export interface WidgetVisualizationProps {
  widgetType: string;
  data: any;
  displaySettings?: Record<string, any>;
  height?: number;
  onCrossFilter?: (filter: { column: string; operator: string; value: any }) => void;
  activeCrossFilters?: Array<{ column: string; value: any }>;
  onDrillDown?: (column: string, value: any) => void;
  currentDrillDepth?: number;
  hierarchyLevels?: string[];
  onDrillUp?: () => void;
}

// ---------------------------------------------------------------------------
// 1. KPI & Gauge View
// ---------------------------------------------------------------------------
export const KPIView: React.FC<{
  data: any;
  displaySettings?: Record<string, any>;
  onCrossFilter?: any;
}> = ({ data, displaySettings = {} }) => {
  const value = data?.formatted_value ?? data?.value ?? '0';
  const metric = data?.metric || displaySettings.metric_name || 'Total Metric';
  const unit = displaySettings.unit || '';
  const subtitle =
    displaySettings.subtitle ||
    (data?.aggregation ? `${data?.aggregation?.toUpperCase()} aggregation` : '');
  const comparison = data?.comparison;

  return (
    <div className="flex flex-col justify-between h-full p-4 bg-gradient-to-br from-white to-[#F5F8FA] rounded-xl border border-[#DCE5EB]/60">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[#52616C] uppercase tracking-wider">
          {metric}
        </span>
        <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] flex items-center justify-center text-[#009F98]">
          <Hash className="w-4 h-4" />
        </div>
      </div>

      <div className="my-2">
        <div className="text-3xl sm:text-4xl font-extrabold text-[#102C46] tracking-tight">
          {unit ? `${unit} ` : ''}
          {value}
        </div>

        {/* Comparative Analytics Pill */}
        {comparison && (
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-bold ${
                comparison.direction === 'up'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : comparison.direction === 'down'
                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {comparison.direction === 'up' ? (
                <ArrowUpRight className="w-3.5 h-3.5" />
              ) : comparison.direction === 'down' ? (
                <ArrowDownRight className="w-3.5 h-3.5" />
              ) : (
                <Minus className="w-3.5 h-3.5" />
              )}
              {comparison.pct_change > 0 ? '+' : ''}
              {comparison.pct_change}%
            </span>
            <span className="text-[11px] text-[#52616C]">
              vs Target ({unit}
              {comparison.target?.toLocaleString()})
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-[#52616C] pt-2 border-t border-[#DCE5EB]/40">
        <span className="font-medium">{subtitle}</span>
        <span className="flex items-center gap-1 text-[#009F98] font-bold">
          <TrendingUp className="w-3.5 h-3.5" />
          Verified
        </span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 2. Gauge View (Radial/Semi-Circle)
// ---------------------------------------------------------------------------
export const GaugeView: React.FC<{ data: any; displaySettings?: Record<string, any> }> = ({
  data,
  displaySettings = {},
}) => {
  const value = Number(data?.value || 0);
  const target = Number(data?.target || 100);
  const min = Number(data?.min || 0);
  const max = Number(data?.max || Math.max(target * 1.25, 100));
  const percentOfTarget = data?.percent_of_target ?? Math.round((value / target) * 100);
  const unit = displaySettings.unit || '';

  const ratio = Math.min(Math.max((value - min) / (max - min || 1), 0), 1);
  const targetRatio = Math.min(Math.max((target - min) / (max - min || 1), 0), 1);

  // Semi-circle SVG angles: -180 deg to 0 deg
  const radius = 70;
  const stroke = 14;
  const circ = Math.PI * radius; // half circle circumference
  const strokeDashoffset = circ * (1 - ratio);

  return (
    <div className="flex flex-col items-center justify-center h-full p-4 text-center">
      <div className="relative w-44 h-24 overflow-hidden">
        <svg viewBox="0 0 160 90" className="w-full h-full">
          {/* Background Arc */}
          <path
            d="M 10 80 A 70 70 0 0 1 150 80"
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          {/* Active Progress Arc */}
          <path
            d="M 10 80 A 70 70 0 0 1 150 80"
            fill="none"
            stroke={ratio >= targetRatio ? PRIMARY_TEAL : '#3B82F6'}
            strokeWidth={stroke}
            strokeDasharray={circ}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        <div className="absolute inset-x-0 bottom-0 text-center">
          <div className="text-2xl font-bold text-[#102C46]">
            {unit}
            {value.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="mt-2 text-xs text-[#52616C] flex items-center gap-3">
        <span>Min: {min}</span>
        <span className="font-semibold text-[#009F98]">
          Target: {unit}
          {target.toLocaleString()} ({percentOfTarget}%)
        </span>
        <span>Max: {max}</span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 3. Multi-Series Bar Chart (Stacked, Grouped, 100% Stacked)
// ---------------------------------------------------------------------------
export const MultiSeriesBarView: React.FC<{
  data: any;
  isStacked?: boolean;
  isPercent?: boolean;
  isGrouped?: boolean;
  displaySettings?: Record<string, any>;
  height?: number;
  onCrossFilter?: any;
}> = ({
  data,
  isStacked = true,
  isPercent = false,
  isGrouped = false,
  displaySettings = {},
  height = 220,
  onCrossFilter,
}) => {
  const [hovered, setHovered] = useState<{ cat: string; sName: string; val: number } | null>(null);

  const categories: string[] = data?.categories || [];
  const series: Array<{ name: string; values: number[] }> = data?.series || [];

  if (!categories.length || !series.length) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-[#52616C] italic">
        No multi-series data available.
      </div>
    );
  }

  // Calculate maximum total or individual value
  let maxScale = 1;
  if (isPercent) {
    maxScale = 100;
  } else if (isStacked) {
    const totals = categories.map((_, cIdx) => series.reduce((sum, s) => sum + (s.values[cIdx] || 0), 0));
    maxScale = Math.max(...totals, 1);
  } else {
    const allVals = series.flatMap((s) => s.values);
    maxScale = Math.max(...allVals, 1);
  }

  return (
    <div className="w-full flex flex-col justify-between" style={{ height: `${height}px` }}>
      {/* Legend */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 text-[11px] text-[#52616C]">
        {series.map((s, idx) => (
          <div key={s.name} className="flex items-center gap-1.5 flex-shrink-0">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: PALETTE[idx % PALETTE.length] }}
            />
            <span>{s.name}</span>
          </div>
        ))}
      </div>

      {/* Bars Canvas */}
      <div className="relative flex-1 flex items-end justify-around gap-2 pt-4 pb-6 border-b border-[#DCE5EB]">
        {categories.map((cat, cIdx) => {
          return (
            <div
              key={cat}
              className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
              onClick={() => onCrossFilter && onCrossFilter({ column: data.group_by, operator: 'eq', value: cat })}
            >
              {/* Stacked or Grouped container */}
              <div
                className={`w-full max-w-[48px] flex ${
                  isGrouped ? 'flex-row items-end gap-0.5' : 'flex-col-reverse'
                }`}
                style={{ height: '80%' }}
              >
                {series.map((s, sIdx) => {
                  const val = s.values[cIdx] || 0;
                  const barH = isPercent
                    ? `${val}%`
                    : isStacked
                    ? `${(val / maxScale) * 100}%`
                    : `${(val / maxScale) * 100}%`;

                  return (
                    <div
                      key={s.name}
                      onMouseEnter={() => setHovered({ cat, sName: s.name, val })}
                      onMouseLeave={() => setHovered(null)}
                      className="w-full rounded-xs transition-all hover:opacity-100 opacity-90"
                      style={{
                        height: barH,
                        backgroundColor: PALETTE[sIdx % PALETTE.length],
                      }}
                    />
                  );
                })}
              </div>

              {/* X Axis Label */}
              <span className="text-[11px] text-[#52616C] mt-2 truncate w-full text-center font-medium">
                {cat}
              </span>
            </div>
          );
        })}

        {/* Floating Tooltip */}
        {hovered && (
          <div className="absolute top-2 right-2 bg-[#102C46] text-white text-[11px] px-2.5 py-1.5 rounded-lg shadow-lg z-20 pointer-events-none">
            <div className="font-bold">{hovered.cat}</div>
            <div>
              {hovered.sName}:{' '}
              <span className="text-[#39C3B8]">
                {hovered.val.toLocaleString()}
                {isPercent ? '%' : ''}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 4. Horizontal Bar View
// ---------------------------------------------------------------------------
export const HorizontalBarView: React.FC<{
  data: any;
  height?: number;
  onCrossFilter?: any;
}> = ({ data, height = 220, onCrossFilter }) => {
  const items: Array<{ label: string; value: number }> = data?.items || [];
  const maxVal = Math.max(...items.map((i) => i.value), 1);

  return (
    <div className="w-full overflow-y-auto space-y-2 pr-2" style={{ maxHeight: `${height}px` }}>
      {items.map((it) => {
        const pct = Math.max(4, (it.value / maxVal) * 100);
        return (
          <div
            key={it.label}
            onClick={() => onCrossFilter && onCrossFilter({ column: data.group_by, operator: 'eq', value: it.label })}
            className="flex items-center gap-3 text-xs group cursor-pointer hover:bg-slate-50 p-1 rounded-lg"
          >
            <span className="w-28 text-right font-medium text-[#102C46] truncate">
              {it.label}
            </span>
            <div className="flex-1 h-5 bg-slate-100 rounded-md overflow-hidden relative">
              <div
                className="h-full bg-gradient-to-r from-[#009F98] to-[#39C3B8] rounded-md transition-all duration-300 group-hover:brightness-105"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-16 text-right font-bold text-[#102C46]">
              {it.value.toLocaleString()}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 5. Heatmap View (2D Intensity Grid)
// ---------------------------------------------------------------------------
export const HeatmapView: React.FC<{ data: any; height?: number; onCrossFilter?: any }> = ({
  data,
  height = 240,
  onCrossFilter,
}) => {
  const xCats: string[] = data?.x_categories || [];
  const yCats: string[] = data?.y_categories || [];
  const matrix: number[][] = data?.matrix || [];
  const minVal = data?.min_value ?? 0;
  const maxVal = data?.max_value ?? 1;
  const range = maxVal - minVal || 1;

  const [hoveredCell, setHoveredCell] = useState<{ x: string; y: string; val: number } | null>(null);

  return (
    <div className="w-full overflow-auto flex flex-col justify-between" style={{ height: `${height}px` }}>
      <table className="w-full text-center border-collapse text-[10px]">
        <thead>
          <tr>
            <th className="p-1"></th>
            {xCats.map((x) => (
              <th key={x} className="p-1 font-bold text-[#102C46] truncate max-w-[60px]">
                {x}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {yCats.map((y, rIdx) => (
            <tr key={y}>
              <td className="p-1 font-bold text-[#102C46] text-right truncate max-w-[80px]">
                {y}
              </td>
              {xCats.map((x, cIdx) => {
                const val = matrix[rIdx]?.[cIdx] ?? 0;
                const norm = Math.min(Math.max((val - minVal) / range, 0), 1);
                // Heat color from light teal to deep peacock
                const bg = `rgba(0, 159, 152, ${0.12 + norm * 0.88})`;
                const textCol = norm > 0.5 ? '#FFFFFF' : '#102C46';

                return (
                  <td
                    key={x}
                    onMouseEnter={() => setHoveredCell({ x, y, val })}
                    onMouseLeave={() => setHoveredCell(null)}
                    onClick={() => onCrossFilter && onCrossFilter({ column: 'region', operator: 'eq', value: x })}
                    className="p-2 border border-white cursor-pointer transition-transform hover:scale-105 rounded-xs"
                    style={{ backgroundColor: bg, color: textCol }}
                  >
                    {val.toLocaleString()}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {hoveredCell && (
        <div className="text-center text-xs text-[#102C46] font-semibold pt-1">
          {hoveredCell.y} × {hoveredCell.x}:{' '}
          <span className="text-[#009F98]">{hoveredCell.val.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 6. Histogram View
// ---------------------------------------------------------------------------
export const HistogramView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 200,
}) => {
  const bins: Array<{ label: string; count: number }> = data?.bins || [];
  const maxCount = Math.max(...bins.map((b) => b.count), 1);

  return (
    <div className="w-full flex items-end justify-between gap-1 pt-6 pb-6" style={{ height: `${height}px` }}>
      {bins.map((b) => {
        const pct = Math.max(6, (b.count / maxCount) * 85);
        return (
          <div key={b.label} className="flex-1 flex flex-col items-center h-full justify-end group relative">
            <span className="text-[10px] text-slate-400 mb-1 group-hover:text-[#009F98] font-bold">
              {b.count}
            </span>
            <div
              className="w-full bg-[#009F98] rounded-t-sm hover:brightness-110 transition-all"
              style={{ height: `${pct}%` }}
            />
            <span className="text-[9px] text-[#52616C] mt-1.5 truncate max-w-[60px] text-center">
              {b.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 7. Box Plot View
// ---------------------------------------------------------------------------
export const BoxPlotView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 220,
}) => {
  const items: Array<{
    label: string;
    min: number;
    q1: number;
    median: number;
    q3: number;
    max: number;
  }> = data?.items || [];

  if (!items.length) {
    return <div className="text-xs text-slate-400 italic text-center py-8">No box plot data.</div>;
  }

  const globalMin = Math.min(...items.map((i) => i.min));
  const globalMax = Math.max(...items.map((i) => i.max), 1);
  const range = globalMax - globalMin || 1;

  const toY = (val: number) => 100 - ((val - globalMin) / range) * 100;

  return (
    <div className="w-full flex items-center justify-around gap-4 px-2" style={{ height: `${height}px` }}>
      {items.map((item) => {
        const yMin = toY(item.min);
        const yQ1 = toY(item.q1);
        const yMed = toY(item.median);
        const yQ3 = toY(item.q3);
        const yMax = toY(item.max);

        return (
          <div key={item.label} className="flex-1 flex flex-col items-center h-full justify-between py-2">
            <div className="relative w-8 h-40 flex items-center justify-center">
              {/* Whiskers Vertical Line */}
              <div
                className="absolute w-0.5 bg-slate-400"
                style={{ top: `${yMax}%`, bottom: `${100 - yMin}%` }}
              />
              {/* Max Whisker Bar */}
              <div
                className="absolute w-4 h-0.5 bg-slate-600"
                style={{ top: `${yMax}%` }}
              />
              {/* Min Whisker Bar */}
              <div
                className="absolute w-4 h-0.5 bg-slate-600"
                style={{ top: `${yMin}%` }}
              />

              {/* IQR Box (Q3 to Q1) */}
              <div
                className="absolute w-8 bg-[#EDF7FA] border border-[#009F98] rounded-xs shadow-xs"
                style={{
                  top: `${Math.min(yQ3, yQ1)}%`,
                  height: `${Math.abs(yQ1 - yQ3)}%`,
                }}
              >
                {/* Median Line */}
                <div
                  className="absolute w-full h-0.5 bg-[#102C46]"
                  style={{ top: `${((yMed - Math.min(yQ3, yQ1)) / (Math.abs(yQ1 - yQ3) || 1)) * 100}%` }}
                />
              </div>
            </div>
            <span className="text-[11px] font-bold text-[#102C46] truncate mt-1">
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 8. Funnel View
// ---------------------------------------------------------------------------
export const FunnelView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 220,
}) => {
  const stages: Array<{
    name: string;
    value: number;
    conversion_rate: number;
    drop_off_rate: number;
  }> = data?.stages || [];

  return (
    <div className="w-full space-y-2 overflow-y-auto pr-1" style={{ maxHeight: `${height}px` }}>
      {stages.map((st, idx) => (
        <div key={st.name} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-[#102C46]">{st.name}</span>
            <div className="flex items-center gap-2">
              <span className="font-bold text-[#009F98]">{st.value.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">({st.conversion_rate}%)</span>
            </div>
          </div>
          <div className="w-full h-4 bg-slate-100 rounded-md overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#009F98] to-[#39C3B8] rounded-md transition-all duration-500"
              style={{ width: `${st.conversion_rate}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 9. Waterfall View
// ---------------------------------------------------------------------------
export const WaterfallView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 220,
}) => {
  const items: Array<{
    label: string;
    value: number;
    running_total: number;
    type: string;
  }> = data?.items || [];

  const maxVal = Math.max(...items.map((i) => Math.abs(i.running_total)), 1);

  return (
    <div className="w-full flex items-end justify-around gap-2 pt-6 pb-6" style={{ height: `${height}px` }}>
      {items.map((it) => {
        const isPos = it.value >= 0;
        const barH = Math.max(8, (Math.abs(it.value) / maxVal) * 75);
        return (
          <div key={it.label} className="flex-1 flex flex-col items-center h-full justify-end group">
            <span className="text-[10px] text-slate-400 mb-1 font-bold">
              {isPos ? '+' : ''}
              {it.value.toLocaleString()}
            </span>
            <div
              className={`w-full max-w-[36px] rounded-t-sm transition-all ${
                isPos ? 'bg-[#009F98]' : 'bg-rose-600'
              }`}
              style={{ height: `${barH}%` }}
            />
            <span className="text-[10px] text-[#52616C] mt-1.5 truncate max-w-[50px] text-center">
              {it.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 10. Pareto Chart View (80/20 Rule)
// ---------------------------------------------------------------------------
export const ParetoView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 220,
}) => {
  const items: Array<{ label: string; value: number; cumulative_pct: number }> =
    data?.items || [];
  const maxVal = Math.max(...items.map((i) => i.value), 1);

  return (
    <div className="w-full relative pt-4 pb-6" style={{ height: `${height}px` }}>
      {/* 80% Threshold Line */}
      <div className="absolute inset-x-0 top-[20%] border-b border-dashed border-rose-400 z-10 flex items-center justify-end pr-2">
        <span className="text-[9px] font-bold text-rose-500 bg-white px-1">80% Pareto Cutoff</span>
      </div>

      <div className="h-full flex items-end justify-around gap-2">
        {items.map((it) => {
          const barH = Math.max(8, (it.value / maxVal) * 80);
          return (
            <div key={it.label} className="flex-1 flex flex-col items-center h-full justify-end group">
              <span className="text-[10px] text-[#009F98] font-bold mb-1">
                {it.cumulative_pct}%
              </span>
              <div
                className="w-full max-w-[36px] bg-[#102C46] rounded-t-sm group-hover:bg-[#009F98] transition-colors"
                style={{ height: `${barH}%` }}
              />
              <span className="text-[10px] text-[#52616C] mt-1.5 truncate max-w-[50px] text-center">
                {it.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 11. Treemap View
// ---------------------------------------------------------------------------
export const TreemapView: React.FC<{ data: any; height?: number }> = ({
  data,
  height = 220,
}) => {
  const nodes: Array<{ name: string; value: number; percent: number }> = data?.nodes || [];

  return (
    <div className="w-full flex flex-wrap gap-1.5 overflow-hidden p-1" style={{ height: `${height}px` }}>
      {nodes.map((n, idx) => (
        <div
          key={n.name}
          className="rounded-lg p-2 text-white flex flex-col justify-between transition-transform hover:scale-[1.02] cursor-pointer"
          style={{
            flex: `1 1 ${Math.max(n.percent * 2, 60)}px`,
            backgroundColor: PALETTE[idx % PALETTE.length],
            minHeight: '60px',
          }}
        >
          <span className="text-xs font-bold truncate">{n.name}</span>
          <div className="flex items-center justify-between text-[11px] opacity-90">
            <span>{n.value.toLocaleString()}</span>
            <span>{n.percent}%</span>
          </div>
        </div>
      ))}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Existing Line / Area / Scatter / Table / Text Views
// ---------------------------------------------------------------------------
export const LineView: React.FC<{ data: any; displaySettings?: Record<string, any>; height?: number }> = ({
  data,
  displaySettings = {},
  height = 220,
}) => {
  const points = data?.points || data?.items || [];
  if (!points.length) return <div className="text-xs text-slate-400 italic text-center py-8">No time-series data.</div>;

  const values = points.map((p: any) => Number(p.value) || 0);
  const minVal = Math.min(...values, 0);
  const maxVal = Math.max(...values, 1);
  const range = maxVal - minVal || 1;

  const width = 600;
  const paddingX = 40;
  const paddingY = 24;
  const chartW = width - paddingX * 2;
  const chartH = height - paddingY * 2;

  const coords = points.map((p: any, idx: number) => {
    const x = paddingX + (idx / Math.max(points.length - 1, 1)) * chartW;
    const y = height - paddingY - ((Number(p.value) - minVal) / range) * chartH;
    return { x, y, label: p.timestamp || `P${idx + 1}`, val: p.value };
  });

  const pathD = coords.reduce((acc: string, pt: any, idx: number) => `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`, '');

  return (
    <div className="w-full relative" style={{ height: `${height}px` }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
        <path d={pathD} fill="none" stroke={PRIMARY_TEAL} strokeWidth="2.5" strokeLinecap="round" />
        {coords.map((pt: any, i: number) => (
          <circle key={i} cx={pt.x} cy={pt.y} r="3" fill="#FFFFFF" stroke={PRIMARY_TEAL} strokeWidth="2" />
        ))}
      </svg>
    </div>
  );
};

export const TableView: React.FC<{ data: any }> = ({ data }) => {
  const columns: string[] = data?.columns || [];
  const rows: any[] = data?.rows || [];

  return (
    <div className="w-full overflow-x-auto max-h-[260px] overflow-y-auto rounded-lg border border-[#DCE5EB]">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-[#F5F8FA] sticky top-0 z-10 border-b border-[#DCE5EB]">
          <tr>
            {columns.map((c) => (
              <th key={c} className="py-2 px-3 font-bold text-[#102C46] whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#DCE5EB]/60">
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-slate-50 transition-colors">
              {columns.map((c) => (
                <td key={c} className="py-2 px-3 text-[#52616C] whitespace-nowrap font-medium">
                  {String(row[c] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const TextView: React.FC<{ data: any; displaySettings?: Record<string, any> }> = ({
  data,
  displaySettings = {},
}) => {
  const content = data?.content || displaySettings.text_content || 'No commentary entered.';
  return (
    <div className="h-full p-4 bg-white rounded-xl border border-[#DCE5EB]/60 flex flex-col justify-center">
      <div className="prose prose-sm max-w-none text-[#102C46] leading-relaxed whitespace-pre-wrap font-sans">
        {content}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Master Visualization Switcher
// ---------------------------------------------------------------------------
export const WidgetVisualization: React.FC<WidgetVisualizationProps> = ({
  widgetType,
  data,
  displaySettings = {},
  height = 200,
  onCrossFilter,
  activeCrossFilters,
  onDrillDown,
  currentDrillDepth,
  hierarchyLevels,
  onDrillUp,
}) => {
  const wt = widgetType.toLowerCase();

  switch (wt) {
    case 'kpi':
      return <KPIView data={data} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'gauge':
      return <GaugeView data={data} displaySettings={displaySettings} />;
    case 'bar':
    case 'top_n':
      return (
        <BarChart
          labels={data?.categories || []}
          values={data?.values || []}
          height={height}
          barColor={PRIMARY_TEAL}
        />
      );
    case 'horizontal_bar':
      return <HorizontalBarView data={data} height={height} onCrossFilter={onCrossFilter} />;
    case 'stacked_bar':
      return <MultiSeriesBarView data={data} isStacked={true} height={height} onCrossFilter={onCrossFilter} />;
    case 'grouped_bar':
      return <MultiSeriesBarView data={data} isStacked={false} isGrouped={true} height={height} onCrossFilter={onCrossFilter} />;
    case 'percent_bar':
      return <MultiSeriesBarView data={data} isStacked={true} isPercent={true} height={height} onCrossFilter={onCrossFilter} />;
    case 'line':
    case 'area':
    case 'multi_line':
    case 'stacked_area':
    case 'combo':
      return <LineView data={data} displaySettings={displaySettings} height={height} />;
    case 'pie':
    case 'donut':
      return (
        <DonutChart
          labels={data?.categories || []}
          values={data?.values || []}
          size={Math.max(120, Math.min(height - 40, 180))}
        />
      );
    case 'heatmap':
      return <HeatmapView data={data} height={height} onCrossFilter={onCrossFilter} />;
    case 'histogram':
      return <HistogramView data={data} height={height} />;
    case 'box_plot':
      return <BoxPlotView data={data} height={height} />;
    case 'funnel':
      return <FunnelView data={data} height={height} />;
    case 'waterfall':
      return <WaterfallView data={data} height={height} />;
    case 'pareto':
      return <ParetoView data={data} height={height} />;
    case 'treemap':
      return <TreemapView data={data} height={height} />;
    case 'table':
      return <TableView data={data} />;
    case 'text':
      return <TextView data={data} displaySettings={displaySettings} />;
    default:
      return (
        <div className="h-full flex items-center justify-center text-xs text-[#52616C]">
          Advanced visualizer for '{widgetType}' active
        </div>
      );
  }
};
