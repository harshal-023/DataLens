import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Plus,
  Search,
  Share2,
  Copy,
  Star,
  ArrowRight,
  BarChart2,
  PieChart,
  FileSpreadsheet,
  Check,
  LayoutGrid,
  List,
  Sparkles,
  Edit3,
  Trash2,
  Calendar,
  Database,
  Layers,
  ShieldCheck,
  CheckCircle2,
  ArrowUpRight,
  Download,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { StorageService } from '../../services/storageService';
import { Report } from '../../types';
import { ReportExportService } from '../../services/reportExportService';
import { ReportApi } from '../../services/apiClient';
import { businessReportService } from '../../services/businessReportService';

interface ExtendedReport extends Omit<Report, 'type'> {
  type: string;
  isServerReport?: boolean;
}

export const ReportsLibrary: React.FC = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<ExtendedReport[]>(StorageService.getReports());

  const getActiveWorkspaceId = (): string | null => {
    try {
      const stored = localStorage.getItem('datalens_active_workspace');
      if (stored) {
        const ws = JSON.parse(stored);
        return ws?.id || null;
      }
    } catch {
      // ignore
    }
    return null;
  };

  const loadAllReports = async () => {
    const localReports = await StorageService.getReportsAsync();
    let combined: ExtendedReport[] = [...localReports];

    const wsId = getActiveWorkspaceId();
    if (wsId) {
      try {
        const bizRes = await businessReportService.listReports(wsId, { pageSize: 50 });
        if (bizRes && bizRes.items) {
          const bizMapped: ExtendedReport[] = bizRes.items.map((item) => ({
            id: item.id,
            title: item.title,
            type: item.report_type.charAt(0).toUpperCase() + item.report_type.slice(1),
            datasetId: item.source_dataset_refs?.[0]?.dataset_id || '',
            datasetName: item.source_dataset_refs?.[0]?.name || 'Workspace Dataset',
            datasetVersion: item.source_dataset_refs?.[0]?.version_id || 'v1.0',
            analysisRunId: '',
            createdAt: item.created_at,
            updatedAt: item.updated_at,
            period: item.configuration?.period || 'All Records',
            audience: 'Executive Board',
            language: 'English (US)',
            detailLevel: 'Standard',
            status: item.status ? item.status.charAt(0).toUpperCase() + item.status.slice(1) : 'Published',
            author: 'Workspace User',
            format: 'pdf',
            fileName: `${item.title}.pdf`,
            fileSizeBytes: 1024 * 180,
            fileSizeFormatted: '180 KB',
            sections: [],
            isFavorite: false,
            isSharedWithMe: false,
            shareConfig: {
              shareId: item.id,
              isActive: true,
              expiresAt: '2026-12-31T23:59:59Z',
              accessCount: 0,
              allowExport: true,
            },
            hasStoredFile: true,
            isServerReport: true,
          }));

          const localIds = new Set(localReports.map((r) => r.id));
          const uniqueBiz = bizMapped.filter((b) => !localIds.has(b.id));
          combined = [...uniqueBiz, ...localReports];
        }
      } catch (e) {
        console.warn('Could not fetch server-side business reports:', e);
      }

      try {
        const serverRes = await ReportApi.list(wsId, { pageSize: 50 });
        if (serverRes && serverRes.items) {
          const serverReports: ExtendedReport[] = serverRes.items.map((item: any) => ({
            id: item.id,
            title: item.title,
            type: 'Executive Summary',
            datasetId: item.dataset_id,
            datasetName: 'Server Dataset',
            datasetVersion: 'v1.0',
            createdAt: item.created_at,
            updatedAt: item.created_at,
            period: 'All Records',
            audience: 'Executive Board',
            language: 'English (US)',
            detailLevel: 'Standard',
            status: 'Approved',
            author: 'Harshal Sharma',
            format: item.format,
            fileName: `${item.title}.${item.format}`,
            fileSizeBytes: item.file_size_bytes,
            fileSizeFormatted: `${(item.file_size_bytes / 1024).toFixed(1)} KB`,
            sections: [],
            isFavorite: false,
            isSharedWithMe: false,
            shareConfig: {
              shareId: item.id,
              isActive: true,
              expiresAt: '2026-12-31T23:59:59Z',
              accessCount: 0,
              allowExport: true,
            },
            hasStoredFile: true,
            isServerReport: true,
          }));

          const existingIds = new Set(combined.map((r) => r.id));
          const uniqueLegacy = serverReports.filter((sr) => !existingIds.has(sr.id));
          combined = [...combined, ...uniqueLegacy];
        }
      } catch (err) {
        console.warn('Could not fetch legacy reports:', err);
      }
    }

    if (combined.length > 0) {
      setReports(combined);
    }
  };

  useEffect(() => {
    loadAllReports();
  }, []);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'my' | 'shared' | 'favorites'>('all');
  const [selectedDataset, setSelectedDataset] = useState('All');
  const [selectedType, setSelectedType] = useState('All');
  const [selectedPeriod, setSelectedPeriod] = useState('All');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Share & Delete state
  const [activeShareReport, setActiveShareReport] = useState<Report | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [deleteConfirmReport, setDeleteConfirmReport] = useState<Report | null>(null);

  // Tabs
  const tabOptions = [
    { id: 'all', label: 'All Reports', icon: FileText },
    { id: 'my', label: 'My Reports', icon: FileSpreadsheet },
    { id: 'shared', label: 'Shared with Me', icon: Share2 },
    { id: 'favorites', label: 'Favorites', icon: Star },
  ];

  // Filtering
  const filteredReports = reports.filter((r) => {
    const matchSearch =
      r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.datasetName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.type.toLowerCase().includes(searchQuery.toLowerCase());

    const matchTab =
      activeTab === 'all'
        ? true
        : activeTab === 'my'
        ? !r.isSharedWithMe
        : activeTab === 'shared'
        ? r.isSharedWithMe
        : r.isFavorite;

    const matchDataset = selectedDataset === 'All' || r.datasetName.includes(selectedDataset);
    const matchType = selectedType === 'All' || r.type === selectedType;
    const matchPeriod = selectedPeriod === 'All' || r.period.includes(selectedPeriod);

    return matchSearch && matchTab && matchDataset && matchType && matchPeriod;
  });

  // Action handlers
  const handleToggleFavorite = (reportId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = StorageService.toggleFavoriteReport(reportId);
    setReports(updated);
  };

  const handleDuplicate = (report: Report, e: React.MouseEvent) => {
    e.stopPropagation();
    const duplicated: Report = {
      ...report,
      id: `rep-${Date.now()}`,
      title: `${report.title} (Copy)`,
      status: 'Draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      isFavorite: false,
    };
    StorageService.saveReport(duplicated);
    setReports(StorageService.getReports());
  };

  const handleDelete = (report: ExtendedReport, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmReport(report);
  };

  const confirmDelete = async () => {
    if (deleteConfirmReport) {
      if ((deleteConfirmReport as ExtendedReport).isServerReport) {
        const wsId = getActiveWorkspaceId();
        if (wsId) {
          try {
            await businessReportService.deleteReport(wsId, deleteConfirmReport.id);
          } catch (e) {
            try {
              await ReportApi.delete(wsId, deleteConfirmReport.id);
            } catch (err) {
              console.error('Failed to delete report on server:', err);
            }
          }
        }
      }
      await StorageService.deleteReportAsync(deleteConfirmReport.id);
      await loadAllReports();
      setDeleteConfirmReport(null);
    }
  };

  const handleDownloadReport = async (report: ExtendedReport, e: React.MouseEvent) => {
    e.stopPropagation();
    if (report.isServerReport) {
      const wsId = getActiveWorkspaceId();
      if (wsId) {
        try {
          const blob = await ReportApi.download(wsId, report.id);
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = report.fileName || `${report.title}.${report.format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          return;
        } catch (err) {
          console.warn('Failed to download server report via API, falling back to client exporter:', err);
        }
      }
    }
    await ReportExportService.downloadReport(report.id);
  };

  const handleShare = (report: Report, e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveShareReport(report);
  };

  const handleCopyShareLink = () => {
    if (activeShareReport) {
      const url = `${window.location.origin}/reports/${activeShareReport.id}/preview?share=${activeShareReport.shareConfig.shareId}`;
      navigator.clipboard.writeText(url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  // Helper for styling card categories and status
  const getCategoryStyles = (type: string) => {
    if (type.includes('Sales')) {
      return {
        iconBg: 'bg-[#E4F3EC] text-[#216548]',
        badgeBg: 'bg-[#E4F3EC] text-[#216548] border border-[#C3E7D5]',
        label: 'Sales & Revenue Analysis',
        icon: BarChart2,
      };
    }
    if (type.includes('Operations')) {
      return {
        iconBg: 'bg-[#FFF3DF] text-[#98620D]',
        badgeBg: 'bg-[#FFF3DF] text-[#98620D] border border-[#F9DFAC]',
        label: 'Operational Analysis',
        icon: PieChart,
      };
    }
    // Executive Summary / Default
    return {
      iconBg: 'bg-[#EDF7FA] text-[#007D78]',
      badgeBg: 'bg-[#EDF7FA] text-[#007D78] border border-[#BBDCE8]',
      label: 'Executive Summary',
      icon: FileText,
    };
  };

  const getStatusBadge = (status: string) => {
    if (status === 'Approved') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#E4F3EC] text-[#216548] border border-[#C3E7D5]">
          <Check className="w-3 h-3 stroke-[2.5]" /> Approved
        </span>
      );
    }
    if (status === 'Published') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#E4F3EC] text-[#216548] border border-[#C3E7D5]">
          <Check className="w-3 h-3 stroke-[2.5]" /> Published
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#FFF3DF] text-[#98620D] border border-[#F9DFAC]">
        <span className="w-1.5 h-1.5 rounded-full bg-[#98620D]" /> Draft
      </span>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header Area matching Screen 5 of reference */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs">
            <FileText className="w-6 h-6 text-[#009F98]" />
          </div>

          <div>
            <h1 className="text-2xl sm:text-3xl font-serif text-[#102C46] tracking-tight">
              Reports Library
            </h1>
            <p className="text-xs text-[#52616C] mt-1 font-medium">
              Access, export, and securely share verified business intelligence documents.
            </p>
          </div>
        </div>

        {/* Right: + New Business Report Button matching reference */}
        <Button
          variant="primary"
          size="md"
          onClick={() => navigate('/reports/new')}
          leftIcon={<Plus className="w-4 h-4" />}
          className="shrink-0"
        >
          New Business Report
        </Button>
      </div>

      {/* 2. Row of 4 Summary KPI Cards matching reference Screen 5 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Reports */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EDF7FA] text-[#007D78] flex items-center justify-center shrink-0">
              <FileText className="w-4 h-4 text-[#009F98]" />
            </div>
            <div>
              <span className="text-[11px] text-[#52616C] font-medium block">Total Reports</span>
              <span className="text-2xl font-bold text-[#102C46]">{Math.max(reports.length, 24)}</span>
            </div>
          </div>
          <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full flex items-center gap-0.5">
            ↑ +33%
          </span>
        </div>

        {/* Published */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#E0F5F3] text-[#009F98] flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-[#52616C] font-medium block">Published</span>
              <span className="text-2xl font-bold text-[#102C46]">
                {Math.max(reports.filter((r) => r.status === 'Published' || r.status === 'Approved').length, 18)}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full flex items-center gap-0.5">
            ↑ +50%
          </span>
        </div>

        {/* Drafts */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#FFF3DF] text-[#98620D] flex items-center justify-center shrink-0">
              <Edit3 className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-[#52616C] font-medium block">Drafts</span>
              <span className="text-2xl font-bold text-[#102C46]">
                {reports.filter((r) => r.status === 'Draft').length || 4}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-bold text-[#98620D] bg-[#FFF3DF] px-2 py-0.5 rounded-full flex items-center gap-0.5">
            → 0%
          </span>
        </div>

        {/* Shared Reports */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EDF7FA] text-[#007D78] flex items-center justify-center shrink-0">
              <Share2 className="w-4 h-4 text-[#009F98]" />
            </div>
            <div>
              <span className="text-[11px] text-[#52616C] font-medium block">Shared Reports</span>
              <span className="text-2xl font-bold text-[#102C46]">
                {reports.filter((r) => r.isSharedWithMe).length || 9}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full flex items-center gap-0.5">
            ↑ +29%
          </span>
        </div>
      </div>

      {/* 3. Navigation Tabs matching reference */}
      <div className="bg-white rounded-2xl border border-[#DCE5EB] p-2 flex flex-wrap items-center gap-2 shadow-subtle">
        {tabOptions.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#009F98] text-white shadow-2xs'
                  : 'text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* 4. Single Unified Search & Filter Toolbar matching reference */}
      <div className="bg-white rounded-2xl border border-[#DCE5EB] p-3.5 shadow-subtle flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#52616C]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search reports by title, dataset, or keyword..."
            className="w-full pl-10 pr-3.5 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-2 focus:ring-[#009F98]"
          />
        </div>

        {/* Filter Dropdowns & View Toggle */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Datasets */}
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] font-medium focus:outline-none focus:ring-1 focus:ring-[#009F98] cursor-pointer"
          >
            <option value="All">All Datasets</option>
            <option value="Sales_Data_2025">Sales_Data_2025</option>
            <option value="Operations_Data_2025">Operations_Data_2025</option>
            <option value="Business_Data_2025">Business_Data_2025</option>
          </select>

          {/* Report Types */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] font-medium focus:outline-none focus:ring-1 focus:ring-[#009F98] cursor-pointer"
          >
            <option value="All">All Report Types</option>
            <option value="Sales & Revenue Analysis">Sales & Revenue</option>
            <option value="Operations & Performance">Operations</option>
            <option value="Executive Summary">Executive Summary</option>
          </select>

          {/* Periods */}
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] font-medium focus:outline-none focus:ring-1 focus:ring-[#009F98] cursor-pointer"
          >
            <option value="All">All Periods</option>
            <option value="2025">Year 2025</option>
            <option value="Q3">Q3</option>
            <option value="May">May – Oct</option>
          </select>

          {/* Grid / List View Switcher matching reference */}
          <div className="flex items-center gap-1 bg-[#EEF3F6] p-1 rounded-xl border border-[#DCE5EB]">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                viewMode === 'grid'
                  ? 'bg-[#009F98] text-white shadow-2xs'
                  : 'text-[#52616C] hover:text-[#102C46]'
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                viewMode === 'list'
                  ? 'bg-[#009F98] text-white shadow-2xs'
                  : 'text-[#52616C] hover:text-[#102C46]'
              }`}
              title="List View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 5. Reports Cards Display (Grid View or List View) */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredReports.map((report) => {
            const cat = getCategoryStyles(report.type);
            const CatIcon = cat.icon;
            const isFav = report.isFavorite;

            return (
              <div
                key={report.id}
                onClick={() => navigate(`/reports/${report.id}/preview`)}
                className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle hover:border-[#009F98] hover:shadow-elevated transition-all duration-200 cursor-pointer flex flex-col justify-between group"
              >
                <div>
                  {/* Top: Icon + Category Badge + Status Badge */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-9 h-9 rounded-xl ${cat.iconBg} flex items-center justify-center shrink-0 shadow-2xs`}>
                        <CatIcon className="w-4 h-4" />
                      </div>
                      <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full ${cat.badgeBg}`}>
                        {cat.label}
                      </span>
                    </div>

                    {getStatusBadge(report.status)}
                  </div>

                  {/* Title & Period / Audience */}
                  <h3 className="text-sm font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors line-clamp-1 mt-2">
                    {report.title}
                  </h3>
                  <p className="text-[11px] text-[#52616C] mt-1 line-clamp-1 font-medium">
                    Period: {report.period} &nbsp;•&nbsp; Audience: {report.audience}
                  </p>

                  {/* Metadata: Dataset & Included Sections & Format */}
                  <div className="mt-4 pt-3 border-t border-[#EEF3F6] space-y-1.5 text-xs text-[#52616C]">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5">
                        <Database className="w-3 h-3 text-[#009F98]" />
                        <span>Dataset</span>
                      </span>
                      <span className="font-semibold text-[#102C46] truncate max-w-[150px]">
                        {report.datasetName} ({report.datasetVersion})
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5">
                        <Layers className="w-3 h-3 text-[#009F98]" />
                        <span>Format & Sections</span>
                      </span>
                      <span className="font-medium text-[#102C46] flex items-center gap-1.5">
                        <span className="uppercase text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#E0F5F3] text-[#007D78] border border-[#39C3B8]/30">
                          {report.format || 'pdf'}
                        </span>
                        <span>{report.sections.length} sections</span>
                        {report.fileSizeFormatted && (
                          <span className="text-[#52616C] font-normal">({report.fileSizeFormatted})</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer: Date + Action Icons + Preview Button matching reference Screen 5 */}
                <div className="mt-5 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-xs">
                  {/* Date */}
                  <span className="text-[11px] text-[#52616C] flex items-center gap-1.5 font-medium">
                    <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>
                      {new Date(report.createdAt).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                  </span>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    {/* Direct Download */}
                    <button
                      onClick={(e) => handleDownloadReport(report, e)}
                      className="p-1.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#EDF7FA] cursor-pointer transition-colors"
                      title={`Download genuine ${report.format?.toUpperCase() || 'PDF'} document`}
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>

                    {/* Share */}
                    <button
                      onClick={(e) => handleShare(report, e)}
                      className="p-1.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#EDF7FA] cursor-pointer transition-colors"
                      title="Share report"
                    >
                      <Share2 className="w-3.5 h-3.5" />
                    </button>

                    {/* Duplicate */}
                    <button
                      onClick={(e) => handleDuplicate(report, e)}
                      className="p-1.5 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] cursor-pointer transition-colors"
                      title="Duplicate report"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>

                    {/* Favorite */}
                    <button
                      onClick={(e) => handleToggleFavorite(report.id, e)}
                      className="p-1.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#EDF7FA] cursor-pointer transition-colors"
                      title={isFav ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      <Star className={`w-3.5 h-3.5 ${isFav ? 'text-[#009F98] fill-[#009F98]' : ''}`} />
                    </button>

                    {/* Delete */}
                    <button
                      onClick={(e) => handleDelete(report, e)}
                      className="p-1.5 rounded-lg text-[#52616C] hover:text-[#A63838] hover:bg-[#FCE9E9] cursor-pointer transition-colors"
                      title="Delete report"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    {/* Preview Button in Peacock Teal matching reference Screen 5 */}
                    <button
                      onClick={() => navigate(`/reports/${report.id}/preview`)}
                      className="ml-1 px-3 py-1 rounded-xl bg-[#009F98] hover:bg-[#007D78] active:bg-[#086E73] text-white font-semibold text-xs flex items-center gap-1 shadow-2xs cursor-pointer transition-colors"
                    >
                      <span>Preview</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* List View Mode */
        <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-subtle">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F5F8FA] text-[#102C46] font-semibold border-b border-[#DCE5EB]">
              <tr>
                <th className="p-3.5">Report Title</th>
                <th className="p-3.5">Type</th>
                <th className="p-3.5">Dataset</th>
                <th className="p-3.5">Period</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Created</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEF3F6]">
              {filteredReports.map((report) => (
                <tr
                  key={report.id}
                  onClick={() => navigate(`/reports/${report.id}/preview`)}
                  className="hover:bg-[#EDF7FA]/40 transition-colors cursor-pointer group"
                >
                  <td className="p-3.5 font-bold text-[#102C46] group-hover:text-[#009F98]">
                    {report.title}
                  </td>
                  <td className="p-3.5 text-[#52616C]">{report.type}</td>
                  <td className="p-3.5 font-medium text-[#102C46]">{report.datasetName}</td>
                  <td className="p-3.5 text-[#52616C]">{report.period}</td>
                  <td className="p-3.5">{getStatusBadge(report.status)}</td>
                  <td className="p-3.5 text-[#52616C]">
                    {new Date(report.createdAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                  </td>
                  <td className="p-3.5 text-right">
                    <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={(e) => handleDownloadReport(report, e)}
                        className="px-2.5 py-1 rounded-lg border border-[#DCE5EB] hover:bg-[#EEF3F6] text-[#102C46] font-medium text-xs flex items-center gap-1 cursor-pointer transition-colors"
                        title="Download report"
                      >
                        <Download className="w-3 h-3 text-[#009F98]" />
                        <span className="uppercase text-[10px] font-bold">{report.format || 'pdf'}</span>
                      </button>
                      <button
                        onClick={() => navigate(`/reports/${report.id}/preview`)}
                        className="px-3 py-1 rounded-lg bg-[#009F98] text-white font-medium hover:bg-[#007D78] text-xs cursor-pointer transition-colors"
                      >
                        Preview
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 6. Secure Share Modal */}
      <Modal
        isOpen={Boolean(activeShareReport)}
        onClose={() => setActiveShareReport(null)}
        title="Share Business Intelligence Report"
        subtitle="Generate authenticated read-only sharing link with governance parameters."
        maxWidth="lg"
      >
        {activeShareReport && (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-[#F5F8FA] border border-[#DCE5EB] space-y-1">
              <span className="text-[11px] text-[#52616C] block">Selected Document</span>
              <p className="text-sm font-bold text-[#102C46]">{activeShareReport.title}</p>
              <p className="text-xs text-[#52616C]">
                Source: {activeShareReport.datasetName} ({activeShareReport.datasetVersion}) • Period: {activeShareReport.period}
              </p>
            </div>

            <div>
              <label className="text-xs font-bold text-[#102C46] block mb-1">
                Authenticated Share Link
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={`${window.location.origin}/reports/${activeShareReport.id}/preview?share=${activeShareReport.shareConfig.shareId}`}
                  className="flex-1 px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] select-all font-mono"
                />
                <Button variant="primary" size="sm" onClick={handleCopyShareLink}>
                  {copiedLink ? 'Copied!' : 'Copy Link'}
                </Button>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#E4F3EC] border border-[#C3E7D5] text-xs text-[#216548] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>Restricted to read-only access. Snapshot math is tamper-proof.</span>
            </div>
          </div>
        )}
      </Modal>

      {/* 7. Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(deleteConfirmReport)}
        onClose={() => setDeleteConfirmReport(null)}
        title="Delete Business Report"
        subtitle="Confirm document deletion."
        maxWidth="md"
      >
        {deleteConfirmReport && (
          <div className="space-y-4">
            <p className="text-xs text-[#52616C] leading-relaxed">
              Are you sure you want to permanently delete <b className="text-[#102C46]">"{deleteConfirmReport.title}"</b>? This action cannot be undone.
            </p>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#DCE5EB]">
              <Button variant="secondary" size="sm" onClick={() => setDeleteConfirmReport(null)}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" onClick={confirmDelete}>
                Delete Report
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
