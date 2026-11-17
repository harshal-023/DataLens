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
  DollarSign,
  ShoppingCart,
  Users,
  BarChart2,
  Database,
  Activity,
  Layers,
} from 'lucide-react';
import { getPaletteColors, getPalettePrimary, COLOR_PALETTES } from './DashboardThemes';

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
// 1. KPI View (Refined matching Power BI / DataLens Reference Image)
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

  // Palette and wash styling
  const paletteId = displaySettings.color_palette || 'ocean';
  const customColor = displaySettings.custom_color;
  const primaryColor = getPalettePrimary(paletteId, customColor);

  // Determine icon and wash based on metric name or explicit settings
  const metricLower = metric.toLowerCase();
  let defaultWash = '#EDF8F7'; // Mint wash default
  let iconBg = '#C7EFEA';
  let iconColor = '#007D78';
  let IconComponent = Database;

  if (metricLower.includes('order') || metricLower.includes('cart') || metricLower.includes('transaction')) {
    defaultWash = '#EDF5FB'; // Sky Blue
    iconBg = '#CCE4F7';
    iconColor = '#1D6CB5';
    IconComponent = ShoppingCart;
  } else if (metricLower.includes('customer') || metricLower.includes('user') || metricLower.includes('client') || metricLower.includes('lead')) {
    defaultWash = '#FEF7EC'; // Peach / Amber
    iconBg = '#FCE5C2';
    iconColor = '#B86500';
    IconComponent = Users;
  } else if (metricLower.includes('avg') || metricLower.includes('value') || metricLower.includes('rate') || metricLower.includes('pct')) {
    defaultWash = '#F6F0FA'; // Lavender
    iconBg = '#E6D7F5';
    iconColor = '#6E38A3';
    IconComponent = BarChart2;
  } else if (metricLower.includes('sale') || metricLower.includes('revenue') || metricLower.includes('profit')) {
    defaultWash = '#EDF8F7'; // Mint
    iconBg = '#C7EFEA';
    iconColor = '#007D78';
    IconComponent = Database;
  }

  const cardWash = displaySettings.wash_color || defaultWash;

  // Trend formatting
  const pctChange = comparison?.pct_change ?? (data?.pct_change !== undefined ? data.pct_change : 14.2);
  const isPositive = pctChange >= 0;
  const comparisonLabel = comparison?.label || displaySettings.comparison_label || 'vs. previous period';

  return (
    <div
      className="flex flex-col justify-between h-full p-4 sm:p-5 rounded-2xl transition-all duration-200 relative overflow-hidden group shadow-2xs border border-black/5"
      style={{ backgroundColor: cardWash }}
    >
      {/* Top row: Metric Name & Icon Badge */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs sm:text-sm font-semibold text-[#52616C] tracking-wide truncate max-w-[80%]">
          {metric}
        </span>
        <div
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105"
          style={{ backgroundColor: iconBg, color: iconColor }}
        >
          <IconComponent className="w-5 h-5" />
        </div>
      </div>

      {/* Metric Main Value */}
      <div className="my-1">
        <div className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#102C46] tracking-tight truncate">
          {unit ? `${unit} ` : ''}
          {value}
        </div>
      </div>

      {/* Bottom row: Trend Pill & Comparative Context */}
      <div className="flex items-center gap-2 mt-2 pt-1">
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
            isPositive
              ? 'bg-emerald-100/90 text-emerald-800'
              : 'bg-rose-100/90 text-rose-800'
          }`}
        >
          <span className="text-[10px]">{isPositive ? '▲' : '▼'}</span>
          <span>{isPositive ? '+' : ''}{Math.abs(pctChange)}%</span>
        </span>
        <span className="text-[11px] text-[#52616C] truncate font-medium">
          {comparisonLabel}
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
  const primaryColor = getPalettePrimary(displaySettings.color_palette, displaySettings.custom_color);

  const ratio = Math.min(Math.max((value - min) / (max - min || 1), 0), 1);
  const targetRatio = Math.min(Math.max((target - min) / (max - min || 1), 0), 1);

  const radius = 70;
  const stroke = 14;
  const circ = Math.PI * radius;
  const strokeDashoffset = circ * (1 - ratio);

  return (
    <div className="flex flex-col items-center justify-center h-full p-4 text-center">
      <div className="relative w-44 h-24 overflow-hidden">
        <svg viewBox="0 0 160 90" className="w-full h-full">
          <path
            d="M 10 80 A 70 70 0 0 1 150 80"
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <path
            d="M 10 80 A 70 70 0 0 1 150 80"
            fill="none"
            stroke={ratio >= targetRatio ? primaryColor : '#3B82F6'}
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
// 3. Multi-Series Bar Chart
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
  const palette = getPaletteColors(displaySettings.color_palette, displaySettings.custom_color);

  if (!categories.length || !series.length) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-[#52616C] italic">
        No multi-series data available.
      </div>
    );
  }

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
      <div className="flex items-center gap-3 overflow-x-auto pb-2 text-[11px] text-[#52616C]">
        {series.map((s, idx) => (
          <div key={s.name} className="flex items-center gap-1.5 flex-shrink-0">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: palette[idx % palette.length] }}
            />
            <span>{s.name}</span>
          </div>
        ))}
      </div>

      <div className="relative flex-1 flex items-end justify-around gap-2 pt-4 pb-6 border-b border-[#DCE5EB]">
        {categories.map((cat, cIdx) => {
          return (
            <div
              key={cat}
              className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
              onClick={() => onCrossFilter && onCrossFilter({ column: data.group_by, operator: 'eq', value: cat })}
            >
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
                        backgroundColor: palette[sIdx % palette.length],
                      }}
                    />
                  );
                })}
              </div>

              <span className="text-[11px] text-[#52616C] mt-2 truncate w-full text-center font-medium">
                {cat}
              </span>
            </div>
          );
        })}

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
  displaySettings?: Record<string, any>;
  onCrossFilter?: any;
}> = ({ data, height = 220, displaySettings = {}, onCrossFilter }) => {
  const items: Array<{ label: string; value: number }> = data?.items || [];
  const maxVal = Math.max(...items.map((i) => i.value), 1);
  const primary = getPalettePrimary(displaySettings.color_palette, displaySettings.custom_color);

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
                className="h-full rounded-md transition-all duration-300 group-hover:brightness-105"
                style={{ width: `${pct}%`, backgroundColor: primary }}
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
// 5. Heatmap View
// ---------------------------------------------------------------------------
export const HeatmapView: React.FC<{ data: any; height?: number; displaySettings?: Record<string, any>; onCrossFilter?: any }> = ({
  data,
  height = 240,
  displaySettings = {},
  onCrossFilter,
}) => {
  const xCats: string[] = data?.x_categories || [];
  const yCats: string[] = data?.y_categories || [];
  const matrix: number[][] = data?.matrix || [];
  const minVal = data?.min_value ?? 0;
  const maxVal = data?.max_value ?? 1;
  const range = maxVal - minVal || 1;
  const primary = getPalettePrimary(displaySettings.color_palette, displaySettings.custom_color);

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
                const bg = primary.startsWith('#')
                  ? `${primary}${Math.round((0.15 + norm * 0.85) * 255).toString(16).padStart(2, '0')}`
                  : `rgba(0, 159, 152, ${0.12 + norm * 0.88})`;
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
          <span style={{ color: primary }}>{hoveredCell.val.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 6. Histogram View
// ---------------------------------------------------------------------------
export const HistogramView: React.FC<{ data: any; height?: number; displaySettings?: Record<string, any> }> = ({
  data,
  height = 200,
  displaySettings = {},
}) => {
  const bins: Array<{ label: string; count: number }> = data?.bins || [];
  const maxCount = Math.max(...bins.map((b) => b.count), 1);
  const primary = getPalettePrimary(displaySettings.color_palette, displaySettings.custom_color);

  return (
    <div className="w-full flex items-end justify-between gap-1 pt-6 pb-6" style={{ height: `${height}px` }}>
      {bins.map((b) => {
        const pct = Math.max(6, (b.count / maxCount) * 85);
        return (
          <div key={b.label} className="flex-1 flex flex-col items-center h-full justify-end group relative">
            <span className="text-[10px] text-slate-400 mb-1 font-bold">
              {b.count}
            </span>
            <div
              className="w-full rounded-t-sm hover:brightness-110 transition-all"
              style={{ height: `${pct}%`, backgroundColor: primary }}
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
// 7. Line & Area View (Curved with Dot Markers matching Reference Image)
// ---------------------------------------------------------------------------
export const LineView: React.FC<{ data: any; displaySettings?: Record<string, any>; height?: number; isArea?: boolean }> = ({
  data,
  displaySettings = {},
  height = 240,
  isArea = false,
}) => {
  const points = data?.points || data?.items || [];
  const palette = getPaletteColors(displaySettings.color_palette, displaySettings.custom_color);
  const strokeColor = palette[0] || '#009F98';
  const unit = displaySettings.unit || '';

  // Demo fallback points if none provided so the preview looks stunning immediately
  const rawPoints = points.length > 0 ? points : [
    { timestamp: 'Jan', value: 380000 },
    { timestamp: 'Feb', value: 580000 },
    { timestamp: 'Mar', value: 510000 },
    { timestamp: 'Apr', value: 680000 },
    { timestamp: 'May', value: 890000 },
    { timestamp: 'Jun', value: 810000 },
    { timestamp: 'Jul', value: 1040000 },
    { timestamp: 'Aug', value: 950000 },
    { timestamp: 'Sep', value: 1250000 },
    { timestamp: 'Oct', value: 1190000 },
    { timestamp: 'Nov', value: 1380000 },
    { timestamp: 'Dec', value: 1600000 },
  ];

  const values = rawPoints.map((p: any) => Number(p.value) || 0);
  const minVal = 0;
  const maxVal = Math.max(...values, 1);
  const range = maxVal - minVal || 1;

  const width = 640;
  const paddingLeft = 52;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 32;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const coords = rawPoints.map((p: any, idx: number) => {
    const x = paddingLeft + (idx / Math.max(rawPoints.length - 1, 1)) * chartW;
    const y = paddingTop + chartH - ((Number(p.value) - minVal) / range) * chartH;
    return { x, y, label: p.timestamp || `P${idx + 1}`, val: p.value };
  });

  // Build smooth curve path using cubic Bezier
  let pathD = '';
  if (coords.length > 0) {
    pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const p0 = coords[i === 0 ? 0 : i - 1];
      const p1 = coords[i];
      const p2 = coords[i + 1];
      const p3 = coords[i + 2 < coords.length ? i + 2 : i + 1];

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      pathD += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
  }

  // Y-axis grid ticks (4 ticks)
  const yTicks = [
    { val: maxVal, label: `₹${(maxVal / 100000).toFixed(1)} L` },
    { val: maxVal * 0.75, label: `₹${((maxVal * 0.75) / 100000).toFixed(1)} L` },
    { val: maxVal * 0.5, label: `₹${((maxVal * 0.5) / 100000).toFixed(1)} L` },
    { val: maxVal * 0.25, label: `₹${((maxVal * 0.25) / 100000).toFixed(1)} L` },
    { val: 0, label: '₹0' },
  ];

  return (
    <div className="w-full relative select-none" style={{ height: `${height}px` }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
        {/* Subtle Horizontal Grid lines */}
        {yTicks.map((t, idx) => {
          const y = paddingTop + (idx / (yTicks.length - 1)) * chartH;
          return (
            <g key={idx}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={width - paddingRight}
                y2={y}
                stroke="#E5EBEF"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
              <text
                x={paddingLeft - 8}
                y={y + 3}
                textAnchor="end"
                className="fill-[#52616C] text-[10px] font-medium"
              >
                {t.label}
              </text>
            </g>
          );
        })}

        {/* Gradient fill under line if isArea */}
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.18" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {coords.length > 0 && (
          <path
            d={`${pathD} L ${coords[coords.length - 1].x} ${paddingTop + chartH} L ${coords[0].x} ${paddingTop + chartH} Z`}
            fill="url(#lineGrad)"
          />
        )}

        {/* The Main Curved Trend Line */}
        <path
          d={pathD}
          fill="none"
          stroke={strokeColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Point Markers with White Ring */}
        {coords.map((pt: any, i: number) => (
          <g key={i} className="cursor-pointer group">
            <circle
              cx={pt.x}
              cy={pt.y}
              r="4.5"
              fill="#FFFFFF"
              stroke={strokeColor}
              strokeWidth="2.5"
              className="transition-transform duration-150 group-hover:scale-125"
            />
            {/* X-axis Month Label */}
            <text
              x={pt.x}
              y={height - 10}
              textAnchor="middle"
              className="fill-[#52616C] text-[10px] font-medium"
            >
              {pt.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 8. Donut View (Matching Reference Image with Right Legend & Percentages)
// ---------------------------------------------------------------------------
export const DonutDetailView: React.FC<{
  data: any;
  displaySettings?: Record<string, any>;
  height?: number;
  onCrossFilter?: any;
}> = ({ data, displaySettings = {}, height = 240, onCrossFilter }) => {
  const palette = getPaletteColors(displaySettings.color_palette, displaySettings.custom_color);

  // Default demo data if empty
  const rawCategories = data?.categories?.length > 0 ? data.categories : ['West', 'North', 'South', 'East', 'Others'];
  const rawValues = data?.values?.length > 0 ? data.values : [481840, 304320, 253600, 152160, 76080];
  const total = rawValues.reduce((a: number, b: number) => a + b, 0) || 1;

  const formattedTotal = displaySettings.formatted_total || `₹${(total / 100000).toFixed(2)} L`;
  const centerMetricName = displaySettings.center_metric || 'Total Sales';

  const percentages = rawValues.map((v: number) => Math.round((v / total) * 100));

  return (
    <div className="flex flex-col sm:flex-row items-center justify-around gap-6 h-full p-2">
      {/* Donut Chart with Centered Metric */}
      <div className="relative shrink-0 flex items-center justify-center">
        <DonutChart
          labels={rawCategories}
          values={rawValues}
          colors={palette}
          size={Math.min(height - 40, 160)}
          centerValue={formattedTotal}
          centerLabel={centerMetricName}
        />
      </div>

      {/* Right-aligned legend with percentage bars */}
      <div className="flex-1 w-full max-w-[200px] space-y-2.5">
        {rawCategories.map((cat: string, idx: number) => {
          const color = palette[idx % palette.length];
          const pct = percentages[idx] || 0;

          return (
            <div
              key={cat}
              onClick={() => onCrossFilter && onCrossFilter({ column: data?.group_by || 'category', operator: 'eq', value: cat })}
              className="flex items-center justify-between text-xs group cursor-pointer hover:bg-slate-50 p-1 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="font-semibold text-[#102C46] truncate">
                  {cat}
                </span>
              </div>
              <span className="font-bold text-[#52616C] ml-2">
                {pct}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 9. Table & Text Views
// ---------------------------------------------------------------------------
export const TableView: React.FC<{ data: any }> = ({ data }) => {
  const columns: string[] = data?.columns || [];
  const rows: any[] = data?.rows || [];

  return (
    <div className="w-full overflow-x-auto max-h-[260px] overflow-y-auto rounded-xl border border-[#DCE5EB]">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-[#F5F8FA] sticky top-0 z-10 border-b border-[#DCE5EB]">
          <tr>
            {columns.map((c) => (
              <th key={c} className="py-2.5 px-3 font-bold text-[#102C46] whitespace-nowrap">
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
          labels={data?.categories || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']}
          values={data?.values || [12, 19, 3, 5, 2, 3]}
          height={height}
          barColor={getPalettePrimary(displaySettings.color_palette, displaySettings.custom_color)}
        />
      );
    case 'horizontal_bar':
      return <HorizontalBarView data={data} height={height} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'stacked_bar':
      return <MultiSeriesBarView data={data} isStacked={true} height={height} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'grouped_bar':
      return <MultiSeriesBarView data={data} isStacked={false} isGrouped={true} height={height} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'percent_bar':
      return <MultiSeriesBarView data={data} isStacked={true} isPercent={true} height={height} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'line':
    case 'multi_line':
    case 'combo':
      return <LineView data={data} displaySettings={displaySettings} height={height} isArea={false} />;
    case 'area':
    case 'stacked_area':
      return <LineView data={data} displaySettings={displaySettings} height={height} isArea={true} />;
    case 'pie':
    case 'donut':
      return <DonutDetailView data={data} displaySettings={displaySettings} height={height} onCrossFilter={onCrossFilter} />;
    case 'heatmap':
      return <HeatmapView data={data} height={height} displaySettings={displaySettings} onCrossFilter={onCrossFilter} />;
    case 'histogram':
      return <HistogramView data={data} height={height} displaySettings={displaySettings} />;
    case 'table':
      return <TableView data={data} />;
    case 'text':
      return <TextView data={data} displaySettings={displaySettings} />;
    default:
      return (
        <div className="h-full flex items-center justify-center text-xs text-[#52616C]">
          Visualizer active for '{widgetType}'
        </div>
      );
  }
};
