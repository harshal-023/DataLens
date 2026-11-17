import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  Save,
  Download,
  Eye,
  Edit3,
  SlidersHorizontal,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  FileText,
  FileCode,
  Layers,
  ChevronDown,
  Filter,
  X,
  Share2,
  MoreVertical,
  Palette,
  BarChart3,
  LineChart as LineIcon,
  AreaChart as AreaIcon,
  PieChart as PieIcon,
  Table as TableIcon,
  Hash,
  Sparkles,
  Check,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  dashboardService,
  Dashboard,
  DashboardWidget,
  DashboardFilter,
} from '../../services/dashboardService';
import { DashboardWidgetCard } from '../../components/dashboards/DashboardWidgetCard';
import { DashboardFilterBar } from '../../components/dashboards/DashboardFilterBar';
import { WidgetConfigModal } from '../../components/dashboards/WidgetConfigModal';
import { FilterConfigModal } from '../../components/dashboards/FilterConfigModal';
import { DashboardThemeModal } from '../../components/dashboards/DashboardThemeModal';
import { getDashboardTheme, DASHBOARD_THEMES } from '../../components/dashboards/DashboardThemes';
import { Button } from '../../components/common/Button';

// Add Widget panel tiles (Matching reference image)
const ADD_WIDGET_TILES = [
  {
    type: 'kpi',
    label: 'KPI Card',
    icon: Hash,
    bg: 'bg-[#EDF8F7]',
    text: 'text-[#009F98]',
    hover: 'hover:bg-[#DCF3F1]',
  },
  {
    type: 'bar',
    label: 'Bar Chart',
    icon: BarChart3,
    bg: 'bg-[#EDF5FB]',
    text: 'text-[#2563EB]',
    hover: 'hover:bg-[#DDECF8]',
  },
  {
    type: 'line',
    label: 'Line Chart',
    icon: LineIcon,
    bg: 'bg-[#F6F0FA]',
    text: 'text-[#8B5CF6]',
    hover: 'hover:bg-[#EEDEF6]',
  },
  {
    type: 'area',
    label: 'Area Chart',
    icon: AreaIcon,
    bg: 'bg-[#FDF2F8]',
    text: 'text-[#EC4899]',
    hover: 'hover:bg-[#FCE3F1]',
  },
  {
    type: 'donut',
    label: 'Pie / Donut',
    icon: PieIcon,
    bg: 'bg-[#FEF7EC]',
    text: 'text-[#F59E0B]',
    hover: 'hover:bg-[#FDEED5]',
  },
  {
    type: 'table',
    label: 'Table',
    icon: TableIcon,
    bg: 'bg-[#ECFDF5]',
    text: 'text-[#10B981]',
    hover: 'hover:bg-[#D3F9E5]',
  },
  {
    type: 'text',
    label: 'Text / Insight',
    icon: FileText,
    bg: 'bg-[#EEF2FF]',
    text: 'text-[#6366F1]',
    hover: 'hover:bg-[#E0E7FF]',
  },
];

