import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Check,
  ShieldCheck,
  Calendar,
  Layers,
  BarChart3,
  FileSpreadsheet,
  AlertCircle,
  FileCode,
  Download,
  Database,
  Sliders,
  DollarSign,
  TrendingUp,
  Activity,
  UserCheck,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { Stepper } from '../../components/common/Stepper';
import { useAuth } from '../../context/AuthContext';
import { DatasetApi } from '../../services/apiClient';
import {
  businessReportService,
  ReportTemplate,
} from '../../services/businessReportService';

const PREDEFINED_TEMPLATES = [
  {
    id: 'tpl-executive-review',
    name: 'Executive Business Review',
    category: 'executive',
    icon: Activity,
    desc: 'High-level strategic briefing with core macro KPIs, revenue trends, and leadership recommendations.',
  },
  {
    id: 'tpl-sales-performance',
    name: 'Sales Performance Report',
    category: 'sales',
    icon: TrendingUp,
    desc: 'Commercial bookings, pipeline conversion funnels, quota attainment, and top product rankings.',
  },
  {
    id: 'tpl-financial-performance',
    name: 'Financial Performance Report',
    category: 'finance',
    icon: DollarSign,
    desc: 'P&L analysis, margin decomposition, variance waterfalls, and cash flow review.',
  },
  {
    id: 'tpl-marketing-analytics',
    name: 'Marketing Analytics Report',
    category: 'marketing',
    icon: BarChart3,
    desc: 'Omnichannel acquisition efficiency, blended CAC, lead volume, and channel mix.',
  },
  {
    id: 'tpl-customer-analytics',
    name: 'Customer Analytics Report',
    category: 'customer',
    icon: UserCheck,
    desc: 'Cohort retention, customer lifetime value (LTV), churn risk, and segmentation.',
  },
  {
    id: 'tpl-operations-report',
    name: 'Operations & Fulfillment Report',
    category: 'operations',
    icon: Layers,
    desc: 'SLA adherence, throughput distribution, incident turnaround times, and defect Pareto curves.',
  },
  {
    id: 'tpl-predictive-analytics',
    name: 'Predictive Analytics Report',
    category: 'predictive',
    icon: Sparkles,
    desc: 'Automated time-series forecasts, anomaly detection outliers, and clustering.',
  },
  {
    id: 'tpl-custom-report',
    name: 'Custom Modular Report',
    category: 'custom',
    icon: FileText,
    desc: 'Blank canvas for modular KPIs, charts, data tables, and custom commentary.',
  },
];

