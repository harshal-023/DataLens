import React, { useState, useEffect, useMemo } from 'react';
import {
  Hash,
  BarChart3,
  LineChart as LineIcon,
  AreaChart as AreaIcon,
  PieChart as PieIcon,
  Table as TableIcon,
  FileText,
  Save,
  Database,
  Layers,
  Gauge as GaugeIcon,
  Sliders,
  TrendingUp,
  Activity,
  Filter,
  Check,
  ChevronRight,
  ChevronDown,
  ArrowLeft,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { DashboardWidget } from '../../services/dashboardService';
import { DatasetApi } from '../../services/apiClient';
import { COLOR_PALETTES, getPaletteColors, getPalettePrimary } from './DashboardThemes';
import { WidgetVisualization } from './WidgetVisualizations';

export interface WidgetConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (widgetData: Partial<DashboardWidget>) => Promise<void>;
  workspaceId: string;
  initialWidget?: DashboardWidget | null;
  defaultWidgetType?: string;
}

interface PrimaryWidgetType {
  id: string;
  name: string;
  desc: string;
  icon: any;
  wash: string;
  iconColor: string;
}

const PRIMARY_WIDGET_TYPES: PrimaryWidgetType[] = [
  {
    id: 'kpi',
    name: 'KPI Card',
    desc: 'Single headline summary with trend indicator',
    icon: Hash,
    wash: 'bg-[#EDF8F7]',
    iconColor: 'text-[#009F98]',
  },
  {
    id: 'bar',
    name: 'Bar Chart',
    desc: 'Compare metrics across categories side-by-side',
    icon: BarChart3,
    wash: 'bg-[#EDF5FB]',
    iconColor: 'text-[#2563EB]',
  },
  {
    id: 'line',
    name: 'Line Chart',
    desc: 'Track continuous trends and changes over time',
    icon: LineIcon,
    wash: 'bg-[#F6F0FA]',
    iconColor: 'text-[#8B5CF6]',
  },
  {
    id: 'area',
    name: 'Area Chart',
    desc: 'Display volume magnitude and cumulative growth',
    icon: AreaIcon,
    wash: 'bg-[#FDF2F8]',
    iconColor: 'text-[#EC4899]',
  },
  {
    id: 'donut',
    name: 'Pie / Donut',
    desc: 'Proportions and percentage breakdown of a whole',
    icon: PieIcon,
    wash: 'bg-[#FEF7EC]',
    iconColor: 'text-[#F59E0B]',
  },
  {
    id: 'table',
    name: 'Data Table',
    desc: 'Structured tabular rows and records view',
    icon: TableIcon,
    wash: 'bg-[#ECFDF5]',
    iconColor: 'text-[#10B981]',
  },
  {
    id: 'text',
    name: 'Text / Insight',
    desc: 'Executive summaries, conclusions, and notes',
    icon: FileText,
    wash: 'bg-[#EEF2FF]',
    iconColor: 'text-[#6366F1]',
  },
];

const ADVANCED_WIDGET_TYPES = [
  { id: 'gauge', name: 'Radial Gauge', desc: 'Progress against a target or quota' },
  { id: 'horizontal_bar', name: 'Horizontal Bar', desc: 'Long-label categorical comparisons' },
  { id: 'stacked_bar', name: 'Stacked Bar', desc: 'Composition across categories' },
  { id: 'grouped_bar', name: 'Grouped Bar', desc: 'Multi-series comparisons' },
  { id: 'heatmap', name: 'Heatmap', desc: '2D matrix intensity across two dimensions' },
  { id: 'histogram', name: 'Histogram', desc: 'Distribution frequency of values' },
  { id: 'funnel', name: 'Funnel Chart', desc: 'Step-by-step conversion drop-off' },
  { id: 'waterfall', name: 'Waterfall', desc: 'Incremental positive/negative changes' },
  { id: 'treemap', name: 'Treemap', desc: 'Nested area proportions' },
];

