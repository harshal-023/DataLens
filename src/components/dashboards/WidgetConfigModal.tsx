import React, { useState, useEffect } from 'react';
import {
  Hash,
  BarChart3,
  LineChart as LineIcon,
  AreaChart as AreaIcon,
  PieChart as PieIcon,
  ScatterChart as ScatterIcon,
  Table as TableIcon,
  FileText,
  Save,
  Database,
  Layers,
  Gauge as GaugeIcon,
  Sliders,
  TrendingUp,
  Activity,
  GitCommit,
  Filter,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { DashboardWidget } from '../../services/dashboardService';
import { DatasetApi } from '../../services/apiClient';

export interface WidgetConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (widgetData: Partial<DashboardWidget>) => Promise<void>;
  workspaceId: string;
  initialWidget?: DashboardWidget | null;
}

interface WidgetTypeOption {
  id: string;
  category: 'Summary' | 'Bar' | 'Time Series' | 'Statistical' | 'Business' | 'Standard';
  label: string;
  desc: string;
}

const WIDGET_TYPE_OPTIONS: WidgetTypeOption[] = [
  // Summary
  { id: 'kpi', category: 'Summary', label: 'KPI Metric', desc: 'Single headline summary with optional target comparison' },
  { id: 'gauge', category: 'Summary', label: 'Gauge & Target', desc: 'Radial gauge measuring progress against target' },

  // Bar Charts
  { id: 'bar', category: 'Bar', label: 'Bar Chart', desc: 'Categorical distribution and rankings' },
  { id: 'stacked_bar', category: 'Bar', label: 'Stacked Bar', desc: 'Segment composition across categories' },
  { id: 'grouped_bar', category: 'Bar', label: 'Grouped Bar', desc: 'Side-by-side multi-metric or multi-series comparison' },
  { id: 'horizontal_bar', category: 'Bar', label: 'Horizontal Bar', desc: 'Long-label categorical ranking and comparisons' },
  { id: 'percent_bar', category: 'Bar', label: '100% Stacked Bar', desc: 'Normalized percentage composition per category' },
  { id: 'top_n', category: 'Bar', label: 'Top-N Ranking', desc: 'Ranked top performers with highlighted contrast' },

  // Time Series
  { id: 'line', category: 'Time Series', label: 'Line Chart', desc: 'Continuous time-series trend' },
  { id: 'multi_line', category: 'Time Series', label: 'Multi-Line', desc: 'Multiple trend lines comparing series or categories' },
  { id: 'area', category: 'Time Series', label: 'Area Chart', desc: 'Volume and magnitude over time' },
  { id: 'stacked_area', category: 'Time Series', label: 'Stacked Area', desc: 'Cumulative volume breakdown over time' },
  { id: 'combo', category: 'Time Series', label: 'Combo Chart', desc: 'Dual-axis Bar (volume) and Line (trend)' },

  // Statistical
  { id: 'heatmap', category: 'Statistical', label: 'Heatmap', desc: '2D matrix intensity across two dimensions' },
  { id: 'histogram', category: 'Statistical', label: 'Histogram', desc: 'Distribution frequency across numerical bins' },
  { id: 'box_plot', category: 'Statistical', label: 'Box Plot', desc: 'Five-number statistical summary (IQR, median, outliers)' },
  { id: 'correlation', category: 'Statistical', label: 'Correlation Matrix', desc: 'Pearson correlation matrix across numerical variables' },

  // Business
  { id: 'treemap', category: 'Business', label: 'Treemap', desc: 'Nested rectangular proportional area breakdown' },
  { id: 'waterfall', category: 'Business', label: 'Waterfall', desc: 'Sequential positive & negative breakdown analysis' },
  { id: 'funnel', category: 'Business', label: 'Funnel Chart', desc: 'Stage-by-stage pipeline conversion & drop-off' },
  { id: 'pareto', category: 'Business', label: 'Pareto 80/20', desc: 'Combined frequency bars and cumulative percentage curve' },

  // Standard
  { id: 'donut', category: 'Standard', label: 'Donut / Pie', desc: 'Proportional categorical composition' },
  { id: 'scatter', category: 'Standard', label: 'Scatter Plot', desc: 'Correlation and distribution between two metrics' },
  { id: 'table', category: 'Standard', label: 'Data Table', desc: 'Tabular records and raw data view' },
  { id: 'text', category: 'Standard', label: 'Text / Markdown', desc: 'Documentation, annotations, and executive notes' },
];

