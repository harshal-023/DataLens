import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Database,
  Search,
  Layers,
  Calendar,
  RefreshCw,
  TrendingUp,
  BarChart3,
  DollarSign,
  PieChart,
  Users,
  Box,
  Truck,
  Activity,
  Briefcase,
  Sliders,
  Trash2,
  Edit2,
  Save,
  Palette,
  Lightbulb,
  X,
  FileSpreadsheet,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { DatasetApi } from '../../services/apiClient';
import { StorageService } from '../../services/storageService';
import {
  AutoDashboardService,
  AutoDashboardPreviewResponse,
  AutoDashboardStatusResponse,
  GeneratedKPIItem,
  GeneratedChartItem,
} from '../../services/autoDashboardService';
import { Dataset } from '../../types';

const PURPOSE_OPTIONS = [
  { id: 'automatic', label: 'Automatic', desc: 'Let DataLens automatically discover key metrics and trends.', icon: Sparkles },
  { id: 'sales', label: 'Sales & Revenue', desc: 'Revenue, orders, customer volume, and regional sales performance.', icon: DollarSign },
  { id: 'finance', label: 'Finance & Profitability', desc: 'Gross profit, operating margins, expenses, and net returns.', icon: TrendingUp },
  { id: 'marketing', label: 'Marketing Performance', desc: 'Campaign conversions, lead acquisition, and channel breakdown.', icon: Activity },
  { id: 'customer', label: 'Customer Analytics', desc: 'Customer retention, cohorts, average order value, and lifetime value.', icon: Users },
  { id: 'operations', label: 'Operations', desc: 'Transaction velocity, cycle times, fulfillment, and volume capacity.', icon: Sliders },
  { id: 'inventory', label: 'Inventory', desc: 'Stock levels, SKU distribution, warehouse capacity, and reorder alerts.', icon: Box },
  { id: 'hr', label: 'Human Resources', desc: 'Headcount distribution, department salaries, tenure, and attrition.', icon: Briefcase },
  { id: 'logistics', label: 'Logistics', desc: 'Shipment timelines, route distribution, delivery status, and carrier performance.', icon: Truck },
  { id: 'custom', label: 'Custom Business Analysis', desc: 'Targeted custom analytics based on your specific questions.', icon: Layers },
];

const THEME_OPTIONS = [
  { id: 'ocean', name: 'Ocean', primary: '#009F98', secondary: '#39C3B8', bg: '#EDF7FA' },
  { id: 'business_blue', name: 'Business Blue', primary: '#1E40AF', secondary: '#3B82F6', bg: '#EFF6FF' },
  { id: 'sunset', name: 'Sunset', primary: '#EA580C', secondary: '#F97316', bg: '#FFF7ED' },
  { id: 'forest', name: 'Forest', primary: '#15803D', secondary: '#22C55E', bg: '#F0FDF4' },
  { id: 'royal', name: 'Royal', primary: '#7E22CE', secondary: '#A855F7', bg: '#FAF5FF' },
  { id: 'vibrant', name: 'Vibrant', primary: '#0284C7', secondary: '#06B6D4', bg: '#F0FDFA' },
  { id: 'monochrome', name: 'Monochrome', primary: '#334155', secondary: '#64748B', bg: '#F8FAFC' },
];

const GENERATION_STAGES = [
  { key: 'reading_structure', label: 'Reading dataset structure' },
  { key: 'understanding_columns', label: 'Understanding columns and data types' },
  { key: 'identifying_metrics', label: 'Identifying business metrics' },
  { key: 'discovering_relationships', label: 'Discovering useful relationships' },
  { key: 'selecting_visualizations', label: 'Selecting KPIs and visualizations' },
  { key: 'calculating_results', label: 'Calculating verified results' },
  { key: 'designing_layout', label: 'Designing dashboard layout' },
  { key: 'preparing_insights', label: 'Preparing business insights' },
];