export const ReportBuilder: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('tpl-executive-review');

  // Datasets
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [datasetColumns, setDatasetColumns] = useState<any[]>([]);

  // Metadata
  const [reportTitle, setReportTitle] = useState<string>('Executive Business Performance Audit');
  const [description, setDescription] = useState<string>('Quarterly operational and financial performance review.');
  const [period, setPeriod] = useState<string>('2026-Q1');
  const [reportType, setReportType] = useState<string>('executive');

  // Sections
  const [includeSummary, setIncludeSummary] = useState<boolean>(true);
  const [includeKPIs, setIncludeKPIs] = useState<boolean>(true);
  const [includeChart, setIncludeChart] = useState<boolean>(true);
  const [includeTable, setIncludeTable] = useState<boolean>(true);
  const [includeFindings, setIncludeFindings] = useState<boolean>(true);
  const [includeRecommendations, setIncludeRecommendations] = useState<boolean>(true);
  const [includeProvenance, setIncludeProvenance] = useState<boolean>(true);

  // Status
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load datasets on mount
  useEffect(() => {
    if (!workspaceId) return;
    const loadDatasets = async () => {
      try {
        const res = await DatasetApi.list(workspaceId, { pageSize: 50 });
        const items = res.items || [];
        setDatasets(items);
        if (items.length > 0) {
          setSelectedDatasetId(items[0].id);
        }
      } catch (e) {
        console.warn('Failed to load datasets:', e);
      }
    };
    loadDatasets();
  }, [workspaceId]);

  // Load columns when dataset selected
  useEffect(() => {
    if (!workspaceId || !selectedDatasetId) return;
    const loadCols = async () => {
      try {
        const d = await DatasetApi.get(workspaceId, selectedDatasetId);
        setDatasetColumns(d.columns || []);
      } catch (e) {
        setDatasetColumns([]);
      }
    };
    loadCols();
  }, [workspaceId, selectedDatasetId]);

  const handleSelectTemplate = (tplId: string) => {
    setSelectedTemplateId(tplId);
    const tpl = PREDEFINED_TEMPLATES.find((t) => t.id === tplId);
    if (tpl) {
      setReportType(tpl.category);
      setReportTitle(`${tpl.name} — ${new Date().getFullYear()}`);
    }
  };

  const steps = [
    { id: 1, label: 'Template & Data', description: 'Blueprint & Sources' },
    { id: 2, label: 'Metadata & Scope', description: 'Period & Context' },
    { id: 3, label: 'Compose Sections', description: 'KPIs & Visuals' },
    { id: 4, label: 'Review & Publish', description: 'Save & Generate' },
  ];

  const handleSaveReport = async (runNow: boolean = true) => {
    if (!workspaceId) return;
    try {
      setIsSaving(true);
      setError(null);

      // Assemble sections configuration
      const sections = [];
      if (includeSummary) {
        sections.push({
          id: 'sec-summary',
          title: 'Executive Summary',
          section_type: 'summary',
          description: 'Synthesizes core business performance and key executive decisions.',
        });
      }
      if (includeKPIs) {
        const numCol = datasetColumns.find((c: any) =>
          ['float', 'double', 'int', 'numeric', 'integer', 'number'].some((t) =>
            (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
          )
        );
        sections.push({
          id: 'sec-kpis',
          title: 'Key Performance Indicators',
          section_type: 'kpi_grid',
          kpi_items: [
            {
              label: numCol ? `Total ${numCol.name}` : 'Recorded Transactions',
              metric_column: numCol ? numCol.name : undefined,
              aggregation: 'sum',
              unit: numCol ? '$' : '',
            },
          ],
        });
      }
      if (includeChart) {
        const strCol = datasetColumns.find((c: any) =>
          ['varchar', 'text', 'string'].some((t) =>
            (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
          )
        );
        const numCol = datasetColumns.find((c: any) =>
          ['float', 'double', 'int', 'numeric', 'integer', 'number'].some((t) =>
            (c.data_type || c.inferred_type || '').toLowerCase().includes(t)
          )
        );
        sections.push({
          id: 'sec-chart',
          title: 'Contribution & Segment Breakdown',
          section_type: 'chart',
          chart_type: 'bar',
          group_by_column: strCol ? strCol.name : undefined,
          metric_column: numCol ? numCol.name : undefined,
          aggregation: 'sum',
        });
      }
      if (includeTable) {
        sections.push({
          id: 'sec-table',
          title: 'Detailed Analytical Ledger',
          section_type: 'table',
          limit: 20,
        });
      }
      if (includeFindings) {
        sections.push({
          id: 'sec-findings',
          title: 'Strategic Business Findings',
          section_type: 'findings',
        });
      }
      if (includeRecommendations) {
        sections.push({
          id: 'sec-recommendations',
          title: 'Actionable Recommendations',
          section_type: 'recommendations',
        });
      }
      if (includeProvenance) {
        sections.push({
          id: 'sec-provenance',
          title: 'Data Provenance & Methodology',
          section_type: 'provenance',
        });
      }

      const selectedDs = datasets.find((d) => d.id === selectedDatasetId);

      const created = await businessReportService.createReport(workspaceId, {
        title: reportTitle.trim() || 'Business Intelligence Audit',
        description: description.trim() || null,
        report_type: reportType,
        template_id: selectedTemplateId,
        configuration: {
          period,
          sections,
          branding: {
            organization_name: 'DataLens Executive Intelligence',
            primary_color: '#102C46',
            accent_color: '#009F98',
          },
        },
        source_dataset_refs: selectedDs
          ? [
              {
                dataset_id: selectedDs.id,
                name: selectedDs.name,
                version_id: selectedDs.current_version_id,
              },
            ]
          : [],
      });

      if (runNow) {
        // Trigger run immediately
        await businessReportService.runReport(workspaceId, created.id, {
          period,
          formats: ['pdf', 'docx', 'xlsx', 'csv'],
        });
      }

      navigate(`/reports/${created.id}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to save and generate report.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-24 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/reports')}
            className="w-8 h-8 rounded-xl bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] flex items-center justify-center text-[#52616C] hover:text-[#102C46] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-[#102C46]">Automated Report Builder</h1>
            <p className="text-xs text-[#52616C]">
              Compose verified executive business reports with deterministic analytics and AI synthesis.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838]">
          {error}
        </div>
      )}

      {/* Stepper Navigation */}
      <Stepper steps={steps} currentStep={currentStep} onStepClick={(id) => setCurrentStep(id)} />

      {/* Step 1: Template & Data */}
      {currentStep === 1 && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-2xs space-y-6">
          <div>
            <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider mb-1">
              1. Choose a Professional Report Template
            </h2>
            <p className="text-xs text-[#52616C] mb-4">
              Select an industry-tailored blueprint or choose custom for blank-canvas composition.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {PREDEFINED_TEMPLATES.map((t) => {
                const Icon = t.icon;
                const isSelected = selectedTemplateId === t.id;
                return (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => handleSelectTemplate(t.id)}
                    className={`flex flex-col items-start p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-[#009F98] bg-[#EDF7FA] text-[#007D78] ring-2 ring-[#009F98]/20 shadow-xs'
                        : 'border-[#DCE5EB] bg-white text-[#52616C] hover:border-[#BBDCE8] hover:bg-[#F5F8FA]'
                    }`}
                  >
                    <Icon className={`w-5 h-5 mb-2 ${isSelected ? 'text-[#009F98]' : 'text-[#52616C]'}`} />
                    <span className="text-xs font-bold text-[#102C46] leading-tight mb-1">
                      {t.name}
                    </span>
                    <span className="text-[10px] text-[#52616C] line-clamp-2 leading-relaxed">
                      {t.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-4 border-t border-[#DCE5EB]">
            <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider mb-1">
              2. Connect Primary Workspace Dataset
            </h2>
            <p className="text-xs text-[#52616C] mb-3">
              Select the source dataset whose immutable Parquet files will power all KPI math and charts.
            </p>

            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="w-full sm:max-w-md px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] font-medium"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.row_count?.toLocaleString()} rows)
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end pt-4 border-t border-[#DCE5EB]">
            <Button
              variant="primary"
              size="md"
              onClick={() => setCurrentStep(2)}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Continue to Metadata
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Metadata & Scope */}
      {currentStep === 2 && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-2xs space-y-6">
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider">
              Report Metadata & Analytical Scope
            </h2>

            <div>
              <label className="block text-xs font-bold text-[#102C46] mb-1">
                Report Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                placeholder="e.g. Q1 Operations & Fulfillment Review"
                className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#102C46] mb-1">
                Executive Subtitle / Objective
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of report objective and scope..."
                className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-[#102C46] mb-1">
                  Reporting Period / Date Window
                </label>
                <input
                  type="text"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  placeholder="e.g. 2026-Q1 or Last 30 Days"
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46]"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-[#102C46] mb-1">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46] capitalize font-medium"
                >
                  <option value="executive">Executive Review</option>
                  <option value="sales">Sales Performance</option>
                  <option value="finance">Financial P&L</option>
                  <option value="marketing">Marketing Analytics</option>
                  <option value="customer">Customer Health</option>
                  <option value="operations">Operations & Fulfillment</option>
                  <option value="predictive">Predictive Analytics</option>
                  <option value="custom">Custom Modular</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-[#DCE5EB]">
            <Button variant="secondary" size="md" onClick={() => setCurrentStep(1)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
              Back
            </Button>
            <Button variant="primary" size="md" onClick={() => setCurrentStep(3)} rightIcon={<ArrowRight className="w-4 h-4" />}>
              Configure Sections
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Compose Sections */}
      {currentStep === 3 && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-2xs space-y-6">
          <div>
            <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider mb-1">
              Select Included Report Sections
            </h2>
            <p className="text-xs text-[#52616C] mb-4">
              Toggle modular blocks to include in your multi-format document.
            </p>

            <div className="space-y-3">
              {[
                { label: 'Executive Summary Narrative', desc: 'Plain-language overview synthesized from verified evidence.', state: includeSummary, set: setIncludeSummary },
                { label: 'Key Performance Indicators Grid', desc: 'Headline metric cards with target benchmarks and period variance.', state: includeKPIs, set: setIncludeKPIs },
                { label: 'Analytical Visualizations', desc: 'Categorical distribution bar or breakdown charts.', state: includeChart, set: setIncludeChart },
                { label: 'Detailed Tabular Ledger', desc: 'Tabular records extracted directly from DuckDB Parquet data.', state: includeTable, set: setIncludeTable },
                { label: 'Strategic Business Findings', desc: 'Evidence-backed observations highlighting growth drivers.', state: includeFindings, set: setIncludeFindings },
                { label: 'Actionable Recommendations', desc: 'Concrete operational recommendations grounded in findings.', state: includeRecommendations, set: setIncludeRecommendations },
                { label: 'Methodology & Data Provenance', desc: 'Audit trail with dataset version IDs, row counts, and manifest hashes.', state: includeProvenance, set: setIncludeProvenance },
              ].map((s, idx) => (
                <label
                  key={idx}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all cursor-pointer ${
                    s.state
                      ? 'border-[#009F98] bg-[#EDF7FA]/50 text-[#102C46]'
                      : 'border-[#DCE5EB] bg-white text-[#52616C] hover:bg-[#F5F8FA]'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={s.state}
                    onChange={(e) => s.set(e.target.checked)}
                    className="mt-0.5 rounded text-[#009F98] focus:ring-[#009F98]"
                  />
                  <div>
                    <span className="text-xs font-bold block">{s.label}</span>
                    <span className="text-[11px] text-[#52616C]">{s.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-[#DCE5EB]">
            <Button variant="secondary" size="md" onClick={() => setCurrentStep(2)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
              Back
            </Button>
            <Button variant="primary" size="md" onClick={() => setCurrentStep(4)} rightIcon={<ArrowRight className="w-4 h-4" />}>
              Review & Finalize
            </Button>
          </div>
        </div>
      )}

      {/* Step 4: Review & Publish */}
      {currentStep === 4 && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-2xs space-y-6">
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider">
              Review Report Configuration
            </h2>

            <div className="bg-[#F5F8FA] p-4 rounded-xl border border-[#DCE5EB] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#52616C]">Report Title:</span>
                <span className="font-bold text-[#102C46]">{reportTitle}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#52616C]">Report Type:</span>
                <span className="font-bold text-[#102C46] capitalize">{reportType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#52616C]">Reporting Window:</span>
                <span className="font-bold text-[#102C46]">{period}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#52616C]">Source Dataset:</span>
                <span className="font-bold text-[#102C46]">
                  {datasets.find((d) => d.id === selectedDatasetId)?.name || 'None selected'}
                </span>
              </div>
            </div>

            <div className="p-4 bg-[#E4F3EC] rounded-xl border border-[#C3E7D5] text-xs text-[#216548] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>
                <strong>Zero Fabrication Guarantee:</strong> Saving this report will freeze the dataset version provenance and generate verified PDF, DOCX, XLSX, and CSV documents.
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-[#DCE5EB]">
            <Button variant="secondary" size="md" onClick={() => setCurrentStep(3)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
              Back
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="md"
                onClick={() => handleSaveReport(false)}
                isLoading={isSaving}
              >
                Save as Draft
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={() => handleSaveReport(true)}
                isLoading={isSaving}
                leftIcon={<Sparkles className="w-4 h-4" />}
              >
                Save & Run Now
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
