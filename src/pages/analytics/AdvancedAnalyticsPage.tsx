import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Users,
  History,
  Play,
  Download,
  Info,
  RefreshCw,
  Brain,
  Sliders,
  Database,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import {
  DatasetApi,
  MlApi,
  AnomalyDetectResponse,
  ForecastResponse,
  SegmentationResponse,
  ModelRunListItem,
  ModelRunDetailResponse,
  InsightResponse,
} from '../../services/apiClient';

export const AdvancedAnalyticsPage: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  // Active Tab
  const [activeTab, setActiveTab] = useState<'anomaly' | 'forecast' | 'segmentation' | 'runs'>('anomaly');

  // Datasets State
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [selectedDatasetDetail, setSelectedDatasetDetail] = useState<any | null>(null);
  const [loadingDatasets, setLoadingDatasets] = useState<boolean>(false);

  // Available Columns
  const [numericColumns, setNumericColumns] = useState<string[]>([]);
  const [dateColumns, setDateColumns] = useState<string[]>([]);

  // -------------------------------------------------------------------------
  // ANOMALY DETECTION STATE
  // -------------------------------------------------------------------------
  const [anomalyTargetCol, setAnomalyTargetCol] = useState<string>('');
  const [anomalyTimeCol, setAnomalyTimeCol] = useState<string>('');
  const [anomalyAlgorithm, setAnomalyAlgorithm] = useState<'z_score' | 'iqr' | 'isolation_forest'>('z_score');
  const [anomalySensitivity, setAnomalySensitivity] = useState<number>(2.5);
  const [anomalyLoading, setAnomalyLoading] = useState<boolean>(false);
  const [anomalyResult, setAnomalyResult] = useState<AnomalyDetectResponse | null>(null);
  const [anomalyError, setAnomalyError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // FORECASTING STATE
  // -------------------------------------------------------------------------
  const [forecastTargetCol, setForecastTargetCol] = useState<string>('');
  const [forecastTimeCol, setForecastTimeCol] = useState<string>('');
  const [forecastHorizon, setForecastHorizon] = useState<number>(6);
  const [forecastAlgorithm, setForecastAlgorithm] = useState<'exponential_smoothing' | 'moving_average' | 'seasonal_naive' | 'linear_trend'>('exponential_smoothing');
  const [forecastConfidence, setForecastConfidence] = useState<number>(0.95);
  const [forecastSeasonality, setForecastSeasonality] = useState<number | undefined>(undefined);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [forecastResult, setForecastResult] = useState<ForecastResponse | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // SEGMENTATION STATE
  // -------------------------------------------------------------------------
  const [segmentFeatures, setSegmentFeatures] = useState<string[]>([]);
  const [segmentAlgorithm, setSegmentAlgorithm] = useState<'kmeans' | 'hierarchical'>('kmeans');
  const [segmentK, setSegmentK] = useState<number>(3);
  const [segmentScale, setSegmentScale] = useState<boolean>(true);
  const [segmentLoading, setSegmentLoading] = useState<boolean>(false);
  const [segmentResult, setSegmentResult] = useState<SegmentationResponse | null>(null);
  const [segmentError, setSegmentError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // MODEL RUNS & REGISTRY STATE
  // -------------------------------------------------------------------------
  const [modelRuns, setModelRuns] = useState<ModelRunListItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState<boolean>(false);
  const [selectedRunDetail, setSelectedRunDetail] = useState<ModelRunDetailResponse | null>(null);
  const [runDetailOpen, setRunDetailOpen] = useState<boolean>(false);
  const [generatingInsight, setGeneratingInsight] = useState<boolean>(false);
  const [runInsight, setRunInsight] = useState<InsightResponse | null>(null);
  const [exportingReport, setExportingReport] = useState<string | null>(null);

  // 1. Load Datasets on workspace change
  useEffect(() => {
    if (!workspaceId) return;
    loadDatasets();
    loadRuns();
  }, [workspaceId]);

  const loadDatasets = async () => {
    if (!workspaceId) return;
    setLoadingDatasets(true);
    try {
      const res = await DatasetApi.list(workspaceId, { pageSize: 50 });
      const items = res?.items || [];
      setDatasets(items);
      if (items.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(items[0].id);
      }
    } catch (e: any) {
      console.error('Failed to load datasets for ML:', e);
    } finally {
      setLoadingDatasets(false);
    }
  };

  const loadRuns = async () => {
    if (!workspaceId) return;
    setLoadingRuns(true);
    try {
      const runs = await MlApi.listModelRuns(workspaceId);
      setModelRuns(runs);
    } catch (e: any) {
      console.error('Failed to load model runs:', e);
    } finally {
      setLoadingRuns(false);
    }
  };

  // 2. Load Columns when Selected Dataset Changes
  useEffect(() => {
    if (!workspaceId || !selectedDatasetId) return;
    loadDatasetColumns(selectedDatasetId);
  }, [workspaceId, selectedDatasetId]);

  const loadDatasetColumns = async (datasetId: string) => {
    try {
      const ds = await DatasetApi.get(workspaceId, datasetId);
      setSelectedDatasetDetail(ds);

      const cols = ds.columns || ds.schema_metadata?.columns || [];
      const numCols: string[] = [];
      const dtCols: string[] = [];

      cols.forEach((c: any) => {
        const colName = c.name || c.column_name || c;
        const colType = (c.inferred_type || c.type || '').toLowerCase();
        if (colType === 'numeric' || colType === 'number' || colType === 'integer' || colType === 'float') {
          numCols.push(colName);
        } else if (colType === 'date' || colType === 'timestamp' || colType === 'datetime') {
          dtCols.push(colName);
        } else {
          // If type unknown, inspect name hints
          const lower = colName.toLowerCase();
          if (lower.includes('date') || lower.includes('time') || lower.includes('day') || lower.includes('month') || lower.includes('year')) {
            dtCols.push(colName);
          } else if (lower.includes('amount') || lower.includes('sales') || lower.includes('price') || lower.includes('qty') || lower.includes('revenue') || lower.includes('cost') || lower.includes('count')) {
            numCols.push(colName);
          }
        }
      });

      // If no numeric detected by metadata, fallback to all columns
      if (numCols.length === 0 && cols.length > 0) {
        cols.forEach((c: any) => numCols.push(c.name || c));
      }

      setNumericColumns(numCols);
      setDateColumns(dtCols);

      if (numCols.length > 0) {
        setAnomalyTargetCol(numCols[0]);
        setForecastTargetCol(numCols[0]);
        setSegmentFeatures(numCols.slice(0, Math.min(3, numCols.length)));
      }
      if (dtCols.length > 0) {
        setAnomalyTimeCol(dtCols[0]);
        setForecastTimeCol(dtCols[0]);
      } else {
        setAnomalyTimeCol('');
        setForecastTimeCol('');
      }
    } catch (e: any) {
      console.error('Failed to load dataset column metadata:', e);
    }
  };

  // -------------------------------------------------------------------------
  // RUN ANOMALY DETECTION
  // -------------------------------------------------------------------------
  const handleRunAnomalyDetection = async () => {
    if (!workspaceId || !selectedDatasetId || !anomalyTargetCol) return;
    setAnomalyLoading(true);
    setAnomalyError(null);
    try {
      const res = await MlApi.detectAnomalies(workspaceId, {
        dataset_id: selectedDatasetId,
        target_column: anomalyTargetCol,
        time_column: anomalyTimeCol || undefined,
        algorithm: anomalyAlgorithm,
        sensitivity: anomalySensitivity,
      });
      setAnomalyResult(res);
      loadRuns(); // Refresh runs history
    } catch (e: any) {
      setAnomalyError(e.message || 'Failed to execute anomaly detection.');
    } finally {
      setAnomalyLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // RUN TIME-SERIES FORECAST
  // -------------------------------------------------------------------------
  const handleRunForecast = async () => {
    if (!workspaceId || !selectedDatasetId || !forecastTargetCol) return;
    if (!forecastTimeCol) {
      setForecastError('A chronological date/time column is required for time-series forecasting.');
      return;
    }
    setForecastLoading(true);
    setForecastError(null);
    try {
      const res = await MlApi.generateForecast(workspaceId, {
        dataset_id: selectedDatasetId,
        target_column: forecastTargetCol,
        time_column: forecastTimeCol,
        forecast_horizon: forecastHorizon,
        algorithm: forecastAlgorithm,
        confidence_level: forecastConfidence,
        seasonality_period: forecastSeasonality || undefined,
      });
      setForecastResult(res);
      loadRuns();
    } catch (e: any) {
      setForecastError(e.message || 'Failed to generate forecast.');
    } finally {
      setForecastLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // RUN SEGMENTATION
  // -------------------------------------------------------------------------
  const handleRunSegmentation = async () => {
    if (!workspaceId || !selectedDatasetId || segmentFeatures.length === 0) {
      setSegmentError('Select at least one numerical feature column for segmentation.');
      return;
    }
    setSegmentLoading(true);
    setSegmentError(null);
    try {
      const res = await MlApi.runSegmentation(workspaceId, {
        dataset_id: selectedDatasetId,
        feature_columns: segmentFeatures,
        algorithm: segmentAlgorithm,
        cluster_count: segmentK,
        scale_features: segmentScale,
      });
      setSegmentResult(res);
      loadRuns();
    } catch (e: any) {
      setSegmentError(e.message || 'Failed to execute customer segmentation.');
    } finally {
      setSegmentLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // VIEW RUN DETAIL & GENERATE INSIGHTS
  // -------------------------------------------------------------------------
  const handleOpenRunDetail = async (runId: string) => {
    setRunInsight(null);
    setRunDetailOpen(true);
    try {
      const detail = await MlApi.getModelRun(workspaceId, runId);
      setSelectedRunDetail(detail);
    } catch (e: any) {
      console.error('Failed to load run details:', e);
    }
  };

  const handleGenerateInsight = async (runId: string) => {
    if (!workspaceId) return;
    setGeneratingInsight(true);
    try {
      const insight = await MlApi.generateInsight(workspaceId, runId, {
        audience: 'executive',
        include_recommendations: true,
      });
      setRunInsight(insight);
    } catch (e: any) {
      console.error('Failed to generate insight:', e);
    } finally {
      setGeneratingInsight(false);
    }
  };

  const handleDownloadReport = async (runId: string, format: 'pdf' | 'docx' | 'xlsx' | 'csv') => {
    if (!workspaceId) return;
    setExportingReport(format);
    try {
      const blob = await MlApi.downloadReport(workspaceId, runId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `datalens_ml_report_${runId.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e: any) {
      console.error(`Failed to export ${format.toUpperCase()} report:`, e);
    } finally {
      setExportingReport(null);
    }
  };

  // -------------------------------------------------------------------------
  // RENDER SVG SCATTER PLOT FOR ANOMALY DETECTION
  // -------------------------------------------------------------------------
  const renderAnomalyScatterPlot = () => {
    if (!anomalyResult || anomalyResult.anomalous_points.length === 0) return null;

    const points = anomalyResult.anomalous_points;
    const values = points.map((p) => p.actual_value);
    const minVal = Math.min(...values, 0);
    const maxVal = Math.max(...values, 100);
    const range = maxVal - minVal || 1;

    const svgWidth = 800;
    const svgHeight = 220;
    const padding = 40;

    return (
      <div className="w-full bg-[#0D2538] rounded-xl p-4 border border-[#1D4664]/60 overflow-hidden">
        <div className="flex items-center justify-between mb-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] animate-pulse" />
            <span className="text-white font-medium">Flagged Outlier Records</span>
          </div>
          <span className="text-[#8BE5DE] font-mono text-[11px]">
            Target Metric: {anomalyResult.target_column}
          </span>
        </div>
        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-48 select-none">
            {/* Grid Lines */}
            <line x1={padding} y1={padding} x2={svgWidth - padding} y2={padding} stroke="#1D4664" strokeDasharray="4 4" />
            <line x1={padding} y1={svgHeight / 2} x2={svgWidth - padding} y2={svgHeight / 2} stroke="#1D4664" strokeDasharray="4 4" />
            <line x1={padding} y1={svgHeight - padding} x2={svgWidth - padding} y2={svgHeight - padding} stroke="#1D4664" />

            {/* Threshold bounds if IQR or Z-score */}
            {anomalyResult.summary_metrics?.upper_bound && (
              <line
                x1={padding}
                y1={svgHeight - padding - ((anomalyResult.summary_metrics.upper_bound - minVal) / range) * (svgHeight - padding * 2)}
                x2={svgWidth - padding}
                y2={svgHeight - padding - ((anomalyResult.summary_metrics.upper_bound - minVal) / range) * (svgHeight - padding * 2)}
                stroke="#F59E0B"
                strokeWidth="1.5"
                strokeDasharray="6 3"
              />
            )}

            {/* Points */}
            {points.map((pt, idx) => {
              const cx = padding + (idx / Math.max(points.length - 1, 1)) * (svgWidth - padding * 2);
              const cy = svgHeight - padding - ((pt.actual_value - minVal) / range) * (svgHeight - padding * 2);
              const isHigh = pt.severity === 'high';

              return (
                <g key={pt.row_index} className="cursor-pointer group">
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHigh ? 6 : 4.5}
                    fill={isHigh ? '#EF4444' : '#F59E0B'}
                    stroke="#ffffff"
                    strokeWidth="1.5"
                    className="transition-transform group-hover:scale-125"
                  />
                  <text
                    x={cx}
                    y={cy - 10}
                    textAnchor="middle"
                    fill="#DDF0F5"
                    fontSize="10"
                    fontWeight="600"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    {pt.actual_value.toLocaleString()}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // RENDER SVG TIME-SERIES FORECAST CHART
  // -------------------------------------------------------------------------
  const renderForecastChart = () => {
    if (!forecastResult) return null;

    const hist = forecastResult.historical_points || [];
    const fc = forecastResult.forecast_points || [];

    const allValues = [
      ...hist.map((p) => p.actual_value),
      ...fc.map((p) => p.forecast_value),
      ...fc.map((p) => p.upper_bound),
      ...fc.map((p) => p.lower_bound),
    ];
    const minVal = Math.min(...allValues, 0);
    const maxVal = Math.max(...allValues, 100);
    const range = maxVal - minVal || 1;

    const totalSteps = hist.length + fc.length;
    const svgWidth = 850;
    const svgHeight = 240;
    const padX = 50;
    const padY = 40;

    // Helper to compute coordinates
    const getX = (index: number) => padX + (index / Math.max(totalSteps - 1, 1)) * (svgWidth - padX * 2);
    const getY = (val: number) => svgHeight - padY - ((val - minVal) / range) * (svgHeight - padY * 2);

    // Build historical polyline path
    const histPoints = hist.map((pt, i) => `${getX(i)},${getY(pt.actual_value)}`).join(' ');

    // Build forecast polyline path (starting from last historical point)
    const lastHistX = hist.length > 0 ? getX(hist.length - 1) : padX;
    const lastHistY = hist.length > 0 ? getY(hist[hist.length - 1].actual_value) : getY(0);
    const fcPoints = [`${lastHistX},${lastHistY}`, ...fc.map((pt, i) => `${getX(hist.length + i)},${getY(pt.forecast_value)}`)].join(' ');

    // Build confidence interval polygon
    const upperPoints = fc.map((pt, i) => `${getX(hist.length + i)},${getY(pt.upper_bound)}`);
    const lowerPointsReversed = fc.map((pt, i) => `${getX(hist.length + i)},${getY(pt.lower_bound)}`).reverse();
    const bandPath = `M ${lastHistX} ${lastHistY} L ${upperPoints.join(' L ')} L ${lowerPointsReversed.join(' L ')} Z`;

    return (
      <div className="w-full bg-[#0D2538] rounded-xl p-5 border border-[#1D4664]/60">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4 text-xs">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 bg-[#8BE5DE] rounded" />
              <span className="text-[#DDF0F5] font-medium">Historical Actuals</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 bg-[#009F98] border border-dashed border-white rounded" />
              <span className="text-[#009F98] font-bold">Predicted Trend</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#009F98]/20 border border-[#009F98]/40 rounded" />
              <span className="text-[#8BE5DE]/80 text-[11px]">Prediction Interval ({(forecastConfidence * 100).toFixed(0)}%)</span>
            </div>
          </div>
          <span className="text-[#8BE5DE] font-mono text-[11px]">
            Horizon: {forecastResult.forecast_horizon} periods
          </span>
        </div>

        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-56 select-none">
            {/* Grid */}
            <line x1={padX} y1={padY} x2={svgWidth - padX} y2={padY} stroke="#1D4664" strokeDasharray="4 4" />
            <line x1={padX} y1={svgHeight / 2} x2={svgWidth - padX} y2={svgHeight / 2} stroke="#1D4664" strokeDasharray="4 4" />
            <line x1={padX} y1={svgHeight - padY} x2={svgWidth - padX} y2={svgHeight - padY} stroke="#1D4664" />

            {/* Split marker between history and projection */}
            {hist.length > 0 && (
              <line
                x1={lastHistX}
                y1={padY}
                x2={lastHistX}
                y2={svgHeight - padY}
                stroke="#39C3B8"
                strokeWidth="1.5"
                strokeDasharray="3 3"
              />
            )}

            {/* Shaded Confidence Band */}
            {fc.length > 0 && <path d={bandPath} fill="#009F98" fillOpacity="0.18" />}

            {/* Historical Line */}
            {hist.length > 1 && (
              <polyline fill="none" stroke="#8BE5DE" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={histPoints} />
            )}

            {/* Forecast Line */}
            {fc.length > 0 && (
              <polyline
                fill="none"
                stroke="#009F98"
                strokeWidth="2.5"
                strokeDasharray="5 4"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={fcPoints}
              />
            )}

            {/* Forecast Point markers */}
            {fc.map((pt, i) => {
              const cx = getX(hist.length + i);
              const cy = getY(pt.forecast_value);
              return (
                <g key={pt.period_index} className="group cursor-pointer">
                  <circle cx={cx} cy={cy} r="4.5" fill="#39C3B8" stroke="#102C46" strokeWidth="2" />
                  <text
                    x={cx}
                    y={cy - 12}
                    textAnchor="middle"
                    fill="#ffffff"
                    fontSize="11"
                    fontWeight="700"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    {pt.forecast_value.toLocaleString()}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#DCE5EB]">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-[#102C46] to-[#009F98] text-white shadow-sm">
              <Sparkles className="w-6 h-6 text-[#8BE5DE]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#102C46] tracking-tight">
                Advanced Analytics & Machine Learning
              </h1>
              <p className="text-sm text-[#52616C] mt-0.5">
                Deterministic statistical forecasting, anomaly detection, and clustering with AI narrative synthesis
              </p>
            </div>
          </div>
        </div>

        {/* Global Dataset Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-[#DCE5EB] shadow-sm">
            <Database className="w-4 h-4 text-[#009F98]" />
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="text-xs font-semibold text-[#102C46] bg-transparent focus:outline-none cursor-pointer"
              disabled={loadingDatasets || datasets.length === 0}
            >
              {datasets.length === 0 ? (
                <option value="">No datasets available</option>
              ) : (
                datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.row_count?.toLocaleString() || 0} rows)
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-[#DCE5EB] text-xs font-semibold">
        <button
          onClick={() => setActiveTab('anomaly')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-all ${
            activeTab === 'anomaly'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Anomaly Detection</span>
        </button>
        <button
          onClick={() => setActiveTab('forecast')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-all ${
            activeTab === 'forecast'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Time-Series Forecasting</span>
        </button>
        <button
          onClick={() => setActiveTab('segmentation')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-all ${
            activeTab === 'segmentation'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Customer & Business Segmentation</span>
        </button>
        <button
          onClick={() => setActiveTab('runs')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-all ${
            activeTab === 'runs'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Model Registry & Reports</span>
          {modelRuns.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-[#DDF0F5] text-[#007D78]">
              {modelRuns.length}
            </span>
          )}
        </button>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* 1. ANOMALY DETECTION TAB */}
      {/* ------------------------------------------------------------------- */}
      {activeTab === 'anomaly' && (
        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="text-sm font-bold text-[#102C46] mb-4 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#009F98]" />
              Anomaly Detection Configuration
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              {/* Target Column */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Target Numeric Column *</label>
                <select
                  value={anomalyTargetCol}
                  onChange={(e) => setAnomalyTargetCol(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  {numericColumns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Time Column */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Time/Date Column (Optional)</label>
                <select
                  value={anomalyTimeCol}
                  onChange={(e) => setAnomalyTimeCol(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value="">None (Index Sequence)</option>
                  {dateColumns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Algorithm */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Algorithm</label>
                <select
                  value={anomalyAlgorithm}
                  onChange={(e) => setAnomalyAlgorithm(e.target.value as any)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value="z_score">Z-Score (Parametric Normal)</option>
                  <option value="iqr">Interquartile Range (IQR Non-parametric)</option>
                  <option value="isolation_forest">Isolation Forest (Tree Ensemble)</option>
                </select>
              </div>

              {/* Sensitivity */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-semibold text-[#52616C]">Sensitivity Threshold</label>
                  <span className="text-xs font-bold text-[#009F98]">{anomalySensitivity}</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="4.0"
                  step="0.1"
                  value={anomalySensitivity}
                  onChange={(e) => setAnomalySensitivity(parseFloat(e.target.value))}
                  className="w-full accent-[#009F98] cursor-pointer mt-1"
                />
              </div>
            </div>

            {anomalyError && (
              <div className="p-3 mb-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{anomalyError}</span>
              </div>
            )}

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleRunAnomalyDetection}
                disabled={anomalyLoading || !anomalyTargetCol}
                className="flex items-center gap-2"
              >
                {anomalyLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing Anomaly Distribution...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Detect Outliers</span>
                  </>
                )}
              </Button>
            </div>
          </Card>

          {/* Anomaly Results Display */}
          {anomalyResult && (
            <div className="space-y-6">
              {/* Summary Metric Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Total Records</span>
                  <p className="text-2xl font-bold text-[#102C46] mt-1">{anomalyResult.total_records_analyzed.toLocaleString()}</p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Flagged Outliers</span>
                  <p className="text-2xl font-bold text-[#EF4444] mt-1">{anomalyResult.anomalies_detected_count}</p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Anomaly Rate</span>
                  <p className="text-2xl font-bold text-[#009F98] mt-1">{anomalyResult.anomaly_percentage}%</p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Execution Time</span>
                  <p className="text-2xl font-bold text-[#52616C] mt-1">{anomalyResult.execution_time_ms} ms</p>
                </Card>
              </div>

              {/* Scatter Visualization */}
              {renderAnomalyScatterPlot()}

              {/* Anomalies Table */}
              <Card className="overflow-hidden">
                <div className="p-4 border-b border-[#DCE5EB] flex items-center justify-between">
                  <h4 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                    Anomalous Observations ({anomalyResult.anomalous_points.length})
                  </h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
                      <tr>
                        <th className="py-2.5 px-4">Row</th>
                        {anomalyTimeCol && <th className="py-2.5 px-4">Timestamp</th>}
                        <th className="py-2.5 px-4">Actual Value</th>
                        <th className="py-2.5 px-4">Expected Baseline</th>
                        <th className="py-2.5 px-4">Score</th>
                        <th className="py-2.5 px-4">Severity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EB]">
                      {anomalyResult.anomalous_points.map((pt) => (
                        <tr key={pt.row_index} className="hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-4 font-mono font-medium text-[#102C46]">{pt.row_index}</td>
                          {anomalyTimeCol && (
                            <td className="py-2.5 px-4 text-[#52616C]">{pt.timestamp || '—'}</td>
                          )}
                          <td className="py-2.5 px-4 font-bold text-[#EF4444]">{pt.actual_value.toLocaleString()}</td>
                          <td className="py-2.5 px-4 text-[#52616C]">{pt.expected_value?.toLocaleString() || '—'}</td>
                          <td className="py-2.5 px-4 font-mono text-[#102C46]">{pt.anomaly_score.toFixed(2)}</td>
                          <td className="py-2.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                pt.severity === 'high'
                                  ? 'bg-rose-100 text-rose-700'
                                  : pt.severity === 'medium'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {pt.severity}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Explanations & Caveats */}
              <Card className="p-4 bg-[#F8FAFC] border border-[#DCE5EB]">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-[#009F98] shrink-0 mt-0.5" />
                  <div className="text-xs space-y-2">
                    <p className="font-semibold text-[#102C46]">{anomalyResult.detection_method_explanation}</p>
                    <div className="space-y-1 text-[#52616C]">
                      {anomalyResult.caveats_and_limitations.map((c, i) => (
                        <p key={i}>• {c}</p>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 2. TIME-SERIES FORECASTING TAB */}
      {/* ------------------------------------------------------------------- */}
      {activeTab === 'forecast' && (
        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="text-sm font-bold text-[#102C46] mb-4 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#009F98]" />
              Time-Series Forecasting Configuration
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              {/* Target Column */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Target Metric *</label>
                <select
                  value={forecastTargetCol}
                  onChange={(e) => setForecastTargetCol(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  {numericColumns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Time Column */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Chronological Date/Time Column *</label>
                <select
                  value={forecastTimeCol}
                  onChange={(e) => setForecastTimeCol(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value="">Select timestamp column</option>
                  {dateColumns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                  {/* Fallback to all if no date column inferred */}
                  {dateColumns.length === 0 && numericColumns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Algorithm */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Forecasting Model</label>
                <select
                  value={forecastAlgorithm}
                  onChange={(e) => setForecastAlgorithm(e.target.value as any)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value="exponential_smoothing">Exponential Smoothing (Holt-Winters Single)</option>
                  <option value="moving_average">Rolling Moving Average</option>
                  <option value="seasonal_naive">Seasonal Naive (Cyclical Lag)</option>
                  <option value="linear_trend">Linear Trend Extrapolation</option>
                </select>
              </div>

              {/* Horizon */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Forecast Horizon</label>
                <select
                  value={forecastHorizon}
                  onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value={3}>3 Periods</option>
                  <option value={6}>6 Periods</option>
                  <option value={12}>12 Periods</option>
                  <option value={24}>24 Periods</option>
                </select>
              </div>
            </div>

            {forecastError && (
              <div className="p-3 mb-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{forecastError}</span>
              </div>
            )}

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleRunForecast}
                disabled={forecastLoading || !forecastTargetCol || !forecastTimeCol}
                className="flex items-center gap-2"
              >
                {forecastLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Projecting Time-Series Trend...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Generate Forecast</span>
                  </>
                )}
              </Button>
            </div>
          </Card>

          {/* Forecast Results */}
          {forecastResult && (
            <div className="space-y-6">
              {/* Backtesting Accuracy Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">MAE (Mean Abs Error)</span>
                  <p className="text-2xl font-bold text-[#102C46] mt-1">
                    {forecastResult.backtest_metrics?.mae != null ? forecastResult.backtest_metrics.mae.toFixed(2) : '—'}
                  </p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">RMSE (Root Mean Sq)</span>
                  <p className="text-2xl font-bold text-[#102C46] mt-1">
                    {forecastResult.backtest_metrics?.rmse != null ? forecastResult.backtest_metrics.rmse.toFixed(2) : '—'}
                  </p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">MAPE (% Error)</span>
                  <p className="text-2xl font-bold text-[#009F98] mt-1">
                    {forecastResult.backtest_metrics?.mape != null ? `${forecastResult.backtest_metrics.mape.toFixed(1)}%` : '—'}
                  </p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Confidence Interval</span>
                  <p className="text-2xl font-bold text-[#007D78] mt-1">{(forecastConfidence * 100).toFixed(0)}%</p>
                </Card>
              </div>

              {/* Chart */}
              {renderForecastChart()}

              {/* Forecast Table */}
              <Card className="overflow-hidden">
                <div className="p-4 border-b border-[#DCE5EB]">
                  <h4 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                    Forward Projections ({forecastResult.forecast_points.length} Periods)
                  </h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
                      <tr>
                        <th className="py-2.5 px-4">Period</th>
                        <th className="py-2.5 px-4">Timestamp</th>
                        <th className="py-2.5 px-4">Forecast Value</th>
                        <th className="py-2.5 px-4">Lower Bound</th>
                        <th className="py-2.5 px-4">Upper Bound</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EB]">
                      {forecastResult.forecast_points.map((pt) => (
                        <tr key={pt.period_index} className="hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-4 font-mono font-medium text-[#102C46]">+{pt.period_index}</td>
                          <td className="py-2.5 px-4 text-[#52616C]">{pt.timestamp}</td>
                          <td className="py-2.5 px-4 font-bold text-[#009F98]">{pt.forecast_value.toLocaleString()}</td>
                          <td className="py-2.5 px-4 font-mono text-[#52616C]">{pt.lower_bound.toLocaleString()}</td>
                          <td className="py-2.5 px-4 font-mono text-[#52616C]">{pt.upper_bound.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Caveats */}
              <Card className="p-4 bg-[#F8FAFC] border border-[#DCE5EB]">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-[#009F98] shrink-0 mt-0.5" />
                  <div className="text-xs space-y-2">
                    <p className="font-semibold text-[#102C46]">{forecastResult.method_explanation}</p>
                    <div className="space-y-1 text-[#52616C]">
                      {forecastResult.caveats_and_limitations.map((c, i) => (
                        <p key={i}>• {c}</p>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 3. SEGMENTATION & CLUSTERING TAB */}
      {/* ------------------------------------------------------------------- */}
      {activeTab === 'segmentation' && (
        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="text-sm font-bold text-[#102C46] mb-4 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#009F98]" />
              Customer & Business Segmentation Configuration
            </h3>

            {/* Feature Checkboxes */}
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[#52616C] mb-2">
                Clustering Feature Dimensions (Select 2+ numerical columns)
              </label>
              <div className="flex flex-wrap gap-2">
                {numericColumns.map((col) => {
                  const isSelected = segmentFeatures.includes(col);
                  return (
                    <button
                      key={col}
                      type="button"
                      onClick={() => {
                        if (isSelected) {
                          setSegmentFeatures(segmentFeatures.filter((f) => f !== col));
                        } else {
                          setSegmentFeatures([...segmentFeatures, col]);
                        }
                      }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                        isSelected
                          ? 'bg-[#102C46] text-white border-[#102C46]'
                          : 'bg-white text-[#52616C] border-[#DCE5EB] hover:border-[#009F98]'
                      }`}
                    >
                      {col}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {/* Algorithm */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Clustering Algorithm</label>
                <select
                  value={segmentAlgorithm}
                  onChange={(e) => setSegmentAlgorithm(e.target.value as any)}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  <option value="kmeans">K-Means (Centroid-based Partitioning)</option>
                  <option value="hierarchical">Hierarchical Agglomerative</option>
                </select>
              </div>

              {/* Number of Clusters K */}
              <div>
                <label className="block text-xs font-semibold text-[#52616C] mb-1">Number of Clusters (K)</label>
                <select
                  value={segmentK}
                  onChange={(e) => setSegmentK(parseInt(e.target.value))}
                  className="w-full text-xs p-2 rounded-lg border border-[#DCE5EB] bg-white text-[#102C46] focus:border-[#009F98] focus:outline-none"
                >
                  {[2, 3, 4, 5, 6].map((k) => (
                    <option key={k} value={k}>{k} Clusters</option>
                  ))}
                </select>
              </div>

              {/* Scaling */}
              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="scaleFeatures"
                  checked={segmentScale}
                  onChange={(e) => setSegmentScale(e.target.checked)}
                  className="rounded text-[#009F98] focus:ring-[#009F98]"
                />
                <label htmlFor="scaleFeatures" className="text-xs font-semibold text-[#102C46] cursor-pointer">
                  StandardScaler Normalization
                </label>
              </div>
            </div>

            {segmentError && (
              <div className="p-3 mb-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{segmentError}</span>
              </div>
            )}

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleRunSegmentation}
                disabled={segmentLoading || segmentFeatures.length === 0}
                className="flex items-center gap-2"
              >
                {segmentLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Segmenting Population Profiles...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Generate Segments</span>
                  </>
                )}
              </Button>
            </div>
          </Card>

          {/* Segmentation Results */}
          {segmentResult && (
            <div className="space-y-6">
              {/* Quality & Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Clusters Formed</span>
                  <p className="text-2xl font-bold text-[#102C46] mt-1">{segmentResult.cluster_count}</p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Total Records Clustered</span>
                  <p className="text-2xl font-bold text-[#102C46] mt-1">{segmentResult.total_records_clustered.toLocaleString()}</p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Silhouette Score</span>
                  <p className="text-2xl font-bold text-[#009F98] mt-1">
                    {segmentResult.silhouette_score != null ? segmentResult.silhouette_score.toFixed(3) : '—'}
                  </p>
                </Card>
                <Card className="p-4 bg-white border border-[#DCE5EB]">
                  <span className="text-[11px] font-semibold text-[#52616C] uppercase tracking-wider">Cluster Quality</span>
                  <p className="text-base font-bold text-[#102C46] mt-2">
                    {segmentResult.silhouette_score && segmentResult.silhouette_score > 0.5
                      ? 'High Separation'
                      : segmentResult.silhouette_score && segmentResult.silhouette_score > 0.25
                      ? 'Moderate Overlap'
                      : 'Diffuse Clusters'}
                  </p>
                </Card>
              </div>

              {/* Cluster Profiles Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {segmentResult.clusters.map((c) => (
                  <Card key={c.cluster_id} className="p-5 border-t-4 border-t-[#009F98]">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-bold text-[#102C46] text-sm">{c.cluster_name}</h4>
                      <Badge variant="teal">{c.percentage}% of cohort</Badge>
                    </div>
                    <p className="text-xs text-[#52616C] mb-4">
                      {c.record_count.toLocaleString()} observations
                    </p>
                    <p className="text-xs bg-[#F8FAFC] p-2.5 rounded-lg border border-[#DCE5EB] text-[#102C46] mb-4 font-medium leading-relaxed">
                      {c.characterization}
                    </p>

                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616C]">
                        Feature Means:
                      </span>
                      {Object.entries(c.feature_means).map(([feat, val]) => (
                        <div key={feat} className="flex items-center justify-between text-xs py-1 border-b border-[#DCE5EB]/40">
                          <span className="text-[#52616C] truncate max-w-[140px]">{feat}</span>
                          <span className="font-mono font-bold text-[#102C46]">{val.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>

              {/* Comparison Summary */}
              <Card className="p-4 bg-[#F8FAFC] border border-[#DCE5EB]">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-[#009F98] shrink-0 mt-0.5" />
                  <div className="text-xs space-y-2">
                    <p className="font-semibold text-[#102C46]">{segmentResult.segment_comparison_summary}</p>
                    <p className="text-[#52616C]">{segmentResult.method_explanation}</p>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 4. MODEL RUNS & REGISTRY TAB */}
      {/* ------------------------------------------------------------------- */}
      {activeTab === 'runs' && (
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <div className="p-4 border-b border-[#DCE5EB] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#009F98]" />
                <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                  Model Run Audit Registry ({modelRuns.length})
                </h3>
              </div>
              <Button variant="outline" size="sm" onClick={loadRuns} disabled={loadingRuns}>
                <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loadingRuns ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAFC] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
                  <tr>
                    <th className="py-3 px-4">Run ID</th>
                    <th className="py-3 px-4">Model Type</th>
                    <th className="py-3 px-4">Algorithm</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Created At</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#DCE5EB]">
                  {modelRuns.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-[#52616C]">
                        No ML model runs recorded yet in this workspace. Execute an anomaly detection, forecast, or clustering task to begin.
                      </td>
                    </tr>
                  ) : (
                    modelRuns.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-[#102C46]">{r.id.slice(0, 8)}...</td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-[#102C46] capitalize">
                            {r.model_type.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#52616C] font-mono">{r.algorithm}</td>
                        <td className="py-3 px-4">
                          <Badge variant={r.status === 'completed' ? 'verified' : 'warning'}>
                            {r.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-[#52616C]">{r.duration_ms} ms</td>
                        <td className="py-3 px-4 text-[#52616C]">
                          {new Date(r.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenRunDetail(r.id)}
                            className="text-xs"
                          >
                            Inspect & Export
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* MODEL RUN DETAIL & REPORT EXPORT MODAL */}
      {/* ------------------------------------------------------------------- */}
      {runDetailOpen && selectedRunDetail && (
        <Modal
          isOpen={runDetailOpen}
          onClose={() => setRunDetailOpen(false)}
          title={`Model Run Provenance: ${selectedRunDetail.model_type.replace('_', ' ').toUpperCase()}`}
          maxWidth="2xl"
        >
          <div className="space-y-5 text-xs">
            {/* Run Metadata */}
            <div className="grid grid-cols-2 gap-3 p-3 bg-[#F8FAFC] rounded-lg border border-[#DCE5EB]">
              <div>
                <span className="text-[#52616C] font-semibold">Run ID:</span>
                <p className="font-mono text-[#102C46] mt-0.5">{selectedRunDetail.id}</p>
              </div>
              <div>
                <span className="text-[#52616C] font-semibold">Algorithm:</span>
                <p className="font-mono text-[#102C46] mt-0.5 uppercase">{selectedRunDetail.algorithm}</p>
              </div>
              <div>
                <span className="text-[#52616C] font-semibold">Dataset ID:</span>
                <p className="font-mono text-[#102C46] mt-0.5">{selectedRunDetail.dataset_id}</p>
              </div>
              <div>
                <span className="text-[#52616C] font-semibold">Dataset Version:</span>
                <p className="font-mono text-[#102C46] mt-0.5">{selectedRunDetail.dataset_version_id}</p>
              </div>
            </div>

            {/* AI Narrative Insight Section */}
            <div className="p-4 bg-gradient-to-br from-[#102C46]/5 to-[#009F98]/10 rounded-xl border border-[#009F98]/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-[#009F98]" />
                  <h4 className="font-bold text-[#102C46]">Executive Business Interpretation</h4>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleGenerateInsight(selectedRunDetail.id)}
                  disabled={generatingInsight}
                  className="text-xs flex items-center gap-1.5"
                >
                  <Sparkles className="w-3 h-3 text-[#8BE5DE]" />
                  {generatingInsight ? 'Synthesizing...' : 'Synthesize AI Insights'}
                </Button>
              </div>

              {runInsight && (
                <div className="space-y-3 pt-2">
                  <p className="text-[#102C46] font-medium leading-relaxed bg-white p-3 rounded-lg border border-[#DCE5EB]">
                    {runInsight.insight_narrative}
                  </p>
                  <div>
                    <span className="font-bold text-[#102C46] block mb-1">Key Findings:</span>
                    <ul className="list-disc pl-5 space-y-1 text-[#52616C]">
                      {runInsight.key_findings.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                  {runInsight.suggested_actions?.length > 0 && (
                    <div>
                      <span className="font-bold text-[#007D78] block mb-1">Suggested Business Actions:</span>
                      <ul className="list-disc pl-5 space-y-1 text-[#52616C]">
                        {runInsight.suggested_actions.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Downloadable Reports Section */}
            <div className="pt-2">
              <span className="font-bold text-[#102C46] block mb-2">Export Analytical Report</span>
              <div className="flex flex-wrap gap-2">
                {(['pdf', 'docx', 'xlsx', 'csv'] as const).map((fmt) => (
                  <Button
                    key={fmt}
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadReport(selectedRunDetail.id, fmt)}
                    disabled={exportingReport === fmt}
                    className="flex items-center gap-1.5 uppercase font-mono text-xs"
                  >
                    <Download className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>{exportingReport === fmt ? 'Exporting...' : fmt}</span>
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