export const AutoDashboardWizard: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const wsId = currentWorkspace?.id || '';

  // Wizard Navigation
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);

  // Screen 1: Dataset Selection State
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [datasetSearch, setDatasetSearch] = useState<string>('');
  const [loadingDatasets, setLoadingDatasets] = useState<boolean>(true);

  // Screen 2: Purpose & Custom Objective State
  const [selectedPurpose, setSelectedPurpose] = useState<string>('automatic');
  const [userObjective, setUserObjective] = useState<string>('');
  const [selectedTheme, setSelectedTheme] = useState<string>('ocean');

  // Screen 3: Generation Job State
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [currentStageKey, setCurrentStageKey] = useState<string>('reading_structure');
  const [generationProgress, setGenerationProgress] = useState<number>(10);
  const [generationMessage, setGenerationMessage] = useState<string>('Analyzing dataset...');
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Screen 4: Preview & Customization State
  const [preview, setPreview] = useState<AutoDashboardPreviewResponse | null>(null);
  const [editableTitle, setEditableTitle] = useState<string>('');
  const [isEditingTitle, setIsEditingTitle] = useState<boolean>(false);
  const [previewKpis, setPreviewKpis] = useState<GeneratedKPIItem[]>([]);
  const [previewCharts, setPreviewCharts] = useState<GeneratedChartItem[]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // 1. Fetch available workspace datasets
  useEffect(() => {
    if (!wsId) return;
    setLoadingDatasets(true);
    DatasetApi.list(wsId, { pageSize: 100 })
      .then((res: any) => {
        const items = res?.items || (Array.isArray(res) ? res : []);
        if (items.length > 0) {
          setDatasets(items);
          setSelectedDatasetId(items[0].id);
        } else {
          StorageService.getDatasetsAsync().then((mockList) => {
            if (mockList && mockList.length > 0) {
              setDatasets(mockList);
              setSelectedDatasetId(mockList[0].id);
            }
          });
        }
      })
      .catch(() => {
        StorageService.getDatasetsAsync().then((mockList) => {
          if (mockList && mockList.length > 0) {
            setDatasets(mockList);
            setSelectedDatasetId(mockList[0].id);
          }
        });
      })
      .finally(() => {
        setLoadingDatasets(false);
      });
  }, [wsId]);

  const filteredDatasets = useMemo(() => {
    if (!datasetSearch.trim()) return datasets;
    return datasets.filter((d) =>
      d.name.toLowerCase().includes(datasetSearch.toLowerCase())
    );
  }, [datasets, datasetSearch]);

  const selectedDataset = useMemo(() => {
    return datasets.find((d) => d.id === selectedDatasetId);
  }, [datasets, selectedDatasetId]);

  // 2. Trigger generation
  const handleStartGeneration = async () => {
    if (!selectedDatasetId || !wsId) return;
    setCurrentStep(3);
    setGenerationError(null);
    setGenerationProgress(15);
    setCurrentStageKey('reading_structure');
    setGenerationMessage('Reading dataset structure & storage files...');

    try {
      const res: AutoDashboardStatusResponse = await AutoDashboardService.startGeneration(wsId, {
        dataset_id: selectedDatasetId,
        business_domain: selectedPurpose,
        user_objective: userObjective.trim() || undefined,
        visual_style: selectedTheme,
      });

      setGenerationId(res.generation_id);

      // Fetch the generated preview
      const previewData: AutoDashboardPreviewResponse = await AutoDashboardService.getPreview(
        wsId,
        res.generation_id
      );

      setPreview(previewData);
      setEditableTitle(previewData.title);
      setPreviewKpis(previewData.kpis);
      setPreviewCharts(previewData.charts);
      setGenerationProgress(100);
      setCurrentStageKey('completed');
      setGenerationMessage('Dashboard ready!');

      setTimeout(() => {
        setCurrentStep(4);
      }, 600);
    } catch (err: any) {
      console.error('Auto dashboard generation failed:', err);
      setGenerationError(err?.message || 'Dashboard generation failed. Ensure dataset has analytical records.');
    }
  };

  // 3. Cancel generation
  const handleCancelGeneration = async () => {
    if (generationId && wsId) {
      try {
        await AutoDashboardService.cancelGeneration(wsId, generationId);
      } catch (err) {
        console.warn('Cancel error:', err);
      }
    }
    setCurrentStep(2);
  };

  // 4. Save generated dashboard to database
  const handleSaveDashboard = async () => {
    if (!generationId || !wsId || !preview || isSaving) return;
    setIsSaving(true);
    setSaveSuccessMsg(null);
    try {
      const saved = await AutoDashboardService.saveDashboard(wsId, generationId, {
        title: editableTitle.trim() || preview.title,
        description: preview.description,
        theme: selectedTheme,
        kpis: previewKpis,
        charts: previewCharts,
        filters: preview.filters,
      });

      setSaveSuccessMsg('Dashboard saved successfully! Redirecting...');
      setTimeout(() => {
        navigate(`/dashboards/${saved.id}`);
      }, 800);
    } catch (err: any) {
      console.error('Failed to save dashboard:', err);
      alert(err?.message || 'Failed to persist dashboard.');
      setIsSaving(false);
    }
  };

  // Widget editing & removing on Preview
  const handleRemoveKpi = (id: string) => {
    setPreviewKpis((prev) => prev.filter((k) => k.id !== id));
  };

  const handleRemoveChart = (id: string) => {
    setPreviewCharts((prev) => prev.filter((c) => c.id !== id));
  };

  const currentThemeObj = THEME_OPTIONS.find((t) => t.id === selectedTheme) || THEME_OPTIONS[0];

  return (
    <div className="h-full flex flex-col min-h-0 w-full max-w-7xl mx-auto animate-in fade-in duration-150">
      {/* Top Breadcrumb & Step Indicator */}
      <div className="shrink-0 flex items-center justify-between border-b border-[#DCE5EB] pb-3 mb-2">
        <button
          type="button"
          onClick={() => navigate('/dashboards')}
          className="flex items-center gap-1.5 text-xs font-semibold text-[#52616C] hover:text-[#102C46] transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboards</span>
        </button>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 text-xs font-bold">
          <span className={`px-2.5 py-0.5 rounded-full transition-colors ${currentStep === 1 ? 'bg-[#009F98] text-white shadow-xs' : 'bg-[#EDF7FA] text-[#009F98]'}`}>
            1. Select Data
          </span>
          <span className="text-[#94A3B8]">→</span>
          <span className={`px-2.5 py-0.5 rounded-full transition-colors ${currentStep === 2 ? 'bg-[#009F98] text-white shadow-xs' : 'bg-[#EDF7FA] text-[#009F98]'}`}>
            2. Purpose
          </span>
          <span className="text-[#94A3B8]">→</span>
          <span className={`px-2.5 py-0.5 rounded-full transition-colors ${currentStep === 3 ? 'bg-[#009F98] text-white shadow-xs' : 'bg-[#EDF7FA] text-[#009F98]'}`}>
            3. AI Generation
          </span>
          <span className="text-[#94A3B8]">→</span>
          <span className={`px-2.5 py-0.5 rounded-full transition-colors ${currentStep === 4 ? 'bg-[#009F98] text-white shadow-xs' : 'bg-[#EDF7FA] text-[#009F98]'}`}>
            4. Preview & Save
          </span>
        </div>
      </div>

      {/* Scrollable Central Content */}
      <div className="flex-1 min-h-0 overflow-y-auto px-1 py-2 sm:px-2">
        {/* ========================================================================= */}
        {/* SCREEN 1: WELCOME & DATASET SELECTION */}
        {/* ========================================================================= */}
        {currentStep === 1 && (
          <div className="space-y-6 max-w-4xl mx-auto pb-4">
            <div className="text-center space-y-2 py-4">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#007D78] to-[#009F98] text-white shadow-md">
                <Sparkles className="w-6 h-6" />
              </div>
              <h1 className="text-2xl font-serif text-[#102C46] tracking-tight">
                Create your dashboard with AI
              </h1>
              <p className="text-xs text-[#52616C] max-w-lg mx-auto leading-relaxed">
                Choose your data and DataLens will automatically discover important metrics, trends, and business insights using DuckDB calculations.
              </p>
            </div>

            {/* Search bar */}
            <div className="relative">
              <Search className="w-4 h-4 text-[#52616C] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search available datasets by name..."
                value={datasetSearch}
                onChange={(e) => setDatasetSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') e.preventDefault();
                }}
                className="w-full pl-10 pr-4 py-2.5 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] placeholder-[#52616C]/60 focus:outline-none focus:border-[#009F98] shadow-2xs"
              />
            </div>

            {/* Dataset Cards Grid */}
            {loadingDatasets ? (
              <div className="p-12 text-center bg-white rounded-2xl border border-[#DCE5EB]">
                <RefreshCw className="w-6 h-6 text-[#009F98] animate-spin mx-auto mb-2" />
                <p className="text-xs font-semibold text-[#102C46]">Loading workspace datasets...</p>
              </div>
            ) : filteredDatasets.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {filteredDatasets.map((d) => {
                  const isSelected = d.id === selectedDatasetId;
                  return (
                    <div
                      key={d.id}
                      onClick={() => setSelectedDatasetId(d.id)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                        isSelected
                          ? 'bg-[#EDF7FA]/60 border-[#009F98] ring-2 ring-[#009F98]/20 shadow-xs'
                          : 'bg-white border-[#DCE5EB] hover:border-[#BBDCE8] hover:shadow-2xs'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                            isSelected ? 'bg-[#009F98] text-white' : 'bg-[#F1F5F9] text-[#52616C]'
                          }`}>
                            <FileSpreadsheet className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="text-xs font-bold text-[#102C46]">{d.name}</h3>
                            <span className="text-[10px] text-[#52616C]">
                              {((d as any).source_type || d.fileType || 'PARQUET DATASET').toUpperCase()}
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <CheckCircle2 className="w-5 h-5 text-[#009F98] shrink-0" />
                        )}
                      </div>

                      <div className="mt-4 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-[11px] text-[#52616C]">
                        <span>
                          <strong className="text-[#102C46]">
                            {d.rowCount ? d.rowCount.toLocaleString() : (d as any).row_count ? (d as any).row_count.toLocaleString() : 'Ready'}
                          </strong> rows
                        </span>
                        <span>
                          <strong className="text-[#102C46]">{d.columnCount || (d as any).column_count || 'Multi'}</strong> columns
                        </span>
                        <span className="text-[#009F98] font-semibold">Active Version</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* Empty State */
              <div className="p-12 text-center bg-white rounded-2xl border border-[#DCE5EB] space-y-3">
                <Database className="w-8 h-8 text-[#94A3B8] mx-auto" />
                <h3 className="text-sm font-bold text-[#102C46]">No datasets available yet</h3>
                <p className="text-xs text-[#52616C] max-w-sm mx-auto">
                  Upload your first CSV or Excel file to get started with autonomous business intelligence.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/data')}
                  className="px-4 py-2 rounded-xl bg-[#009F98] text-white text-xs font-bold shadow-sm hover:bg-[#007D78] cursor-pointer"
                >
                  Go to Data Management
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* SCREEN 2: DASHBOARD PURPOSE & CUSTOM OBJECTIVES */}
        {/* ========================================================================= */}
        {currentStep === 2 && (
          <div className="space-y-6 max-w-4xl mx-auto pb-4">
            <div className="text-center space-y-1.5 py-3">
              <span className="text-[11px] font-bold text-[#009F98] bg-[#EDF7FA] px-2.5 py-0.5 rounded-full border border-[#BBDCE8]">
                Target: {selectedDataset?.name || 'Selected Dataset'}
              </span>
              <h2 className="text-2xl font-serif text-[#102C46] tracking-tight">
                What would you like to understand from this data?
              </h2>
              <p className="text-xs text-[#52616C]">
                Select an analytical focus or let DataLens automatically decide based on your data.
              </p>
            </div>

            {/* Purpose Choice Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PURPOSE_OPTIONS.map((opt) => {
                const isSelected = selectedPurpose === opt.id;
                const IconComp = opt.icon;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setSelectedPurpose(opt.id)}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                      isSelected
                        ? 'bg-[#EDF7FA]/70 border-[#009F98] ring-2 ring-[#009F98]/20 shadow-xs'
                        : 'bg-white border-[#DCE5EB] hover:border-[#BBDCE8]'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                      isSelected ? 'bg-[#009F98] text-white' : 'bg-[#F1F5F9] text-[#52616C]'
                    }`}>
                      <IconComp className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-[#102C46]">{opt.label}</h4>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-[#009F98]" />}
                      </div>
                      <p className="text-[11px] text-[#52616C] mt-0.5 leading-relaxed">{opt.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Custom Prompt Exploration (Optional) */}
            <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[#102C46]">
                  Describe what you want to explore (Optional)
                </label>
                <span className="text-[10px] text-[#52616C]">Plain English prompt</span>
              </div>
              <textarea
                rows={2}
                value={userObjective}
                onChange={(e) => setUserObjective(e.target.value)}
                placeholder="e.g. Help me understand which products generate the most revenue and which regions are performing poorly."
                className="w-full p-3 text-xs bg-[#F8FAFC] border border-[#DCE5EB] rounded-xl text-[#102C46] placeholder-[#52616C]/60 focus:outline-none focus:border-[#009F98]"
              />
            </div>

            {/* Visual Palette Selector */}
            <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] space-y-2">
              <label className="text-xs font-bold text-[#102C46] flex items-center gap-2">
                <Palette className="w-4 h-4 text-[#009F98]" />
                <span>Dashboard Visual Palette</span>
              </label>
              <div className="flex items-center gap-2 flex-wrap">
                {THEME_OPTIONS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSelectedTheme(t.id)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer transition-all ${
                      selectedTheme === t.id
                        ? 'border-[#009F98] bg-[#EDF7FA] text-[#007D78] shadow-2xs'
                        : 'border-[#DCE5EB] bg-white text-[#52616C] hover:border-[#BBDCE8]'
                    }`}
                  >
                    <span className="w-3 h-3 rounded-full" style={{ backgroundColor: t.primary }} />
                    <span>{t.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* SCREEN 3: GENERATION PROGRESS INTERFACE */}
        {/* ========================================================================= */}
        {currentStep === 3 && (
          <div className="max-w-xl mx-auto py-8 space-y-6 pb-4">
            <div className="text-center space-y-2">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#007D78] to-[#009F98] text-white shadow-lg animate-pulse">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-2xl font-serif text-[#102C46] tracking-tight">
                DataLens is understanding your data
              </h2>
              <p className="text-xs text-[#52616C] max-w-md mx-auto">
                Profiling columns, executing DuckDB analytical aggregations, and preparing layout intelligence.
              </p>
            </div>

            {/* Progress Bar */}
            <div className="bg-white p-6 rounded-2xl border border-[#DCE5EB] shadow-sm space-y-5">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-bold text-[#102C46]">
                  <span>{generationMessage}</span>
                  <span>{generationProgress}%</span>
                </div>
                <div className="w-full bg-[#EEF3F6] h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-[#007D78] to-[#009F98] h-full transition-all duration-300 rounded-full"
                    style={{ width: `${generationProgress}%` }}
                  />
                </div>
              </div>

              {/* 8 Meaningful Stages List */}
              <div className="space-y-2.5 pt-2 border-t border-[#EEF3F6]">
                {GENERATION_STAGES.map((st, idx) => {
                  const stageIndex = GENERATION_STAGES.findIndex((s) => s.key === currentStageKey);
                  const isPassed = generationProgress === 100 || idx < stageIndex;
                  const isCurrent = idx === stageIndex && generationProgress < 100;

                  return (
                    <div key={st.key} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2.5">
                        {isPassed ? (
                          <CheckCircle2 className="w-4 h-4 text-[#009F98] shrink-0" />
                        ) : isCurrent ? (
                          <RefreshCw className="w-4 h-4 text-[#009F98] animate-spin shrink-0" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-[#CBD5E1] shrink-0" />
                        )}
                        <span className={isPassed ? 'text-[#102C46] font-semibold' : isCurrent ? 'text-[#009F98] font-bold' : 'text-[#94A3B8]'}>
                          {st.label}
                        </span>
                      </div>
                      {isPassed && <span className="text-[10px] text-[#009F98] font-bold">Done</span>}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Error Message if Failed */}
            {generationError && (
              <div className="p-4 bg-[#FDE8E8] border border-[#F8B4B4] rounded-xl text-xs text-[#9B1C1C] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-[#9B1C1C]" />
                  <span>{generationError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="font-bold underline cursor-pointer"
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* SCREEN 4: DASHBOARD PREVIEW, CUSTOMIZATION & SAVE */}
        {/* ========================================================================= */}
        {currentStep === 4 && preview && (
          <div className="space-y-6 pb-4">
            {/* Header Bar */}
            <div className="bg-white p-5 rounded-2xl border border-[#DCE5EB] shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-[#009F98] bg-[#EDF7FA] px-2.5 py-0.5 rounded-full border border-[#BBDCE8] uppercase">
                    AI Generated
                  </span>
                  <span className="text-xs text-[#52616C]">
                    Dataset: <strong>{preview.dataset_name}</strong>
                  </span>
                </div>

                {isEditingTitle ? (
                  <div className="flex items-center gap-2 mt-1">
                    <input
                      type="text"
                      value={editableTitle}
                      onChange={(e) => setEditableTitle(e.target.value)}
                      className="px-2.5 py-1 text-base font-bold text-[#102C46] border border-[#009F98] rounded-lg focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setIsEditingTitle(false)}
                      className="p-1 rounded bg-[#009F98] text-white text-xs cursor-pointer"
                    >
                      Done
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold text-[#102C46] tracking-tight">{editableTitle}</h1>
                    <button
                      type="button"
                      onClick={() => setIsEditingTitle(true)}
                      className="p-1 text-[#94A3B8] hover:text-[#102C46] cursor-pointer"
                      title="Edit Title"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
                <p className="text-xs text-[#52616C]">{preview.description}</p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2.5 flex-wrap">
                {/* Palette Switcher */}
                <select
                  value={selectedTheme}
                  onChange={(e) => setSelectedTheme(e.target.value)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] cursor-pointer"
                >
                  {THEME_OPTIONS.map((t) => (
                    <option key={t.id} value={t.id}>
                      Theme: {t.name}
                    </option>
                  ))}
                </select>

                {/* Regenerate */}
                <button
                  type="button"
                  onClick={handleStartGeneration}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#DCE5EB] text-xs font-semibold text-[#52616C] hover:bg-[#F8FAFC] cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Regenerate</span>
                </button>

                {/* Save Dashboard Button */}
                <button
                  type="button"
                  onClick={handleSaveDashboard}
                  disabled={isSaving}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-[#007D78] to-[#009F98] text-white text-xs font-bold shadow-md hover:shadow-lg disabled:opacity-50 cursor-pointer"
                >
                  {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  <span>{isSaving ? 'Saving Dashboard...' : 'Save Dashboard'}</span>
                </button>
              </div>
            </div>

            {/* Success Banner */}
            {saveSuccessMsg && (
              <div className="p-3 bg-[#E4F3EC] border border-[#B7E2CE] rounded-xl text-xs text-[#216548] font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>{saveSuccessMsg}</span>
              </div>
            )}

            {/* Generated Filters Bar */}
            {preview.filters.length > 0 && (
              <div className="bg-white px-4 py-2.5 rounded-xl border border-[#DCE5EB] flex items-center gap-3 overflow-x-auto text-xs shadow-2xs">
                <span className="font-bold text-[#102C46] flex items-center gap-1 shrink-0">
                  <Sliders className="w-3.5 h-3.5 text-[#009F98]" /> Filters:
                </span>
                {preview.filters.map((f) => (
                  <div key={f.id} className="flex items-center gap-1.5 px-2.5 py-1 bg-[#F8FAFC] border border-[#DCE5EB] rounded-lg shrink-0">
                    <span className="text-[10px] text-[#52616C] uppercase font-bold">{f.name}:</span>
                    <span className="font-semibold text-[#102C46]">All</span>
                  </div>
                ))}
              </div>
            )}

            {/* SECTION 1: KPI CARDS */}
            {previewKpis.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {previewKpis.map((k) => (
                  <div
                    key={k.id}
                    className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs relative group hover:border-[#009F98] transition-all"
                  >
                    <button
                      type="button"
                      onClick={() => handleRemoveKpi(k.id)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 text-[#94A3B8] hover:text-[#9B1C1C] cursor-pointer"
                      title="Remove Widget"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-[#52616C] block">
                      {k.title}
                    </span>
                    <div
                      className="text-2xl font-bold mt-2"
                      style={{ color: currentThemeObj.primary }}
                    >
                      {k.formatted_value}
                    </div>
                    <span className="text-[10px] text-[#64748B] mt-1 block">
                      {k.aggregation.toUpperCase()} • DuckDB Verified
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* SECTION 2 & 3: CHARTS & VISUALIZATIONS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {previewCharts.map((c) => {
                const data = c.calculated_data;
                return (
                  <div
                    key={c.id}
                    className="bg-white p-5 rounded-2xl border border-[#DCE5EB] shadow-2xs flex flex-col justify-between relative group hover:border-[#009F98] transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] uppercase font-bold text-[#009F98] bg-[#EDF7FA] px-2 py-0.5 rounded-md">
                            {c.widget_type}
                          </span>
                          <h3 className="text-xs font-bold text-[#102C46]">{c.title}</h3>
                        </div>
                        {c.description && <p className="text-[11px] text-[#52616C] mt-0.5">{c.description}</p>}
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveChart(c.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-[#94A3B8] hover:text-[#9B1C1C] cursor-pointer"
                        title="Remove Widget"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Chart Rendering Canvas Preview */}
                    <div className="my-4 min-h-[180px] flex items-center justify-center bg-[#F8FAFC] rounded-xl p-3 border border-[#EEF3F6]">
                      {c.widget_type === 'donut' || c.widget_type === 'pie' ? (
                        <div className="w-full space-y-2">
                          {data?.items?.slice(0, 5).map((item: any, i: number) => {
                            const pct = data.total > 0 ? Math.round((item.value / data.total) * 100) : 0;
                            return (
                              <div key={i} className="space-y-1">
                                <div className="flex justify-between text-xs">
                                  <span className="font-semibold text-[#102C46]">{item.label}</span>
                                  <span className="text-[#52616C]">{item.value.toLocaleString()} ({pct}%)</span>
                                </div>
                                <div className="w-full bg-[#E2E8F0] h-2 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full"
                                    style={{
                                      width: `${pct}%`,
                                      backgroundColor: i === 0 ? currentThemeObj.primary : currentThemeObj.secondary,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : c.widget_type === 'table' ? (
                        <div className="w-full overflow-x-auto max-h-48 text-[11px]">
                          <table className="w-full text-left">
                            <thead>
                              <tr className="border-b border-[#CBD5E1] text-[#64748B]">
                                {data?.columns?.slice(0, 4).map((col: string) => (
                                  <th key={col} className="p-1 font-bold">{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {data?.rows?.slice(0, 5).map((row: any, rIdx: number) => (
                                <tr key={rIdx} className="border-b border-[#EEF3F6]">
                                  {data.columns.slice(0, 4).map((col: string) => (
                                    <td key={col} className="p-1 text-[#102C46]">{String(row[col] ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        /* Bar / Line Trajectory */
                        <div className="w-full space-y-2">
                          {data?.categories?.slice(0, 5).map((cat: string, cIdx: number) => {
                            const val = data.values[cIdx] || 0;
                            const maxVal = Math.max(...data.values, 1);
                            const barWidth = Math.round((val / maxVal) * 100);
                            return (
                              <div key={cIdx} className="space-y-0.5">
                                <div className="flex justify-between text-xs">
                                  <span className="font-semibold text-[#102C46]">{cat}</span>
                                  <span className="text-[#52616C]">{val.toLocaleString()}</span>
                                </div>
                                <div className="w-full bg-[#E2E8F0] h-2 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all"
                                    style={{
                                      width: `${barWidth}%`,
                                      backgroundColor: currentThemeObj.primary,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                          {(!data?.categories || data.categories.length === 0) && (
                            <div className="text-center text-xs text-[#94A3B8]">Calculated time-series data</div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-[#EEF3F6] flex items-center justify-between text-[11px] text-[#52616C]">
                      <span>Metric: <strong className="text-[#102C46]">{c.query_config.metric_column || 'Count'}</strong></span>
                      <span className="text-[#009F98] font-semibold">DuckDB Engine</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* SECTION 4: VERIFIED AI BUSINESS INSIGHTS */}
            {preview.insights.length > 0 && (
              <div className="bg-[#EDF7FA] p-5 rounded-2xl border border-[#BBDCE8] space-y-3">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-[#007D78]" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#007D78]">
                    Verified Business Intelligence Insights
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {preview.insights.map((ins) => (
                    <div key={ins.id} className="p-3 bg-white rounded-xl border border-[#DCE5EB] space-y-1">
                      <h4 className="text-xs font-bold text-[#102C46]">{ins.title}</h4>
                      <p className="text-[11px] text-[#52616C] leading-relaxed">{ins.observation}</p>
                      <div className="text-[10px] text-[#94A3B8] pt-1">
                        Evidence: {ins.evidence}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* PERSISTENT NON-SCROLLING WIZARD NAVIGATION FOOTER */}
      {/* ========================================================================= */}
      <footer className="shrink-0 bg-white border border-[#DCE5EB] rounded-2xl px-6 py-3.5 shadow-sm mt-3 flex items-center justify-between gap-4">
        {currentStep === 1 && (
          <>
            <button
              type="button"
              onClick={() => navigate('/dashboards')}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#DCE5EB] bg-white text-xs font-semibold text-[#52616C] hover:bg-[#F8FAFC] cursor-pointer transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Dashboards</span>
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              disabled={!selectedDatasetId}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#007D78] to-[#009F98] text-white text-xs font-bold shadow-md hover:shadow-lg disabled:opacity-50 cursor-pointer transition-all"
            >
              <span>Next: Purpose</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </>
        )}

        {currentStep === 2 && (
          <>
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#DCE5EB] bg-white text-xs font-semibold text-[#52616C] hover:bg-[#F8FAFC] cursor-pointer transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>

            <button
              type="button"
              onClick={handleStartGeneration}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#007D78] to-[#009F98] text-white text-xs font-bold shadow-md hover:shadow-lg cursor-pointer transition-all"
            >
              <Sparkles className="w-4 h-4 text-white" />
              <span>Next: Generate Dashboard</span>
            </button>
          </>
        )}

        {currentStep === 3 && (
          <>
            <button
              type="button"
              onClick={handleCancelGeneration}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#F8B4B4] bg-[#FDE8E8] text-xs font-semibold text-[#9B1C1C] hover:bg-[#FBD5D5] cursor-pointer transition-colors"
            >
              <X className="w-4 h-4" />
              <span>Cancel Generation</span>
            </button>

            <div className="flex items-center gap-2 text-xs font-bold text-[#009F98]">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Generating Dashboard ({generationProgress}%)...</span>
            </div>
          </>
        )}

        {currentStep === 4 && (
          <>
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#DCE5EB] bg-white text-xs font-semibold text-[#52616C] hover:bg-[#F8FAFC] cursor-pointer transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={handleStartGeneration}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#DCE5EB] text-xs font-semibold text-[#52616C] hover:bg-[#F8FAFC] cursor-pointer transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Regenerate</span>
              </button>

              <button
                type="button"
                onClick={handleSaveDashboard}
                disabled={isSaving}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#007D78] to-[#009F98] text-white text-xs font-bold shadow-md hover:shadow-lg disabled:opacity-50 cursor-pointer transition-all"
              >
                {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>{isSaving ? 'Saving Dashboard...' : 'Save Dashboard'}</span>
              </button>
            </div>
          </>
        )}
      </footer>
    </div>
  );
};
