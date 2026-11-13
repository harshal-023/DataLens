import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Edit,
  RotateCw,
  Download,
  Share2,
  Calendar,
  Database,
  Clock,
  ChevronDown,
  CheckCircle2,
  ShieldCheck,
  ArrowLeft,
  FileText,
  FileSpreadsheet,
  FileCode,
  History,
  Send,
  Sparkles,
  Sliders,
  TrendingUp,
  TrendingDown,
  Check,
  AlertTriangle,
} from 'lucide-react';
import { DataLensLogo } from '../../components/common/DataLensLogo';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { useAuth } from '../../context/AuthContext';
import {
  businessReportService,
  BusinessReport,
  ReportRun,
} from '../../services/businessReportService';
import { StorageService } from '../../services/storageService';

export const ReportPreview: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [businessReport, setBusinessReport] = useState<BusinessReport | null>(null);
  const [evidence, setEvidence] = useState<any | null>(null);
  const [latestRun, setLatestRun] = useState<ReportRun | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Actions state
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runMsg, setRunMsg] = useState<string | null>(null);
  const [downloadMsg, setDownloadMsg] = useState<string | null>(null);
  const [isShareModalOpen, setIsShareModalOpen] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);

  // Schedule Modal state
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [schedFrequency, setSchedFrequency] = useState<'daily' | 'weekly' | 'monthly'>('weekly');
  const [schedHour, setSchedHour] = useState<number>(8);
  const [schedTimezone, setSchedTimezone] = useState<string>('UTC');
  const [schedRecipients, setSchedRecipients] = useState<string>('');
  const [savingSchedule, setSavingSchedule] = useState<boolean>(false);

  // Load report & preview data
  const loadReportData = useCallback(async () => {
    if (!reportId) return;
    try {
      setLoading(true);
      setError(null);

      // Check server-side BusinessReport first
      if (workspaceId) {
        try {
          const rep = await businessReportService.getReport(workspaceId, reportId);
          setBusinessReport(rep);

          // Get preview evidence
          const ev = await businessReportService.previewReport(workspaceId, reportId);
          setEvidence(ev);

          // Get runs to find latest completed run
          const runs = await businessReportService.listReportRuns(workspaceId, reportId);
          if (runs && runs.length > 0) {
            setLatestRun(runs[0]);
          }
          return;
        } catch (e) {
          // Fall through to client storage
        }
      }

      // Client storage fallback
      const local = await StorageService.getReportByIdAsync(reportId);
      if (local) {
        setEvidence({
          report_title: local.title,
          report_type: local.type || 'Custom',
          period: local.period || 'All Records',
          generated_at: local.createdAt,
          ai_generated: false,
          sections: local.sections.map((s) => ({
            id: s.id,
            title: s.title,
            section_type: s.type,
            content: s.contentMarkdown,
            kpi_items: [],
          })),
          kpis: [],
          provenance: [
            {
              dataset_name: local.datasetName,
              version_id: local.datasetVersion,
              row_count: 0,
            },
          ],
        });
      } else {
        setError('Report not found in workspace.');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load report preview.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, reportId]);

  useEffect(() => {
    loadReportData();
  }, [loadReportData]);

  // Handle Manual Run
  const handleTriggerRun = async () => {
    if (!workspaceId || !reportId) return;
    try {
      setIsRunning(true);
      setRunMsg('Assembling analytical evidence and generating multi-format exports...');
      const run = await businessReportService.runReport(workspaceId, reportId, {
        period: businessReport?.configuration?.period || 'Current Window',
        formats: ['pdf', 'docx', 'xlsx', 'csv'],
      });
      setLatestRun(run);
      setRunMsg('Report generated successfully with verified provenance!');
      // Refresh preview evidence
      const ev = await businessReportService.previewReport(workspaceId, reportId);
      setEvidence(ev);
    } catch (err: any) {
      setRunMsg(`Run failed: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsRunning(false);
      setTimeout(() => setRunMsg(null), 4000);
    }
  };

  // Handle Download
  const handleDownload = async (format: 'pdf' | 'docx' | 'xlsx' | 'csv') => {
    if (!workspaceId) return;
    try {
      setDownloadMsg(`Downloading ${format.toUpperCase()}...`);

      // If we have a completed run, download its stored file
      let blob: Blob;
      if (latestRun && latestRun.execution_status === 'completed' && latestRun.generated_files?.[format]) {
        blob = await businessReportService.downloadRunFile(workspaceId, latestRun.id, format);
      } else if (reportId) {
        // Trigger a fresh run or download
        const run = await businessReportService.runReport(workspaceId, reportId, { formats: [format] });
        blob = await businessReportService.downloadRunFile(workspaceId, run.id, format);
      } else {
        throw new Error('No report available for download.');
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(evidence?.report_title || 'business_report').toLowerCase().replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setDownloadMsg(`${format.toUpperCase()} downloaded!`);
    } catch (err: any) {
      setDownloadMsg(`Download failed: ${err?.message}`);
    } finally {
      setTimeout(() => setDownloadMsg(null), 3000);
    }
  };

  // Handle Schedule Creation
  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || !reportId) return;
    try {
      setSavingSchedule(true);
      const recipientList = schedRecipients
        .split(',')
        .map((r) => r.trim())
        .filter(Boolean);

      await businessReportService.createSchedule(workspaceId, reportId, {
        frequency: schedFrequency,
        hour: Number(schedHour),
        minute: 0,
        timezone: schedTimezone,
        delivery_configuration: {
          email_recipients: recipientList,
          attach_formats: ['pdf', 'xlsx'],
        },
      });

      setIsScheduleModalOpen(false);
      alert(`Automated ${schedFrequency} schedule configured successfully!`);
    } catch (err: any) {
      alert(err?.message || 'Failed to create schedule.');
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
        <span className="text-xs text-[#52616C] font-medium">Assembling business report...</span>
      </div>
    );
  }

  if (error || !evidence) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-bold text-[#102C46]">Report Not Found</h2>
        <p className="text-xs text-[#52616C] mt-1">{error}</p>
        <Link to="/reports" className="text-xs font-bold text-[#009F98] hover:underline mt-4 inline-block">
          Return to Reports Library
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-24 animate-in fade-in duration-150">
      {/* Top Breadcrumb & Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
        <div className="flex items-center gap-2 text-xs text-[#52616C]">
          <button
            onClick={() => navigate('/reports')}
            className="hover:text-[#102C46] transition-colors cursor-pointer flex items-center gap-1 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Reports</span>
          </button>
          <span>&gt;</span>
          <span className="font-semibold text-[#102C46] truncate max-w-xs sm:max-w-md">
            {evidence.report_title}
          </span>
          {evidence.ai_generated ? (
            <span className="text-[10px] font-bold text-[#009F98] bg-[#EDF7FA] px-2 py-0.5 rounded-full border border-[#BBDCE8] flex items-center gap-1">
              <Sparkles className="w-2.5 h-2.5" />
              AI Grounded
            </span>
          ) : (
            <span className="text-[10px] font-bold text-[#52616C] bg-[#F5F8FA] px-2 py-0.5 rounded-full border border-[#DCE5EB]">
              Deterministic
            </span>
          )}
        </div>

        {/* Action Buttons Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {runMsg && (
            <span className="text-xs font-semibold text-[#216548] flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> {runMsg}
            </span>
          )}
          {downloadMsg && (
            <span className="text-xs font-semibold text-[#009F98] flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> {downloadMsg}
            </span>
          )}

          {/* Run Now Button */}
          <Button
            variant="primary"
            size="sm"
            onClick={handleTriggerRun}
            isLoading={isRunning}
            leftIcon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Run Now
          </Button>

          {/* Schedule Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsScheduleModalOpen(true)}
            leftIcon={<Calendar className="w-3.5 h-3.5 text-[#009F98]" />}
          >
            Schedule
          </Button>

          {/* Run History */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/reports/${reportId}/history`)}
            leftIcon={<History className="w-3.5 h-3.5 text-[#52616C]" />}
          >
            History
          </Button>

          {/* Download Dropdown */}
          <div className="relative group">
            <button
              type="button"
              className="px-3 py-1.5 rounded-xl border border-[#DCE5EB] bg-white hover:bg-[#F5F8FA] text-xs font-semibold text-[#102C46] flex items-center gap-1.5 shadow-2xs cursor-pointer transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-[#009F98]" />
              <span>Export</span>
              <ChevronDown className="w-3 h-3 text-[#52616C]" />
            </button>

            <div className="absolute right-0 mt-1 w-44 bg-white rounded-xl shadow-elevated border border-[#DCE5EB] p-1.5 hidden group-hover:block z-30 animate-in fade-in-50">
              <button
                type="button"
                onClick={() => handleDownload('pdf')}
                className="w-full text-left px-3 py-1.5 text-xs text-[#102C46] hover:bg-[#F5F8FA] rounded-lg cursor-pointer flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5 text-red-500" />
                Executive PDF (.pdf)
              </button>
              <button
                type="button"
                onClick={() => handleDownload('docx')}
                className="w-full text-left px-3 py-1.5 text-xs text-[#102C46] hover:bg-[#F5F8FA] rounded-lg cursor-pointer flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5 text-blue-500" />
                Word Document (.docx)
              </button>
              <button
                type="button"
                onClick={() => handleDownload('xlsx')}
                className="w-full text-left px-3 py-1.5 text-xs text-[#102C46] hover:bg-[#F5F8FA] rounded-lg cursor-pointer flex items-center gap-2"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                Excel Workbook (.xlsx)
              </button>
              <button
                type="button"
                onClick={() => handleDownload('csv')}
                className="w-full text-left px-3 py-1.5 text-xs text-[#102C46] hover:bg-[#F5F8FA] rounded-lg cursor-pointer flex items-center gap-2"
              >
                <FileCode className="w-3.5 h-3.5 text-[#009F98]" />
                CSV Data (.csv)
              </button>
            </div>
          </div>

          {/* Share */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsShareModalOpen(true)}
            leftIcon={<Share2 className="w-3.5 h-3.5 text-[#52616C]" />}
          >
            Share
          </Button>
        </div>
      </div>

      {/* Main Report Document Canvas */}
      <div className="bg-white rounded-3xl border border-[#DCE5EB] shadow-elevated p-6 sm:p-12 space-y-10 relative overflow-hidden">
        {/* Cover / Header Banner */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 pb-6 border-b border-[#DCE5EB]">
          <div className="space-y-4 max-w-2xl">
            <DataLensLogo size="md" theme="light" />

            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#102C46] tracking-tight">
                {evidence.report_title}
              </h1>
              <p className="text-xs text-[#52616C] mt-1 font-medium capitalize">
                {evidence.report_type} Business Review • DataLens Automated Intelligence
              </p>
            </div>

            {/* Metadata Pills */}
            <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
              <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] px-3 py-1.5 rounded-xl text-[#102C46]">
                <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                <span className="text-[#52616C]">Reporting Window:</span>
                <span className="font-semibold">{evidence.period}</span>
              </div>

              <div className="flex items-center gap-1.5 bg-[#F5F8FA] border border-[#DCE5EB] px-3 py-1.5 rounded-xl text-[#102C46]">
                <Clock className="w-3.5 h-3.5 text-[#009F98]" />
                <span className="text-[#52616C]">Assembled:</span>
                <span className="font-semibold">{evidence.generated_at}</span>
              </div>
            </div>
          </div>

          {/* Top Decorative Banner Card */}
          <div className="p-4 bg-gradient-to-br from-[#102C46] to-[#1D4664] rounded-2xl text-white max-w-xs shrink-0 shadow-sm">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#39C3B8]">
              Governance Certified
            </span>
            <h4 className="text-xs font-bold mt-1">Verified Analytical Parity</h4>
            <p className="text-[11px] text-white/80 mt-1 leading-relaxed">
              Every numerical claim is backed by immutable DuckDB execution records and Parquet dataset manifests.
            </p>
          </div>
        </div>

        {/* Sections Renderer */}
        {evidence.sections?.map((sec: any, idx: number) => {
          const secType = sec.section_type;
          return (
            <section key={sec.id || idx} className="space-y-4">
              <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-2">
                <h2 className="text-sm font-bold text-[#102C46] uppercase tracking-wider flex items-center gap-2">
                  <span className="w-5 h-5 rounded-lg bg-[#EDF7FA] text-[#009F98] flex items-center justify-center text-xs">
                    {idx + 1}
                  </span>
                  <span>{sec.title}</span>
                </h2>
                {sec.description && (
                  <span className="text-[11px] text-[#52616C] hidden sm:inline">
                    {sec.description}
                  </span>
                )}
              </div>

              {/* Summary Narrative */}
              {secType === 'summary' && (
                <div className="p-5 rounded-2xl bg-[#F5F8FA] border border-[#DCE5EB] text-xs leading-relaxed text-[#102C46] space-y-3 font-medium">
                  {sec.content ? (
                    sec.content.split('\n\n').map((para: string, pIdx: number) => (
                      <p key={pIdx}>{para}</p>
                    ))
                  ) : (
                    <p className="text-[#52616C] italic">No narrative generated yet.</p>
                  )}
                </div>
              )}

              {/* KPI Grid */}
              {secType === 'kpi_grid' && sec.kpi_items && (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {sec.kpi_items.map((kpi: any, kIdx: number) => {
                    const comp = kpi.comparison;
                    return (
                      <div
                        key={kIdx}
                        className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs space-y-2 hover:border-[#009F98] transition-colors"
                      >
                        <span className="text-xs font-semibold text-[#52616C] line-clamp-1">
                          {kpi.metric}
                        </span>
                        <div className="flex items-baseline justify-between">
                          <span className="text-xl sm:text-2xl font-extrabold text-[#102C46]">
                            {kpi.formatted_value || kpi.value}
                          </span>
                          {comp && (
                            <span
                              className={`text-[11px] font-bold px-2 py-0.5 rounded-full flex items-center gap-0.5 ${
                                comp.direction === 'up'
                                  ? 'bg-[#E4F3EC] text-[#216548]'
                                  : comp.direction === 'down'
                                  ? 'bg-[#FCE9E9] text-[#A63838]'
                                  : 'bg-[#F5F8FA] text-[#52616C]'
                              }`}
                            >
                              {comp.direction === 'up' ? (
                                <TrendingUp className="w-3 h-3" />
                              ) : (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              {comp.percentage_change > 0 ? '+' : ''}
                              {comp.percentage_change}%
                            </span>
                          )}
                        </div>
                        {comp && (
                          <span className="text-[10px] text-[#52616C] block">
                            vs Target {comp.benchmark}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Chart Breakdown Table / Preview */}
              {secType === 'chart' && sec.chart_items && (
                <div className="bg-[#F5F8FA] p-4 rounded-2xl border border-[#DCE5EB] space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-[#102C46]">
                    <span>Category Distribution</span>
                    <span className="text-[11px] text-[#009F98] uppercase">
                      {sec.chart_type || 'Bar'} Breakdown
                    </span>
                  </div>
                  <div className="space-y-2">
                    {sec.chart_items.slice(0, 8).map((item: any, cIdx: number) => {
                      const total = sec.chart_items.reduce((s: number, i: any) => s + (i.value || 0), 0) || 1;
                      const pct = Math.round(((item.value || 0) / total) * 100);
                      return (
                        <div key={cIdx} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-[#102C46]">{item.label}</span>
                            <span className="font-mono text-[#52616C]">
                              {typeof item.value === 'number' ? item.value.toLocaleString() : item.value} ({pct}%)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-[#DCE5EB] overflow-hidden">
                            <div
                              className="h-full bg-[#009F98] rounded-full transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Data Table */}
              {secType === 'table' && sec.columns && sec.rows && (
                <div className="border border-[#DCE5EB] rounded-2xl overflow-hidden shadow-2xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#F5F8FA] border-b border-[#DCE5EB] text-[#52616C] font-bold">
                        <tr>
                          {sec.columns.slice(0, 6).map((col: string, colIdx: number) => (
                            <th key={colIdx} className="py-2.5 px-3">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#DCE5EB]">
                        {sec.rows.slice(0, 10).map((row: any, rIdx: number) => (
                          <tr key={rIdx} className="hover:bg-[#F5F8FA]/60">
                            {sec.columns.slice(0, 6).map((col: string, colIdx: number) => (
                              <td key={colIdx} className="py-2 px-3 text-[#102C46] font-mono">
                                {String(row[col] ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Strategic Findings */}
              {secType === 'findings' && sec.findings && (
                <div className="space-y-2">
                  {sec.findings.map((f: string, fIdx: number) => (
                    <div
                      key={fIdx}
                      className="p-3 bg-white rounded-xl border border-[#DCE5EB] text-xs text-[#102C46] flex items-start gap-2 shadow-2xs"
                    >
                      <Check className="w-4 h-4 text-[#009F98] shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Executive Recommendations */}
              {secType === 'recommendations' && sec.recommendations && (
                <div className="space-y-2">
                  {sec.recommendations.map((r: string, rIdx: number) => (
                    <div
                      key={rIdx}
                      className="p-3 bg-[#EDF7FA] rounded-xl border border-[#BBDCE8] text-xs text-[#007D78] flex items-start gap-2 shadow-2xs font-medium"
                    >
                      <CheckCircle2 className="w-4 h-4 text-[#009F98] shrink-0 mt-0.5" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Provenance Table */}
              {secType === 'provenance' && sec.provenance_records && (
                <div className="border border-[#DCE5EB] rounded-2xl overflow-hidden shadow-2xs bg-[#F5F8FA]/50">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F5F8FA] border-b border-[#DCE5EB] text-[#52616C] font-bold">
                      <tr>
                        <th className="py-2.5 px-3">Dataset Name</th>
                        <th className="py-2.5 px-3">Version ID</th>
                        <th className="py-2.5 px-3">Analyzed Rows</th>
                        <th className="py-2.5 px-3">Manifest Integrity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EB]">
                      {sec.provenance_records.map((p: any, pIdx: number) => (
                        <tr key={pIdx}>
                          <td className="py-2 px-3 font-bold text-[#102C46]">
                            {p.dataset_name}
                          </td>
                          <td className="py-2 px-3 font-mono text-[11px] text-[#52616C]">
                            {p.version_id}
                          </td>
                          <td className="py-2 px-3 text-[#102C46]">
                            {p.row_count?.toLocaleString() || '-'} records
                          </td>
                          <td className="py-2 px-3 text-[11px] text-emerald-700 font-mono">
                            <ShieldCheck className="w-3.5 h-3.5 inline mr-1 text-emerald-600" />
                            {p.manifest_sha256?.slice(0, 12)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Limitations */}
              {secType === 'limitations' && sec.limitations && (
                <div className="space-y-1.5">
                  {sec.limitations.map((l: string, lIdx: number) => (
                    <div
                      key={lIdx}
                      className="p-2.5 bg-[#FFF9E6] border border-[#FFE8A3] rounded-xl text-xs text-[#8A6D1C] flex items-center gap-2"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{l}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          );
        })}

        {/* Footer */}
        <div className="pt-8 border-t border-[#DCE5EB] flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-[#52616C] gap-2">
          <span>DataLens Enterprise Automated Business Report • Certified Lineage</span>
          <span>Confidential Executive Audit • Generated by DataLens Engine</span>
        </div>
      </div>

      {/* Schedule Modal */}
      <Modal
        isOpen={isScheduleModalOpen}
        onClose={() => setIsScheduleModalOpen(false)}
        title="Schedule Automated Report"
        subtitle="Configure recurring report generation and secure email delivery."
        maxWidth="md"
      >
        <form onSubmit={handleSaveSchedule} className="space-y-4 pt-2">
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Generation Frequency
            </label>
            <select
              value={schedFrequency}
              onChange={(e) => setSchedFrequency(e.target.value as any)}
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-[#102C46] mb-1">
                Execution Hour (0-23)
              </label>
              <input
                type="number"
                min="0"
                max="23"
                value={schedHour}
                onChange={(e) => setSchedHour(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#102C46] mb-1">
                Timezone
              </label>
              <select
                value={schedTimezone}
                onChange={(e) => setSchedTimezone(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
              >
                <option value="UTC">UTC (Universal)</option>
                <option value="America/New_York">US Eastern (EST)</option>
                <option value="America/Los_Angeles">US Pacific (PST)</option>
                <option value="Europe/London">London (GMT)</option>
                <option value="Asia/Kolkata">India (IST)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Email Recipients (Comma-separated)
            </label>
            <input
              type="text"
              value={schedRecipients}
              onChange={(e) => setSchedRecipients(e.target.value)}
              placeholder="e.g. executive@company.com, team@company.com"
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl bg-white text-[#102C46]"
            />
            <span className="text-[10px] text-[#52616C] mt-1 block">
              Automated reports will be emailed with PDF and Excel attachments.
            </span>
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-[#DCE5EB]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsScheduleModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={savingSchedule}
              leftIcon={<Send className="w-3.5 h-3.5" />}
            >
              Save Schedule
            </Button>
          </div>
        </form>
      </Modal>

      {/* Share Modal */}
      <Modal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        title="Share Executive Report"
        subtitle="Provide secure read-only access to stakeholders."
        maxWidth="md"
      >
        <div className="space-y-4 pt-2">
          <p className="text-xs text-[#52616C]">
            Anyone with this link will have verified, tamper-proof viewing access.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              readOnly
              value={window.location.href}
              className="flex-1 px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white select-all text-[#102C46]"
            />
            <button
              onClick={handleCopyLink}
              className="px-3.5 py-2 rounded-xl bg-[#009F98] text-white text-xs font-semibold hover:bg-[#007D78] cursor-pointer transition-colors"
            >
              {copiedLink ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