const CATEGORIES = ['All', 'Summary', 'Bar', 'Time Series', 'Statistical', 'Business', 'Standard'] as const;

export const WidgetConfigModal: React.FC<WidgetConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  workspaceId,
  initialWidget,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [widgetType, setWidgetType] = useState<string>('bar');
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [gridW, setGridW] = useState<number>(6);
  const [gridH, setGridH] = useState<number>(4);

  // Dataset states
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [datasetColumns, setDatasetColumns] = useState<Array<{ name: string; data_type?: string }>>([]);
  const [loadingDatasets, setLoadingDatasets] = useState<boolean>(false);

  // Query config
  const [metricColumn, setMetricColumn] = useState<string>('');
  const [groupByColumn, setGroupByColumn] = useState<string>('');
  const [subGroupByColumn, setSubGroupByColumn] = useState<string>('');
  const [timeColumn, setTimeColumn] = useState<string>('');
  const [xColumn, setXColumn] = useState<string>('');
  const [yColumn, setYColumn] = useState<string>('');
  const [aggregation, setAggregation] = useState<string>('sum');
  const [granularity, setGranularity] = useState<string>('month');
  const [limit, setLimit] = useState<number>(10);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [bins, setBins] = useState<number>(10);
  const [textContent, setTextContent] = useState<string>('');

  // Drill-down & Comparative config
  const [hierarchyLevelsStr, setHierarchyLevelsStr] = useState<string>('');
  const [targetValue, setTargetValue] = useState<string>('');
  const [compareTo, setCompareTo] = useState<string>('none');
  const [unit, setUnit] = useState<string>('');

  // Annotations
  const [annotationValue, setAnnotationValue] = useState<string>('');
  const [annotationLabel, setAnnotationLabel] = useState<string>('');

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

        // Prepopulate if editing
        if (initialWidget) {
          setWidgetType(initialWidget.widget_type);
          setTitle(initialWidget.title);
          setDescription(initialWidget.description || '');
          setGridW(initialWidget.grid_w);
          setGridH(initialWidget.grid_h);
          setSelectedDatasetId(initialWidget.dataset_id || '');

          const qc = initialWidget.query_config || {};
          setMetricColumn(qc.metric_column || '');
          setGroupByColumn(qc.group_by_column || '');
          setSubGroupByColumn(qc.sub_group_by_column || '');
          setTimeColumn(qc.time_column || '');
          setXColumn(qc.x_column || '');
          setYColumn(qc.y_column || '');
          setAggregation(qc.aggregation || 'sum');
          setGranularity(qc.granularity || 'month');
          setLimit(qc.limit || 10);
          setSortDirection(qc.sort_direction || 'desc');
          setBins(qc.bins || 10);
          setTextContent(qc.text_content || '');

          if (Array.isArray(qc.hierarchy_levels)) {
            setHierarchyLevelsStr(qc.hierarchy_levels.join(', '));
          } else {
            setHierarchyLevelsStr('');
          }

          if (qc.target_value !== undefined && qc.target_value !== null) {
            setTargetValue(String(qc.target_value));
          } else {
            setTargetValue('');
          }
          setCompareTo(qc.compare_to || 'none');

          const ds = initialWidget.display_settings || {};
          setUnit(ds.unit || '');

          if (Array.isArray(ds.annotations) && ds.annotations.length > 0) {
            setAnnotationValue(String(ds.annotations[0].value));
            setAnnotationLabel(ds.annotations[0].label || '');
          } else {
            setAnnotationValue('');
            setAnnotationLabel('');
          }
        } else if (items.length > 0) {
          setSelectedDatasetId(items[0].id);
          setTitle('New Analytical Widget');
        }
      } catch (err: any) {
        setError('Failed to load datasets.');
      } finally {
        setLoadingDatasets(false);
      }
    };

    loadDatasets();
  }, [isOpen, workspaceId, initialWidget]);

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
          const numCol = cols.find((c: any) =>
            ['float', 'double', 'int', 'numeric', 'integer', 'number'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );
          const strCol = cols.find((c: any) =>
            ['varchar', 'text', 'string'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );
          const dateCol = cols.find((c: any) =>
            ['date', 'timestamp', 'time'].some((t) =>
              (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
            )
          );

          if (numCol) setMetricColumn(numCol.name);
          if (strCol) {
            setGroupByColumn(strCol.name);
            const otherStrCol = cols.find((c: any) => c.name !== strCol.name && ['varchar', 'text', 'string'].some((t) => (c.data_type || c.inferred_type || '').toLowerCase().includes(t)));
            if (otherStrCol) setSubGroupByColumn(otherStrCol.name);
          }
          if (dateCol) setTimeColumn(dateCol.name);
          if (numCol && cols.length > 1) {
            setXColumn(strCol ? strCol.name : cols[0].name);
            setYColumn(numCol.name);
          }
        }
      } catch (e) {
        // Fallback
      }
    };

    loadCols();
  }, [selectedDatasetId, workspaceId, initialWidget]);

  // Filter types by selected category
  const filteredTypes = WIDGET_TYPE_OPTIONS.filter(
    (t) => selectedCategory === 'All' || t.category === selectedCategory
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Please provide a widget title.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const query_config: Record<string, any> = {};

      // Parse hierarchy levels if provided
      const parsedHierarchy = hierarchyLevelsStr
        ? hierarchyLevelsStr
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
      if (parsedHierarchy.length > 0) {
        query_config.hierarchy_levels = parsedHierarchy;
      }

      // Target value & comparison
      if (targetValue.trim() !== '' && !isNaN(Number(targetValue))) {
        query_config.target_value = Number(targetValue);
      }
      if (compareTo !== 'none') {
        query_config.compare_to = compareTo;
      }

      // Configure based on widget family
      if (['kpi', 'gauge'].includes(widgetType)) {
        query_config.metric_column = metricColumn || undefined;
        query_config.aggregation = aggregation;
      } else if (
        [
          'bar',
          'donut',
          'pie',
          'stacked_bar',
          'grouped_bar',
          'horizontal_bar',
          'percent_bar',
          'top_n',
          'pareto',
          'waterfall',
          'funnel',
          'treemap',
        ].includes(widgetType)
      ) {
        query_config.group_by_column = groupByColumn;
        query_config.metric_column = metricColumn || undefined;
        query_config.aggregation = aggregation;
        query_config.sort_direction = sortDirection;
        query_config.limit = limit;

        if (
          ['stacked_bar', 'grouped_bar', 'percent_bar', 'treemap'].includes(widgetType) &&
          subGroupByColumn
        ) {
          query_config.sub_group_by_column = subGroupByColumn;
        }
      } else if (
        ['line', 'area', 'multi_line', 'stacked_area', 'combo'].includes(widgetType)
      ) {
        query_config.time_column = timeColumn;
        query_config.metric_column = metricColumn || undefined;
        query_config.aggregation = aggregation;
        query_config.granularity = granularity;
        if (['multi_line', 'stacked_area', 'combo'].includes(widgetType) && subGroupByColumn) {
          query_config.sub_group_by_column = subGroupByColumn;
        }
      } else if (widgetType === 'heatmap') {
        query_config.group_by_column = groupByColumn;
        query_config.sub_group_by_column = subGroupByColumn || groupByColumn;
        query_config.metric_column = metricColumn || undefined;
        query_config.aggregation = aggregation;
      } else if (widgetType === 'histogram') {
        query_config.metric_column = metricColumn;
        query_config.bins = bins || 10;
      } else if (widgetType === 'box_plot') {
        query_config.metric_column = metricColumn;
        query_config.group_by_column = groupByColumn || undefined;
      } else if (widgetType === 'correlation') {
        query_config.limit = limit;
      } else if (widgetType === 'scatter') {
        query_config.x_column = xColumn;
        query_config.y_column = yColumn;
        query_config.limit = 200;
      } else if (widgetType === 'table') {
        query_config.limit = 50;
        query_config.sort_column = metricColumn || undefined;
        query_config.sort_direction = sortDirection;
      } else if (widgetType === 'text') {
        query_config.text_content = textContent;
      }

      // Display settings & Annotations
      const display_settings: Record<string, any> = {
        unit: unit || undefined,
        theme: 'teal',
      };

      if (annotationValue.trim() !== '' && !isNaN(Number(annotationValue))) {
        display_settings.annotations = [
          {
            value: Number(annotationValue),
            label: annotationLabel.trim() || 'Threshold',
            color: '#E05D52',
          },
        ];
      }

      await onSave({
        widget_type: widgetType as any,
        title: title.trim(),
        description: description.trim() || null,
        dataset_id: widgetType !== 'text' ? selectedDatasetId : null,
        grid_w: gridW,
        grid_h: gridH,
        query_config,
        display_settings,
      });

      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to save widget configuration.');
    } finally {
      setSaving(false);
    }
  };

  const needsSubGroupBy = [
    'stacked_bar',
    'grouped_bar',
    'percent_bar',
    'multi_line',
    'stacked_area',
    'combo',
    'heatmap',
    'treemap',
  ].includes(widgetType);

  const supportsDrillDown = [
    'bar',
    'stacked_bar',
    'grouped_bar',
    'horizontal_bar',
    'percent_bar',
    'donut',
    'treemap',
  ].includes(widgetType);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialWidget ? 'Configure Dashboard Widget' : 'Add Visualization Widget'}
      subtitle="Select an advanced chart type, bind dataset dimensions, and customize interactions."
      maxWidth="4xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6 pt-2">
        {error && (
          <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838] font-medium">
            {error}
          </div>
        )}

        {/* 1. Category Tabs & Visualization Type Selector */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <label className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
              1. Choose Chart Type
            </label>
            <div className="flex items-center gap-1 overflow-x-auto pb-1 max-w-full">
              {CATEGORIES.map((cat) => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
                    selectedCategory === cat
                      ? 'bg-[#102C46] text-white shadow-2xs'
                      : 'bg-[#F5F8FA] text-[#52616C] hover:bg-[#EBF1F5] hover:text-[#102C46]'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5 max-h-56 overflow-y-auto pr-1">
            {filteredTypes.map((t) => {
              const isSelected = widgetType === t.id;
              return (
                <button
                  type="button"
                  key={t.id}
                  onClick={() => setWidgetType(t.id)}
                  className={`flex flex-col items-start p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    isSelected
                      ? 'border-[#009F98] bg-[#EDF7FA] text-[#007D78] shadow-xs ring-2 ring-[#009F98]/20'
                      : 'border-[#DCE5EB] bg-white text-[#52616C] hover:border-[#BBDCE8] hover:bg-[#F5F8FA]'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <span className="text-xs font-bold text-[#102C46] leading-tight truncate">
                      {t.label}
                    </span>
                    <span className="text-[9px] font-bold uppercase tracking-wider text-[#009F98] bg-white px-1.5 py-0.5 rounded border border-[#BBDCE8]/50">
                      {t.category}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#52616C] line-clamp-2 leading-relaxed">
                    {t.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. General Information */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Widget Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Regional Revenue by Product Category"
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Subtitle / Context (Optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Click bar segments to filter or drill down"
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
            />
          </div>
        </div>

        {/* 3. Dataset Connection & Field Mapping */}
        {widgetType !== 'text' ? (
          <div className="bg-[#F5F8FA] p-4 rounded-xl border border-[#DCE5EB] space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-[#102C46] uppercase tracking-wider">
                <Database className="w-4 h-4 text-[#009F98]" />
                <span>Dataset & Query Mapping</span>
              </div>
              <span className="text-[11px] text-[#52616C]">
                Configuring: <strong className="text-[#009F98]">{WIDGET_TYPE_OPTIONS.find((o) => o.id === widgetType)?.label}</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Source Dataset
                </label>
                <select
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  disabled={loadingDatasets}
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40 font-medium"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.row_count?.toLocaleString()} rows)
                    </option>
                  ))}
                </select>
              </div>

              {/* Metric Column & Math Aggregation */}
              {!['table', 'correlation'].includes(widgetType) && (
                <div>
                  <label className="block text-xs font-medium text-[#52616C] mb-1">
                    Metric Column & Math
                  </label>
                  <div className="flex gap-2">
                    <select
                      value={metricColumn}
                      onChange={(e) => setMetricColumn(e.target.value)}
                      className="flex-1 px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40 font-medium"
                    >
                      <option value="">(Count rows)</option>
                      {datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name} {c.data_type ? `[${c.data_type}]` : ''}
                        </option>
                      ))}
                    </select>

                    <select
                      value={aggregation}
                      onChange={(e) => setAggregation(e.target.value)}
                      className="w-24 px-2 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none font-bold"
                    >
                      <option value="sum">SUM</option>
                      <option value="avg">AVG</option>
                      <option value="count">COUNT</option>
                      <option value="min">MIN</option>
                      <option value="max">MAX</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Categorical & Dimension Bindings */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-[#DCE5EB]">
              {/* Group By Category */}
              {[
                'bar',
                'donut',
                'pie',
                'stacked_bar',
                'grouped_bar',
                'horizontal_bar',
                'percent_bar',
                'top_n',
                'pareto',
                'waterfall',
                'funnel',
                'treemap',
                'heatmap',
                'box_plot',
              ].includes(widgetType) && (
                <div>
                  <label className="block text-xs font-medium text-[#52616C] mb-1">
                    Primary Dimension / Category
                  </label>
                  <select
                    value={groupByColumn}
                    onChange={(e) => setGroupByColumn(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40 font-medium"
                  >
                    <option value="">(Select category column)</option>
                    {datasetColumns.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Secondary Sub-Group / Series Dimension */}
              {needsSubGroupBy && (
                <div>
                  <label className="block text-xs font-medium text-[#52616C] mb-1">
                    Secondary Series / Stack Dimension
                  </label>
                  <select
                    value={subGroupByColumn}
                    onChange={(e) => setSubGroupByColumn(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40 font-medium"
                  >
                    <option value="">(None / Single series)</option>
                    {datasetColumns.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Time Series Specific */}
              {['line', 'area', 'multi_line', 'stacked_area', 'combo'].includes(widgetType) && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      Timestamp / Date Column
                    </label>
                    <select
                      value={timeColumn}
                      onChange={(e) => setTimeColumn(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none font-medium"
                    >
                      {datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      Time Interval
                    </label>
                    <select
                      value={granularity}
                      onChange={(e) => setGranularity(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none font-medium"
                    >
                      <option value="day">Daily</option>
                      <option value="week">Weekly</option>
                      <option value="month">Monthly</option>
                      <option value="quarter">Quarterly</option>
                      <option value="year">Yearly</option>
                    </select>
                  </div>
                </>
              )}

              {/* Histogram Bins */}
              {widgetType === 'histogram' && (
                <div>
                  <label className="block text-xs font-medium text-[#52616C] mb-1">
                    Number of Bins
                  </label>
                  <input
                    type="number"
                    min="3"
                    max="50"
                    value={bins}
                    onChange={(e) => setBins(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-bold"
                  />
                </div>
              )}

              {/* Scatter Plot Coordinates */}
              {widgetType === 'scatter' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      X Axis (Horizontal)
                    </label>
                    <select
                      value={xColumn}
                      onChange={(e) => setXColumn(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-medium"
                    >
                      {datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      Y Axis (Vertical)
                    </label>
                    <select
                      value={yColumn}
                      onChange={(e) => setYColumn(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-medium"
                    >
                      {datasetColumns.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {/* Top-N & Sort options */}
              {['bar', 'donut', 'pie', 'horizontal_bar', 'top_n'].includes(widgetType) && (
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      Sort Direction
                    </label>
                    <select
                      value={sortDirection}
                      onChange={(e) => setSortDirection(e.target.value as any)}
                      className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none font-medium"
                    >
                      <option value="desc">Highest First (DESC)</option>
                      <option value="asc">Lowest First (ASC)</option>
                    </select>
                  </div>
                  <div className="w-24">
                    <label className="block text-xs font-medium text-[#52616C] mb-1">
                      Limit
                    </label>
                    <input
                      type="number"
                      min="3"
                      max="100"
                      value={limit}
                      onChange={(e) => setLimit(Number(e.target.value))}
                      className="w-full px-2 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] text-center font-bold"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Drill-down Hierarchy (if supported) */}
            {supportsDrillDown && (
              <div className="pt-2 border-t border-[#DCE5EB]">
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Hierarchical Drill-Down Levels (Comma-separated column names in order)
                </label>
                <input
                  type="text"
                  value={hierarchyLevelsStr}
                  onChange={(e) => setHierarchyLevelsStr(e.target.value)}
                  placeholder="e.g. Region, Country, City   or   Category, Subcategory"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
                />
                <span className="text-[10px] text-[#52616C] mt-1 block">
                  Enables click-to-drill interactivity. Clicking an element drills into the next lower level.
                </span>
              </div>
            )}

            {/* Target Value & Comparative Analysis */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-[#DCE5EB]">
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Target / Benchmark Value
                </label>
                <input
                  type="number"
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                  placeholder="e.g. 1000000"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-semibold"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Comparison Mode
                </label>
                <select
                  value={compareTo}
                  onChange={(e) => setCompareTo(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-medium"
                >
                  <option value="none">No Comparison</option>
                  <option value="target">Target vs Actual</option>
                  <option value="prior_period">Period-over-Period (MoM)</option>
                  <option value="yoy">Year-over-Year (YoY)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Display Unit / Currency
                </label>
                <input
                  type="text"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="e.g. $, €, %, units"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
                />
              </div>
            </div>

            {/* Threshold Reference Annotation */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-[#DCE5EB]">
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Threshold Reference Line (Value)
                </label>
                <input
                  type="number"
                  value={annotationValue}
                  onChange={(e) => setAnnotationValue(e.target.value)}
                  placeholder="e.g. 80"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#52616C] mb-1">
                  Threshold Label
                </label>
                <input
                  type="text"
                  value={annotationLabel}
                  onChange={(e) => setAnnotationLabel(e.target.value)}
                  placeholder="e.g. 80% SLA Target"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
                />
              </div>
            </div>
          </div>
        ) : (
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Text / Markdown Content
            </label>
            <textarea
              rows={5}
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Enter executive summary, instructions, or findings..."
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40 font-mono"
            />
          </div>
        )}

        {/* 4. Layout Dimensions */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-[#52616C] mb-1">
              Grid Width (Columns out of 12)
            </label>
            <select
              value={gridW}
              onChange={(e) => setGridW(Number(e.target.value))}
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-semibold"
            >
              <option value={3}>3 Columns (Quarter width)</option>
              <option value={4}>4 Columns (One-third width)</option>
              <option value={6}>6 Columns (Half width)</option>
              <option value={8}>8 Columns (Two-thirds width)</option>
              <option value={12}>12 Columns (Full width)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#52616C] mb-1">
              Grid Height (Row blocks)
            </label>
            <select
              value={gridH}
              onChange={(e) => setGridH(Number(e.target.value))}
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-semibold"
            >
              <option value={3}>Small (3 rows)</option>
              <option value={4}>Medium (4 rows)</option>
              <option value={6}>Large (6 rows)</option>
              <option value={8}>Extra Large (8 rows)</option>
            </select>
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#DCE5EB]">
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={saving}
            leftIcon={<Save className="w-4 h-4" />}
          >
            {initialWidget ? 'Update Widget' : 'Add Widget'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