export const WidgetConfigModal: React.FC<WidgetConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  workspaceId,
  initialWidget,
  defaultWidgetType,
}) => {
  // Wizard Steps: 1 = Type, 2 = Data, 3 = Appearance
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Widget Core State
  const [widgetType, setWidgetType] = useState<string>(defaultWidgetType || 'kpi');
  const [showAdvancedTypes, setShowAdvancedTypes] = useState<boolean>(false);
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [gridW, setGridW] = useState<number>(6);
  const [gridH, setGridH] = useState<number>(4);

  // Dataset states
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [datasetColumns, setDatasetColumns] = useState<Array<{ name: string; data_type?: string }>>([]);
  const [loadingDatasets, setLoadingDatasets] = useState<boolean>(false);

  // Query config (Plain Language)
  const [metricColumn, setMetricColumn] = useState<string>('');
  const [aggregation, setAggregation] = useState<string>('sum');
  const [groupByColumn, setGroupByColumn] = useState<string>('');
  const [subGroupByColumn, setSubGroupByColumn] = useState<string>('');
  const [timeColumn, setTimeColumn] = useState<string>('');
  const [limit, setLimit] = useState<number>(10);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [textContent, setTextContent] = useState<string>('');

  // Appearance & Styling State
  const [colorPalette, setColorPalette] = useState<string>('ocean');
  const [customColor, setCustomColor] = useState<string>('');
  const [unit, setUnit] = useState<string>('₹');
  const [showLegend, setShowLegend] = useState<boolean>(true);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState<boolean>(false);

  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available datasets
  useEffect(() => {
    if (!isOpen || !workspaceId) return;

    const loadDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const res = await DatasetApi.list(workspaceId, { pageSize: 100 });
        const items = res.items || [];
        setDatasets(items);

        if (initialWidget) {
          // Editing existing widget: jump straight to Step 2 or 3
          setCurrentStep(2);
          setWidgetType(initialWidget.widget_type);
          setTitle(initialWidget.title);
          setDescription(initialWidget.description || '');
          setGridW(initialWidget.grid_w);
          setGridH(initialWidget.grid_h);
          setSelectedDatasetId(initialWidget.dataset_id || (items[0]?.id || ''));

          const qc = initialWidget.query_config || {};
          setMetricColumn(qc.metric_column || '');
          setAggregation(qc.aggregation || 'sum');
          setGroupByColumn(qc.group_by_column || '');
          setSubGroupByColumn(qc.sub_group_by_column || '');
          setTimeColumn(qc.time_column || '');
          setLimit(qc.limit || 10);
          setSortDirection(qc.sort_direction || 'desc');
          setTextContent(qc.text_content || '');

          const ds = initialWidget.display_settings || {};
          setColorPalette(ds.color_palette || 'ocean');
          setCustomColor(ds.custom_color || '');
          setUnit(ds.unit || '₹');
          setShowLegend(ds.show_legend !== false);
          setShowLabels(ds.show_labels !== false);
        } else {
          // Creating fresh widget
          setCurrentStep(1);
          setWidgetType(defaultWidgetType || 'kpi');
          setTitle('');
          setDescription('');
          setGridW(defaultWidgetType === 'kpi' ? 3 : 6);
          setGridH(defaultWidgetType === 'kpi' ? 3 : 4);
          setColorPalette('ocean');
          setCustomColor('');
          setUnit('₹');
          setShowLegend(true);
          setShowLabels(true);

          if (items.length > 0) {
            setSelectedDatasetId(items[0].id);
          }
        }
      } catch (err: any) {
        setError('Failed to load datasets.');
      } finally {
        setLoadingDatasets(false);
      }
    };

    loadDatasets();
  }, [isOpen, workspaceId, initialWidget, defaultWidgetType]);

  // Load columns when dataset selection changes
  useEffect(() => {
    if (!selectedDatasetId || !workspaceId) {
      setDatasetColumns([]);
      return;
    }

    const loadCols = async () => {
      try {
        const d = await DatasetApi.get(workspaceId, selectedDatasetId);
        const cols = d.columns || [];
        setDatasetColumns(cols);

        if (!initialWidget || initialWidget.dataset_id !== selectedDatasetId) {
          // Intelligent Column Auto-Detection
          const numCols = cols.filter((c: any) =>
            ['float', 'double', 'int', 'numeric', 'integer', 'number', 'real', 'decimal'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );
          const strCols = cols.filter((c: any) =>
            ['varchar', 'text', 'string', 'char'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );
          const dateCols = cols.filter((c: any) =>
            ['date', 'timestamp', 'time'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );

          if (numCols.length > 0) setMetricColumn(numCols[0].name);
          if (strCols.length > 0) {
            setGroupByColumn(strCols[0].name);
            if (strCols.length > 1) setSubGroupByColumn(strCols[1].name);
          }
          if (dateCols.length > 0) setTimeColumn(dateCols[0].name);

          // Auto-generate title
          const metricName = numCols[0]?.name ? numCols[0].name.replace(/_/g, ' ') : 'Metric';
          const capitalizedMetric = metricName.charAt(0).toUpperCase() + metricName.slice(1);
          if (widgetType === 'kpi') {
            setTitle(`Total ${capitalizedMetric}`);
          } else if (strCols[0]?.name) {
            const catName = strCols[0].name.replace(/_/g, ' ');
            const capitalizedCat = catName.charAt(0).toUpperCase() + catName.slice(1);
            setTitle(`${capitalizedMetric} by ${capitalizedCat}`);
          } else {
            setTitle(`${capitalizedMetric} Trend`);
          }
        }
      } catch (e) {
        // Fallback
      }
    };

    loadCols();
  }, [selectedDatasetId, workspaceId, initialWidget, widgetType]);

  // Derived categorized column lists
  const numericColumns = useMemo(() => {
    return datasetColumns.filter((c: any) =>
      ['float', 'double', 'int', 'numeric', 'integer', 'number', 'real', 'decimal'].some((t) =>
        (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
      )
    );
  }, [datasetColumns]);

  const categoricalColumns = useMemo(() => {
    return datasetColumns.filter((c: any) =>
      ['varchar', 'text', 'string', 'char'].some((t) =>
        (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
      )
    );
  }, [datasetColumns]);

  const dateColumns = useMemo(() => {
    return datasetColumns.filter((c: any) =>
      ['date', 'timestamp', 'time'].some((t) =>
        (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
      )
    );
  }, [datasetColumns]);

  // Handle Wizard Step Navigation
  const handleNext = () => {
    setError(null);
    if (currentStep === 1) {
      if (!widgetType) {
        setError('Please choose a widget type to continue.');
        return;
      }
      // If auto-title is empty, suggest one
      if (!title) {
        setTitle(
          widgetType === 'kpi'
            ? 'Total Sales'
            : widgetType === 'donut'
            ? 'Sales by Category'
            : widgetType === 'line'
            ? 'Monthly Trend'
            : 'Performance Overview'
        );
      }
      setCurrentStep(2);
    } else if (currentStep === 2) {
      if (widgetType !== 'text' && !selectedDatasetId) {
        setError('Please select a dataset to use for this widget.');
        return;
      }
      setCurrentStep(3);
    }
  };

  const handleBack = () => {
    setError(null);
    if (currentStep === 3) setCurrentStep(2);
    else if (currentStep === 2) setCurrentStep(1);
  };

  // Submit and Save
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Please provide a title for this widget.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const query_config: Record<string, any> = {
        aggregation,
        sort_direction: sortDirection,
        limit,
      };

      if (['kpi', 'gauge'].includes(widgetType)) {
        query_config.metric_column = metricColumn || undefined;
      } else if (['bar', 'donut', 'horizontal_bar', 'stacked_bar', 'grouped_bar', 'heatmap', 'treemap', 'funnel', 'waterfall'].includes(widgetType)) {
        query_config.group_by_column = groupByColumn || categoricalColumns[0]?.name;
        query_config.metric_column = metricColumn || numericColumns[0]?.name;
        if (subGroupByColumn) query_config.sub_group_by_column = subGroupByColumn;
      } else if (['line', 'area'].includes(widgetType)) {
        query_config.time_column = timeColumn || dateColumns[0]?.name;
        query_config.metric_column = metricColumn || numericColumns[0]?.name;
        query_config.granularity = 'month';
      } else if (widgetType === 'table') {
        query_config.limit = limit || 50;
        query_config.sort_column = metricColumn || undefined;
      } else if (widgetType === 'text') {
        query_config.text_content = textContent;
      }

      const display_settings: Record<string, any> = {
        unit: unit || '',
        color_palette: colorPalette,
        custom_color: customColor || undefined,
        show_legend: showLegend,
        show_labels: showLabels,
      };

      await onSave({
        widget_type: widgetType as any,
        title: title.trim(),
        description: description.trim() || undefined,
        dataset_id: widgetType === 'text' ? undefined : selectedDatasetId,
        grid_w: gridW,
        grid_h: gridH,
        query_config,
        display_settings,
      });

      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to save widget.');
    } finally {
      setSaving(false);
    }
  };

  // Mini Preview Mock Data
  const previewData = useMemo(() => {
    const metricName = metricColumn || 'Sales';
    if (widgetType === 'kpi') {
      return {
        value: '12,680',
        formatted_value: `${unit}12.68 L`,
        metric: title || `Total ${metricName}`,
        pct_change: 14.2,
      };
    } else if (widgetType === 'donut') {
      return {
        categories: ['West', 'North', 'South', 'East', 'Others'],
        values: [48, 24, 20, 12, 6],
        group_by: groupByColumn || 'Region',
      };
    } else if (widgetType === 'line' || widgetType === 'area') {
      return {
        points: [
          { timestamp: 'Jan', value: 380 },
          { timestamp: 'Feb', value: 580 },
          { timestamp: 'Mar', value: 510 },
          { timestamp: 'Apr', value: 680 },
          { timestamp: 'May', value: 890 },
          { timestamp: 'Jun', value: 810 },
          { timestamp: 'Jul', value: 1040 },
          { timestamp: 'Aug', value: 950 },
          { timestamp: 'Sep', value: 1250 },
          { timestamp: 'Oct', value: 1190 },
          { timestamp: 'Nov', value: 1380 },
          { timestamp: 'Dec', value: 1600 },
        ],
      };
    } else {
      return {
        categories: ['Category A', 'Category B', 'Category C', 'Category D'],
        values: [45, 78, 32, 64],
        group_by: groupByColumn || 'Category',
      };
    }
  }, [widgetType, title, metricColumn, groupByColumn, unit]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        initialWidget
          ? 'Edit Dashboard Widget'
          : `Create Widget: ${
              currentStep === 1
                ? 'Step 1 of 3: Choose What to Display'
                : currentStep === 2
                ? 'Step 2 of 3: Select Your Data'
                : 'Step 3 of 3: Customize Appearance'
            }`
      }
      maxWidth="xl"
    >
      <form onSubmit={handleSave} className="space-y-5">
        {/* Step Indicator Progress Bar */}
        <div className="flex items-center justify-between pb-3 border-b border-[#DCE5EB]">
          {[
            { step: 1, label: '1. Widget Type' },
            { step: 2, label: '2. Data & Metrics' },
            { step: 3, label: '3. Appearance & Style' },
          ].map((s) => (
            <button
              key={s.step}
              type="button"
              onClick={() => {
                // Allow clicking past steps or step 1
                if (s.step < currentStep || initialWidget) setCurrentStep(s.step as any);
              }}
              className={`flex items-center gap-2 text-xs font-bold transition-all cursor-pointer ${
                currentStep === s.step
                  ? 'text-[#009F98]'
                  : currentStep > s.step
                  ? 'text-[#102C46]'
                  : 'text-slate-400'
              }`}
            >
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  currentStep === s.step
                    ? 'bg-[#009F98] text-white shadow-xs'
                    : currentStep > s.step
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {currentStep > s.step ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : s.step}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
          ))}
        </div>

        {error && (
          <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838]">
            {error}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* STEP 1: CHOOSE WHAT TO DISPLAY */}
        {/* ------------------------------------------------------------- */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-bold text-[#102C46]">
                What type of visual do you want to create?
              </h3>
              <p className="text-xs text-[#52616C] mt-0.5">
                Select a visual presentation style. You can change your metrics and styling in the next steps.
              </p>
            </div>

            {/* Primary Visual Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {PRIMARY_WIDGET_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = widgetType === t.id;

                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      setWidgetType(t.id);
                      setGridW(t.id === 'kpi' ? 3 : 6);
                      setGridH(t.id === 'kpi' ? 3 : 4);
                    }}
                    className={`text-left p-3.5 rounded-2xl border-2 transition-all cursor-pointer relative flex flex-col justify-between ${
                      isSelected
                        ? 'border-[#009F98] ring-2 ring-[#009F98]/20 bg-[#EDF8F7]/30 shadow-xs'
                        : 'border-[#DCE5EB] hover:border-slate-300 hover:shadow-2xs bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center ${t.wash} ${t.iconColor}`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>
                      {isSelected && (
                        <span className="w-5 h-5 rounded-full bg-[#009F98] text-white flex items-center justify-center">
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </span>
                      )}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-[#102C46]">{t.name}</h4>
                      <p className="text-[11px] text-[#52616C] mt-1 leading-snug">{t.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Advanced Types Toggle */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowAdvancedTypes(!showAdvancedTypes)}
                className="text-xs font-bold text-[#009F98] hover:text-[#007D78] flex items-center gap-1.5 cursor-pointer"
              >
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${showAdvancedTypes ? 'rotate-180' : ''}`}
                />
                {showAdvancedTypes ? 'Hide additional chart types' : 'More chart types (Gauge, Funnel, Heatmap, Waterfall...)'}
              </button>

              {showAdvancedTypes && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mt-3 pt-3 border-t border-[#DCE5EB]">
                  {ADVANCED_WIDGET_TYPES.map((at) => (
                    <button
                      key={at.id}
                      type="button"
                      onClick={() => {
                        setWidgetType(at.id);
                        setGridW(6);
                        setGridH(4);
                      }}
                      className={`text-left p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        widgetType === at.id
                          ? 'border-[#009F98] bg-[#EDF8F7] font-bold text-[#009F98]'
                          : 'border-[#DCE5EB] hover:bg-slate-50 text-[#102C46]'
                      }`}
                    >
                      <div className="font-bold">{at.name}</div>
                      <div className="text-[10px] text-[#52616C] mt-0.5">{at.desc}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* STEP 2: SELECT YOUR DATA (BUSINESS-FRIENDLY QUESTIONS) */}
        {/* ------------------------------------------------------------- */}
        {currentStep === 2 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left 7 Columns: Friendly Questions */}
            <div className="lg:col-span-7 space-y-4">
              {/* Question 1: Dataset */}
              {widgetType !== 'text' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-[#102C46] flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-[#009F98]" />
                    Which dataset should we use?
                  </label>
                  <select
                    value={selectedDatasetId}
                    onChange={(e) => setSelectedDatasetId(e.target.value)}
                    className="w-full text-xs font-semibold px-3 py-2.5 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} {d.row_count ? `(${d.row_count.toLocaleString()} rows)` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Question 2: What do you want to measure? (Metric) */}
              {widgetType !== 'text' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-[#102C46]">
                      What do you want to measure?
                    </label>
                    <select
                      value={metricColumn}
                      onChange={(e) => setMetricColumn(e.target.value)}
                      className="w-full text-xs font-semibold px-3 py-2.5 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                    >
                      <option value="">(Select a numerical field)</option>
                      {numericColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name.replace(/_/g, ' ')}
                        </option>
                      ))}
                      {numericColumns.length === 0 &&
                        datasetColumns.map((c) => (
                          <option key={c.name} value={c.name}>
                            {c.name}
                          </option>
                        ))}
                    </select>
                  </div>

                  {/* Question 3: Calculation (Aggregation) */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-[#102C46]">
                      How should we calculate it?
                    </label>
                    <select
                      value={aggregation}
                      onChange={(e) => setAggregation(e.target.value)}
                      className="w-full text-xs font-semibold px-3 py-2.5 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                    >
                      <option value="sum">Sum (Total)</option>
                      <option value="avg">Average (Mean)</option>
                      <option value="count">Count of records</option>
                      <option value="count_distinct">Unique count</option>
                      <option value="min">Minimum</option>
                      <option value="max">Maximum</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Question 4: Dimension / Grouping (For charts) */}
              {['bar', 'donut', 'pie', 'horizontal_bar', 'stacked_bar', 'grouped_bar', 'heatmap', 'treemap'].includes(
                widgetType
              ) && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-[#102C46]">
                    What should we compare it by? (Categories)
                  </label>
                  <select
                    value={groupByColumn}
                    onChange={(e) => setGroupByColumn(e.target.value)}
                    className="w-full text-xs font-semibold px-3 py-2.5 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                  >
                    <option value="">(Select category or segment)</option>
                    {categoricalColumns.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name.replace(/_/g, ' ')}
                      </option>
                    ))}
                    {categoricalColumns.length === 0 &&
                      datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Time Dimension for Line/Area */}
              {['line', 'area'].includes(widgetType) && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-[#102C46]">
                    What date or time field shows the trend?
                  </label>
                  <select
                    value={timeColumn}
                    onChange={(e) => setTimeColumn(e.target.value)}
                    className="w-full text-xs font-semibold px-3 py-2.5 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                  >
                    <option value="">(Select date / timestamp)</option>
                    {dateColumns.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name.replace(/_/g, ' ')}
                      </option>
                    ))}
                    {dateColumns.length === 0 &&
                      datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Text Widget input */}
              {widgetType === 'text' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-[#102C46]">Insight / Commentary</label>
                  <textarea
                    rows={5}
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Enter executive insights, data commentary, or Markdown notes..."
                    className="w-full text-xs p-3 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                  />
                </div>
              )}
            </div>

            {/* Right 5 Columns: Real-Time Preview Card */}
            <div className="lg:col-span-5 bg-[#F5F8FA] rounded-2xl p-4 border border-[#DCE5EB]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-bold text-[#52616C] uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#009F98]" />
                  Live Visual Preview
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Sample Data</span>
              </div>

              <div className="bg-white rounded-xl p-3 border border-[#DCE5EB] shadow-2xs min-h-[160px] flex items-center justify-center">
                <WidgetVisualization
                  widgetType={widgetType}
                  data={previewData}
                  displaySettings={{
                    unit,
                    color_palette: colorPalette,
                    custom_color: customColor,
                  }}
                  height={150}
                />
              </div>

              <p className="text-[11px] text-[#52616C] mt-3 text-center">
                This preview updates in real-time as you refine calculations and appearance.
              </p>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* STEP 3: CUSTOMIZE APPEARANCE & STYLING */}
        {/* ------------------------------------------------------------- */}
        {currentStep === 3 && (
          <div className="space-y-5">
            {/* Widget Title & Subtitle */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#102C46]">Widget Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Sales by Region"
                  className="w-full text-xs font-semibold px-3 py-2 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#102C46]">Optional Subtitle</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Current Fiscal Year vs. Target"
                  className="w-full text-xs font-medium px-3 py-2 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                />
              </div>
            </div>

            {/* 7 Color Palettes */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-[#102C46]">
                Color Palette (7 Distinct Themes)
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {Object.values(COLOR_PALETTES).map((pal) => {
                  const isSelected = colorPalette === pal.id && !customColor;

                  return (
                    <button
                      key={pal.id}
                      type="button"
                      onClick={() => {
                        setColorPalette(pal.id);
                        setCustomColor('');
                      }}
                      className={`text-left p-2.5 rounded-xl border-2 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-[#009F98] bg-[#EDF8F7] shadow-xs'
                          : 'border-[#DCE5EB] hover:border-slate-300 bg-white'
                      }`}
                    >
                      <div className="flex items-center gap-1 mb-1.5">
                        {pal.colors.slice(0, 4).map((c, i) => (
                          <span
                            key={i}
                            className="w-3.5 h-3.5 rounded-full border border-black/10 shadow-2xs"
                            style={{ backgroundColor: c }}
                          />
                        ))}
                      </div>
                      <div className="text-xs font-bold text-[#102C46] flex items-center justify-between">
                        <span>{pal.name.split(' ')[0]}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#009F98]" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Custom Accent Color & Display Format */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              {/* Custom Accent Color */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#102C46]">
                  Custom Accent Color (Optional)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={customColor || '#009F98'}
                    onChange={(e) => setCustomColor(e.target.value)}
                    className="w-9 h-9 rounded-lg border border-[#DCE5EB] p-0.5 cursor-pointer bg-white"
                  />
                  <input
                    type="text"
                    value={customColor}
                    onChange={(e) => setCustomColor(e.target.value)}
                    placeholder="#009F98 or leave blank"
                    className="flex-1 text-xs px-3 py-2 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] font-mono"
                  />
                </div>
              </div>

              {/* Number Format / Unit */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#102C46]">Number Format / Unit</label>
                <select
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full text-xs font-semibold px-3 py-2 bg-white border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] cursor-pointer"
                >
                  <option value="₹">Indian Rupee (₹)</option>
                  <option value="$">US Dollar ($)</option>
                  <option value="€">Euro (€)</option>
                  <option value="%">Percentage (%)</option>
                  <option value="">Plain Number (no unit)</option>
                </select>
              </div>
            </div>

            {/* Display Toggles */}
            <div className="flex items-center gap-6 pt-2 border-t border-[#DCE5EB]">
              <label className="flex items-center gap-2 text-xs font-semibold text-[#102C46] cursor-pointer">
                <input
                  type="checkbox"
                  checked={showLegend}
                  onChange={(e) => setShowLegend(e.target.checked)}
                  className="w-4 h-4 rounded text-[#009F98] focus:ring-[#009F98] accent-[#009F98]"
                />
                Show Legend
              </label>

              <label className="flex items-center gap-2 text-xs font-semibold text-[#102C46] cursor-pointer">
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  className="w-4 h-4 rounded text-[#009F98] focus:ring-[#009F98] accent-[#009F98]"
                />
                Show Data Labels
              </label>
            </div>

            {/* Collapsible Advanced Technical Settings */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                className="text-xs font-bold text-[#52616C] hover:text-[#102C46] flex items-center gap-1.5 cursor-pointer"
              >
                <ChevronDown
                  className={`w-3.5 h-3.5 transition-transform ${showAdvancedSettings ? 'rotate-180' : ''}`}
                />
                {showAdvancedSettings ? 'Hide Advanced Settings' : 'Advanced Settings (Sorting, Limit, Dimensions)'}
              </button>

              {showAdvancedSettings && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 mt-2 bg-[#F5F8FA] rounded-xl border border-[#DCE5EB] text-xs">
                  <div className="space-y-1">
                    <label className="font-semibold text-[#102C46]">Max Categories / Limit</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={limit}
                      onChange={(e) => setLimit(Number(e.target.value) || 10)}
                      className="w-full text-xs p-2 bg-white border border-[#DCE5EB] rounded-lg"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-[#102C46]">Sort Order</label>
                    <select
                      value={sortDirection}
                      onChange={(e) => setSortDirection(e.target.value as any)}
                      className="w-full text-xs p-2 bg-white border border-[#DCE5EB] rounded-lg"
                    >
                      <option value="desc">Highest First (Descending)</option>
                      <option value="asc">Lowest First (Ascending)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-[#102C46]">Grid Width (Cols)</label>
                    <select
                      value={gridW}
                      onChange={(e) => setGridW(Number(e.target.value))}
                      className="w-full text-xs p-2 bg-white border border-[#DCE5EB] rounded-lg"
                    >
                      <option value={3}>1/4 Width (3 cols)</option>
                      <option value={4}>1/3 Width (4 cols)</option>
                      <option value={6}>1/2 Width (6 cols)</option>
                      <option value={12}>Full Width (12 cols)</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* FOOTER ACTIONS */}
        {/* ------------------------------------------------------------- */}
        <div className="pt-4 border-t border-[#DCE5EB] flex items-center justify-between">
          <div>
            {currentStep > 1 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleBack}
                leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
              >
                Back
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>

            {currentStep < 3 ? (
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={handleNext}
                rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
              >
                Next Step
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={saving}
                leftIcon={<Save className="w-3.5 h-3.5" />}
              >
                {initialWidget ? 'Update Widget' : 'Add to Dashboard'}
              </Button>
            )}
          </div>
        </div>
      </form>
    </Modal>
  );
};
