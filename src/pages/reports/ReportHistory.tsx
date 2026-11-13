import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  Download,
  AlertCircle,
  CheckCircle2,
  FileText,
  FileSpreadsheet,
  FileCode,
  RotateCw,
  Eye,
  Layers,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  businessReportService,
  BusinessReport,
  ReportRun,
} from '../../services/businessReportService';
import { Button } from '../../components/common/Button';

export const ReportHistory: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [report, setReport] = useState<BusinessReport | null>(null);
  const [runs, setRuns] = useState<ReportRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!workspaceId || !reportId) return;
    try {
      setLoading(true);
      setError(null);
      const rep = await businessReportService.getReport(workspaceId, reportId);
      setReport(rep);
      const runList = await businessReportService.listReportRuns(workspaceId, reportId);
      setRuns(runList);
    } catch (err: any) {
      setError(err?.message || 'Failed to load report run history.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, reportId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDownload = async (runId: string, format: 'pdf' | 'docx' | 'xlsx' | 'csv') => {
    if (!workspaceId) return;
    try {
      setDownloadingId(`${runId}-${format}`);
      const blob = await businessReportService.downloadRunFile(workspaceId, runId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report?.title.toLowerCase().replace(/\s+/g, '_') || 'report'}_${runId.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err?.message || `Failed to download ${format.toUpperCase()}`);
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
        <span className="text-xs text-[#52616C] font-medium">Loading report history...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-20 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/reports/${reportId}`)}
            className="w-8 h-8 rounded-xl bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] flex items-center justify-center text-[#52616C] hover:text-[#102C46] transition-colors cursor-pointer"
            title="Back to Report"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-[#102C46]">
              Execution History: {report?.title}
            </h1>
            <p className="text-xs text-[#52616C]">
              Immutable record of manual and scheduled report generation runs.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData} leftIcon={<RotateCw className="w-3.5 h-3.5" />}>
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate(`/reports/${reportId}`)} leftIcon={<Eye className="w-3.5 h-3.5" />}>
            View Live Report
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838]">
          {error}
        </div>
      )}

      {/* Runs Table */}
      {runs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-[#DCE5EB] p-8">
          <div className="w-12 h-12 bg-[#EDF7FA] rounded-xl flex items-center justify-center text-[#009F98] mx-auto mb-3">
            <Layers className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-[#102C46]">No Execution Runs Recorded</h3>
          <p className="text-xs text-[#52616C] max-w-sm mx-auto mt-1 mb-4">
            This business report has not been generated yet. Trigger a manual run or configure a recurring schedule.
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate(`/reports/${reportId}`)}
          >
            Go to Report
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F5F8FA] border-b border-[#DCE5EB] text-[#52616C] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Report Period</th>
                  <th className="py-3 px-4">Trigger</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">AI Grounded</th>
                  <th className="py-3 px-4">Executed At</th>
                  <th className="py-3 px-4 text-right">Downloads</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#DCE5EB]">
                {runs.map((r) => {
                  const isCompleted = r.execution_status === 'completed';
                  const isFailed = r.execution_status === 'failed';
                  return (
                    <tr key={r.id} className="hover:bg-[#F5F8FA]/60 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                            isCompleted
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : isFailed
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : isFailed ? (
                            <AlertCircle className="w-3 h-3" />
                          ) : (
                            <Clock className="w-3 h-3 animate-spin" />
                          )}
                          {r.execution_status.toUpperCase()}
                        </span>
                      </td>

                      <td className="py-3 px-4 font-semibold text-[#102C46]">
                        {r.report_period || 'Current Window'}
                      </td>

                      <td className="py-3 px-4 text-[#52616C] capitalize">
                        {r.trigger_type}
                      </td>

                      <td className="py-3 px-4 text-[#52616C]">
                        {r.execution_duration_ms > 0 ? `${(r.execution_duration_ms / 1000).toFixed(2)}s` : '-'}
                      </td>

                      <td className="py-3 px-4">
                        {r.ai_generated ? (
                          <span className="text-[10px] font-bold text-[#009F98] bg-[#EDF7FA] px-2 py-0.5 rounded border border-[#BBDCE8]">
                            Gemini
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-[#52616C] bg-[#F5F8FA] px-2 py-0.5 rounded border border-[#DCE5EB]">
                            Deterministic
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-[#52616C]">
                        {new Date(r.created_at).toLocaleString()}
                      </td>

                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        {isCompleted && r.generated_files ? (
                          <div className="flex items-center justify-end gap-1.5">
                            {r.generated_files.pdf && (
                              <button
                                type="button"
                                onClick={() => handleDownload(r.id, 'pdf')}
                                disabled={downloadingId === `${r.id}-pdf`}
                                className="px-2 py-1 rounded bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] text-[11px] font-bold text-[#102C46] flex items-center gap-1 cursor-pointer"
                                title="Download PDF"
                              >
                                <FileText className="w-3 h-3 text-red-500" />
                                PDF
                              </button>
                            )}
                            {r.generated_files.docx && (
                              <button
                                type="button"
                                onClick={() => handleDownload(r.id, 'docx')}
                                disabled={downloadingId === `${r.id}-docx`}
                                className="px-2 py-1 rounded bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] text-[11px] font-bold text-[#102C46] flex items-center gap-1 cursor-pointer"
                                title="Download Word DOCX"
                              >
                                <FileText className="w-3 h-3 text-blue-500" />
                                DOCX
                              </button>
                            )}
                            {r.generated_files.xlsx && (
                              <button
                                type="button"
                                onClick={() => handleDownload(r.id, 'xlsx')}
                                disabled={downloadingId === `${r.id}-xlsx`}
                                className="px-2 py-1 rounded bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] text-[11px] font-bold text-[#102C46] flex items-center gap-1 cursor-pointer"
                                title="Download Excel XLSX"
                              >
                                <FileSpreadsheet className="w-3 h-3 text-emerald-600" />
                                XLSX
                              </button>
                            )}
                            {r.generated_files.csv && (
                              <button
                                type="button"
                                onClick={() => handleDownload(r.id, 'csv')}
                                disabled={downloadingId === `${r.id}-csv`}
                                className="px-2 py-1 rounded bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] text-[11px] font-bold text-[#102C46] flex items-center gap-1 cursor-pointer"
                                title="Download CSV"
                              >
                                <FileCode className="w-3 h-3 text-[#009F98]" />
                                CSV
                              </button>
                            )}
                          </div>
                        ) : isFailed ? (
                          <span className="text-[11px] text-red-600 font-medium">
                            {r.error_details || 'Execution failed'}
                          </span>
                        ) : (
                          <span className="text-[11px] text-[#52616C] animate-pulse">Running...</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