export const DashboardEditor: React.FC = () => {
  const { dashboardId } = useParams<{ dashboardId: string }>();
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [filters, setFilters] = useState<DashboardFilter[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Mode: edit mode vs presentation view
  const [isEditMode, setIsEditMode] = useState<boolean>(true);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<'clean' | 'dirty' | 'saved' | 'saving'>('clean');

  // Inline title editing
  const [isEditingTitle, setIsEditingTitle] = useState<boolean>(false);
  const [titleInput, setTitleInput] = useState<string>('');

  // Modals state
  const [isWidgetModalOpen, setIsWidgetModalOpen] = useState<boolean>(false);
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null);
  const [selectedWidgetTypeForModal, setSelectedWidgetTypeForModal] = useState<string>('kpi');

  const [isFilterModalOpen, setIsFilterModalOpen] = useState<boolean>(false);
  const [editingFilter, setEditingFilter] = useState<DashboardFilter | null>(null);

  const [isThemeModalOpen, setIsThemeModalOpen] = useState<boolean>(false);

  // Dropdown states
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [isMoreMenuOpen, setIsMoreMenuOpen] = useState<boolean>(false);
  const [shareToast, setShareToast] = useState<boolean>(false);

  // Runtime active filter state
  const [filterState, setFilterState] = useState<Record<string, { column: string; operator: string; value: any }>>({});
  const [crossFilterState, setCrossFilterState] = useState<Record<string, { column: string; operator: string; value: any }>>({});

  // Drag and drop state
  const [draggedWidgetId, setDraggedWidgetId] = useState<string | null>(null);

  // Fetch full dashboard
  const loadDashboard = useCallback(async () => {
    if (!workspaceId || !dashboardId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await dashboardService.getDashboard(workspaceId, dashboardId);
      setDashboard(data);
      setTitleInput(data.title);
      setWidgets(data.widgets || []);
      setFilters(data.filters || []);
      setIsDirty(false);
      setSaveStatus('clean');
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, dashboardId]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Active theme calculation
  const currentTheme = useMemo(() => {
    return getDashboardTheme(dashboard?.layout_config?.theme);
  }, [dashboard?.layout_config?.theme]);

  // Handle Theme Change
  const handleSelectTheme = async (themeId: string) => {
    if (!dashboard || !workspaceId || !dashboardId) return;
    const newLayoutConfig = {
      ...(dashboard.layout_config || {}),
      theme: themeId,
    };
    setDashboard({ ...dashboard, layout_config: newLayoutConfig });
    setIsDirty(true);
    setSaveStatus('dirty');

    try {
      await dashboardService.updateDashboard(workspaceId, dashboardId, {
        layout_config: newLayoutConfig,
      });
      setSaveStatus('clean');
      setIsDirty(false);
    } catch (e) {
      // Keep dirty if network fails
    }
  };

  // Handle Interactive Filter Change
  const handleFilterChange = (column: string, operator: string, value: any) => {
    setFilterState((prev) => {
      const next = { ...prev };
      if (value === null || value === '' || value === undefined) {
        delete next[column];
      } else {
        next[column] = { column, operator, value };
      }
      return next;
    });
  };

  const handleClearFilters = () => {
    setFilterState({});
    setCrossFilterState({});
  };

  // Cross-filtering interactions
  const handleCrossFilter = (filter: { column: string; operator: string; value: any }) => {
    const { column, value } = filter;
    setCrossFilterState((prev) => {
      const next = { ...prev };
      if (next[column] && next[column].value === value) {
        delete next[column];
      } else {
        next[column] = { column, operator: 'equals', value };
      }
      return next;
    });
  };

  const handleRemoveCrossFilter = (column: string) => {
    setCrossFilterState((prev) => {
      const next = { ...prev };
      delete next[column];
      return next;
    });
  };

  const activeCrossFilterList = useMemo(() => Object.values(crossFilterState), [crossFilterState]);

  // Combined dashboard filters + cross-filters
  const combinedFilterList = useMemo(() => {
    const map = new Map<string, { column: string; operator: string; value: any }>();
    Object.values(filterState).forEach((f) => map.set(f.column, f));
    Object.values(crossFilterState).forEach((f) => map.set(f.column, f));
    return Array.from(map.values());
  }, [filterState, crossFilterState]);

  // Open Add Widget modal from quick palette tile
  const handleAddWidgetFromTile = (type: string) => {
    setSelectedWidgetTypeForModal(type);
    setEditingWidget(null);
    setIsWidgetModalOpen(true);
  };

  const handleOpenAddWidget = () => {
    setSelectedWidgetTypeForModal('kpi');
    setEditingWidget(null);
    setIsWidgetModalOpen(true);
  };

  const handleEditWidget = (w: DashboardWidget) => {
    setSelectedWidgetTypeForModal(w.widget_type);
    setEditingWidget(w);
    setIsWidgetModalOpen(true);
  };

  const handleSaveWidget = async (widgetData: Partial<DashboardWidget>) => {
    if (!workspaceId || !dashboardId) return;

    if (editingWidget) {
      const updated = await dashboardService.updateWidget(
        workspaceId,
        dashboardId,
        editingWidget.id,
        widgetData
      );
      setWidgets((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
    } else {
      const created = await dashboardService.addWidget(workspaceId, dashboardId, widgetData);
      setWidgets((prev) => [...prev, created]);
    }
    setIsDirty(true);
    setSaveStatus('dirty');
  };

  const handleDeleteWidget = async (widgetId: string) => {
    if (!workspaceId || !dashboardId) return;
    try {
      await dashboardService.deleteWidget(workspaceId, dashboardId, widgetId);
      setWidgets((prev) => prev.filter((w) => w.id !== widgetId));
      setIsDirty(true);
      setSaveStatus('dirty');
    } catch (err: any) {
      setError(err?.message || 'Failed to remove widget.');
    }
  };

  const handleResizeWidget = async (widgetId: string, deltaW: number, deltaH: number) => {
    setWidgets((prev) =>
      prev.map((w) => {
        if (w.id === widgetId) {
          const newW = Math.min(Math.max(w.grid_w + deltaW, 3), 12);
          const newH = Math.min(Math.max(w.grid_h + deltaH, 2), 12);
          return { ...w, grid_w: newW, grid_h: newH };
        }
        return w;
      })
    );
    setIsDirty(true);
    setSaveStatus('dirty');
  };

  const handleMoveWidget = (widgetId: string, direction: 'up' | 'down') => {
    const idx = widgets.findIndex((w) => w.id === widgetId);
    if (idx === -1) return;
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= widgets.length) return;

    const copy = [...widgets];
    const [moved] = copy.splice(idx, 1);
    copy.splice(targetIdx, 0, moved);

    const updated = copy.map((w, i) => ({ ...w, grid_y: i }));
    setWidgets(updated);
    setIsDirty(true);
    setSaveStatus('dirty');
  };

  const handleUpdateWidgetSettings = async (widgetId: string, displaySettings: Record<string, any>) => {
    if (!workspaceId || !dashboardId) return;
    try {
      const updated = await dashboardService.updateWidget(workspaceId, dashboardId, widgetId, {
        display_settings: displaySettings,
      });
      setWidgets((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
    } catch (e) {
      // Fallback
    }
  };

  // Drag and Drop handlers
  const handleDragStart = (_e: React.DragEvent, widgetId: string) => {
    setDraggedWidgetId(widgetId);
  };

  const handleDragOver = (e: React.DragEvent, _widgetId: string) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetWidgetId: string) => {
    e.preventDefault();
    if (!draggedWidgetId || draggedWidgetId === targetWidgetId) return;

    const sourceIdx = widgets.findIndex((w) => w.id === draggedWidgetId);
    const targetIdx = widgets.findIndex((w) => w.id === targetWidgetId);
    if (sourceIdx === -1 || targetIdx === -1) return;

    const copy = [...widgets];
    const [moved] = copy.splice(sourceIdx, 1);
    copy.splice(targetIdx, 0, moved);

    const updated = copy.map((w, i) => ({ ...w, grid_y: i }));
    setWidgets(updated);
    setDraggedWidgetId(null);
    setIsDirty(true);
    setSaveStatus('dirty');
  };

  // Filter Actions
  const handleOpenAddFilter = () => {
    setEditingFilter(null);
    setIsFilterModalOpen(true);
  };

  const handleSaveFilter = async (filterData: Partial<DashboardFilter>) => {
    if (!workspaceId || !dashboardId) return;

    if (editingFilter) {
      const updated = await dashboardService.updateFilter(
        workspaceId,
        dashboardId,
        editingFilter.id,
        filterData
      );
      setFilters((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
    } else {
      const created = await dashboardService.addFilter(workspaceId, dashboardId, filterData);
      setFilters((prev) => [...prev, created]);
    }
  };

  const handleDeleteFilter = async (filterId: string) => {
    if (!workspaceId || !dashboardId) return;
    try {
      await dashboardService.deleteFilter(workspaceId, dashboardId, filterId);
      setFilters((prev) => prev.filter((f) => f.id !== filterId));
    } catch (err: any) {
      setError(err?.message || 'Failed to remove filter.');
    }
  };

  // Save full dashboard changes
  const handleSaveDashboard = async () => {
    if (!workspaceId || !dashboardId || !dashboard) return;
    try {
      setSaving(true);
      setSaveStatus('saving');

      await dashboardService.updateDashboard(workspaceId, dashboardId, {
        title: dashboard.title,
        description: dashboard.description,
        visibility: dashboard.visibility,
        layout_config: dashboard.layout_config,
      });

      const layoutPayload = widgets.map((w, idx) => ({
        id: w.id,
        grid_x: w.grid_x,
        grid_y: idx,
        grid_w: w.grid_w,
        grid_h: w.grid_h,
      }));
      await dashboardService.updateLayout(workspaceId, dashboardId, layoutPayload);

      setIsDirty(false);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('clean'), 2000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save dashboard.');
      setSaveStatus('dirty');
    } finally {
      setSaving(false);
    }
  };

  // Save inline title
  const handleSaveTitle = async () => {
    if (!titleInput.trim() || !dashboard || !workspaceId || !dashboardId) return;
    setIsEditingTitle(false);
    if (titleInput.trim() === dashboard.title) return;

    setDashboard({ ...dashboard, title: titleInput.trim() });
    try {
      await dashboardService.updateDashboard(workspaceId, dashboardId, {
        title: titleInput.trim(),
      });
    } catch (e) {
      // Fallback
    }
  };

  // Share Dashboard Link
  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setShareToast(true);
    setTimeout(() => setShareToast(false), 2500);
  };

  // Export Dashboard Action
  const handleExport = async (format: 'pdf' | 'csv' | 'xlsx') => {
    if (!workspaceId || !dashboardId || !dashboard) return;
    try {
      setExporting(true);
      setIsExportOpen(false);

      const blob = await dashboardService.exportDashboard(
        workspaceId,
        dashboardId,
        format,
        combinedFilterList
      );

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dashboard.title.toLowerCase().replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err?.message || `Failed to export ${format.toUpperCase()}`);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
        <span className="text-xs text-[#52616C] font-medium">Loading dashboard and widgets...</span>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="text-center py-16">
        <h3 className="text-base font-bold text-[#102C46]">Dashboard not found</h3>
        <Button variant="secondary" size="md" onClick={() => navigate('/dashboards')} className="mt-4">
          Return to Dashboards
        </Button>
      </div>
    );
  }

  return (
    <div
      className="h-full flex flex-col min-h-0 overflow-hidden animate-in fade-in duration-150"
      style={{ backgroundColor: currentTheme.canvasBg }}
    >
      {/* ------------------------------------------------------------- */}
      {/* STATIONARY TOP HEADER BAR (Matching Reference Image) */}
      {/* ------------------------------------------------------------- */}
      <div className="shrink-0 pb-3">
        {/* Section title pill */}
        <div className="text-xs font-bold text-[#52616C] mb-2 px-1">
          Analytics &amp; Dashboards
        </div>

        {/* White Rounded Header Card */}
        <div
          className="rounded-2xl border p-4 shadow-2xs flex flex-col md:flex-row md:items-center md:justify-between gap-4"
          style={{
            backgroundColor: currentTheme.headerBg,
            borderColor: currentTheme.borderColor,
          }}
        >
          {/* Left: Brand Icon, Title with Pencil, and Dataset Subtitle */}
          <div className="flex items-center gap-3 min-w-0">
            {/* Teal Square Icon with 3 Bars */}
            <div className="w-10 h-10 rounded-xl bg-[#EDF8F7] text-[#009F98] flex items-center justify-center shrink-0 shadow-2xs">
              <BarChart3 className="w-5 h-5 stroke-[2.5]" />
            </div>

            <div className="min-w-0">
              {/* Title with Inline Pencil */}
              <div className="flex items-center gap-2">
                {isEditingTitle ? (
                  <input
                    type="text"
                    autoFocus
                    value={titleInput}
                    onChange={(e) => setTitleInput(e.target.value)}
                    onBlur={handleSaveTitle}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                    className="text-lg sm:text-xl font-extrabold text-[#102C46] bg-[#F5F8FA] border border-[#009F98] rounded-lg px-2 py-0.5 focus:outline-none"
                  />
                ) : (
                  <h1 className="text-lg sm:text-xl font-extrabold text-[#102C46] tracking-tight truncate flex items-center gap-2">
                    <span>{dashboard.title}</span>
                    {isEditMode && (
                      <button
                        type="button"
                        onClick={() => setIsEditingTitle(true)}
                        className="text-[#52616C] hover:text-[#009F98] transition-colors p-1 rounded-lg hover:bg-[#F5F8FA] cursor-pointer"
                        title="Rename Dashboard"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </h1>
                )}
              </div>

              {/* Subtitle with Dataset and Row Count */}
              <p className="text-xs text-[#52616C] truncate mt-0.5 font-medium">
                Dataset: {dashboard.description || 'Business Sales (4,115 rows)'}
              </p>
            </div>
          </div>

          {/* Right Toolbar Controls (View/Edit Pill, Share, Export, 3-Dots) */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* View / Edit Mode Pill Toggle */}
            <div className="flex items-center bg-[#F5F8FA] p-1 rounded-xl border border-[#DCE5EB]">
              <button
                type="button"
                onClick={() => setIsEditMode(false)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  !isEditMode
                    ? 'bg-white text-[#102C46] shadow-2xs font-bold'
                    : 'text-[#52616C] hover:text-[#102C46]'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                View
              </button>
              <button
                type="button"
                onClick={() => setIsEditMode(true)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  isEditMode
                    ? 'bg-[#009F98] text-white shadow-2xs font-bold'
                    : 'text-[#52616C] hover:text-[#102C46]'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit
              </button>
            </div>

            {/* Share Button */}
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
                leftIcon={<Share2 className="w-3.5 h-3.5 text-[#009F98]" />}
              >
                Share
              </Button>
              {shareToast && (
                <div className="absolute right-0 top-10 bg-[#102C46] text-white text-[11px] px-2.5 py-1 rounded-lg shadow-lg whitespace-nowrap z-50 animate-in fade-in">
                  Link copied to clipboard!
                </div>
              )}
            </div>

            {/* Export Dropdown */}
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsExportOpen(!isExportOpen)}
                isLoading={exporting}
                leftIcon={<Download className="w-3.5 h-3.5 text-[#009F98]" />}
                rightIcon={<ChevronDown className="w-3 h-3 text-[#52616C]" />}
              >
                Export
              </Button>

              {isExportOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-[#DCE5EB] py-1.5 z-40 animate-in fade-in duration-100">
                  <button
                    type="button"
                    onClick={() => handleExport('pdf')}
                    className="w-full text-left px-3.5 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                  >
                    <FileText className="w-4 h-4 text-[#009F98]" />
                    Download PDF Report
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExport('xlsx')}
                    className="w-full text-left px-3.5 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-[#009F98]" />
                    Download Excel (XLSX)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExport('csv')}
                    className="w-full text-left px-3.5 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                  >
                    <FileCode className="w-4 h-4 text-[#009F98]" />
                    Download CSV Data
                  </button>
                </div>
              )}
            </div>

            {/* Save Status & Button (In Edit Mode) */}
            {isEditMode && isDirty && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveDashboard}
                isLoading={saving}
                leftIcon={<Save className="w-3.5 h-3.5" />}
              >
                Save
              </Button>
            )}

            {/* 3-Dots More Options Menu */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsMoreMenuOpen(!isMoreMenuOpen)}
                className="w-8 h-8 rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] hover:bg-[#EEF3F6] flex items-center justify-center text-[#52616C] hover:text-[#102C46] transition-colors cursor-pointer"
                title="More Options"
              >
                <MoreVertical className="w-4 h-4" />
              </button>

              {isMoreMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-[#DCE5EB] py-1.5 z-40 animate-in fade-in duration-100">
                  <button
                    type="button"
                    onClick={() => {
                      setIsMoreMenuOpen(false);
                      setIsThemeModalOpen(true);
                    }}
                    className="w-full text-left px-3.5 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                  >
                    <Palette className="w-4 h-4 text-[#009F98]" />
                    Dashboard Theme &amp; Style
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsMoreMenuOpen(false);
                      loadDashboard();
                    }}
                    className="w-full text-left px-3.5 py-2 text-xs font-medium text-[#52616C] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                  >
                    Refresh Dashboard Data
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dashboard Filter Bar (Stationary under header) */}
        <div className="mt-3">
          <DashboardFilterBar
            filters={filters}
            activeValues={filterState}
            onFilterChange={handleFilterChange}
            onClearFilters={handleClearFilters}
            onAddFilter={handleOpenAddFilter}
            onDeleteFilter={handleDeleteFilter}
            isEditMode={isEditMode}
          />
        </div>

        {/* Active Cross-Filters Pill Bar */}
        {activeCrossFilterList.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2 bg-[#EDF7FA] border border-[#BBDCE8] rounded-xl text-xs mb-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 font-bold text-[#102C46]">
                <Filter className="w-3.5 h-3.5 text-[#009F98]" />
                Interactive Filters:
              </span>
              {activeCrossFilterList.map((cf) => (
                <span
                  key={cf.column}
                  className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-white border border-[#BBDCE8] rounded-lg text-[#102C46] font-medium shadow-2xs text-[11px]"
                >
                  <strong className="text-[#009F98]">{cf.column}:</strong> {String(cf.value)}
                  <button
                    type="button"
                    onClick={() => handleRemoveCrossFilter(cf.column)}
                    className="text-[#52616C] hover:text-red-500 transition-colors ml-0.5 cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            <button
              type="button"
              onClick={handleClearFilters}
              className="text-[11px] font-bold text-[#009F98] hover:text-[#007D78] underline cursor-pointer"
            >
              Clear Cross-Filters
            </button>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* MAIN CONTENT AREA: SCROLLABLE CANVAS + DOCKED ADD WIDGET PANEL */}
      {/* ------------------------------------------------------------- */}
      <div className="flex-1 min-h-0 flex items-start gap-5 overflow-hidden">
        {/* Left: Scrollable Canvas */}
        <div className="flex-1 h-full min-h-0 overflow-y-auto pr-2 pb-16">
          {widgets.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-[#DCE5EB] p-8">
              <div className="w-12 h-12 bg-[#EDF7FA] rounded-2xl flex items-center justify-center text-[#009F98] mx-auto mb-3">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-[#102C46]">Your Dashboard is Empty</h3>
              <p className="text-xs text-[#52616C] max-w-sm mx-auto mt-1 mb-5">
                Pick a widget from the right panel to begin constructing your sales and performance dashboard.
              </p>
              <Button
                variant="primary"
                size="md"
                onClick={handleOpenAddWidget}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                Add Your First Widget
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-12 gap-4 sm:gap-5 items-start">
              {widgets.map((widget) => (
                <DashboardWidgetCard
                  key={widget.id}
                  widget={widget}
                  workspaceId={workspaceId}
                  isEditMode={isEditMode}
                  activeFilters={combinedFilterList}
                  onCrossFilter={handleCrossFilter}
                  onEditWidget={handleEditWidget}
                  onDeleteWidget={handleDeleteWidget}
                  onResizeWidget={handleResizeWidget}
                  onMoveWidget={handleMoveWidget}
                  onUpdateWidgetSettings={handleUpdateWidgetSettings}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  cardBg={currentTheme.cardBg}
                  borderColor={currentTheme.borderColor}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Docked "Add Widget" Panel (Matching Reference Image) */}
        {isEditMode && (
          <div className="w-[230px] shrink-0 bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-2xs h-fit animate-in fade-in duration-200">
            <h3 className="text-sm font-bold text-[#102C46]">Add Widget</h3>
            <p className="text-[11px] text-[#52616C] mt-0.5 mb-4 leading-snug">
              Choose a widget and add it to your dashboard.
            </p>

            {/* 2-Column Pastel Tile Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              {ADD_WIDGET_TILES.map((t) => {
                const Icon = t.icon;

                return (
                  <button
                    key={t.type}
                    type="button"
                    onClick={() => handleAddWidgetFromTile(t.type)}
                    className={`${t.bg} ${t.hover} rounded-2xl p-3 flex flex-col items-center justify-center text-center transition-all duration-150 cursor-pointer shadow-2xs hover:scale-102 hover:shadow-xs group`}
                    style={{ minHeight: '80px' }}
                  >
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center mb-1.5 ${t.text}`}
                    >
                      <Icon className="w-5 h-5 transition-transform group-hover:scale-110" />
                    </div>
                    <span className="text-[11px] font-bold text-[#102C46] leading-tight">
                      {t.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Widget Configuration Wizard Modal */}
      <WidgetConfigModal
        isOpen={isWidgetModalOpen}
        onClose={() => setIsWidgetModalOpen(false)}
        onSave={handleSaveWidget}
        workspaceId={workspaceId}
        initialWidget={editingWidget}
        defaultWidgetType={selectedWidgetTypeForModal}
      />

      {/* Filter Configuration Modal */}
      <FilterConfigModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        onSave={handleSaveFilter}
        initialFilter={editingFilter}
      />

      {/* Dashboard Appearance & Theme Modal */}
      <DashboardThemeModal
        isOpen={isThemeModalOpen}
        onClose={() => setIsThemeModalOpen(false)}
        currentThemeId={dashboard.layout_config?.theme || 'clean_light'}
        onSelectTheme={handleSelectTheme}
      />
    </div>
  );
};
