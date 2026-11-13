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
import { Button } from '../../components/common/Button';

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

  // Mode: edit mode (builder controls) vs presentation view
  const [isEditMode, setIsEditMode] = useState<boolean>(true);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<'clean' | 'dirty' | 'saved' | 'saving'>('clean');

  // Modals state
  const [isWidgetModalOpen, setIsWidgetModalOpen] = useState<boolean>(false);
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null);
  const [isFilterModalOpen, setIsFilterModalOpen] = useState<boolean>(false);
  const [editingFilter, setEditingFilter] = useState<DashboardFilter | null>(null);

  // Export dropdown
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  // Runtime active filter state: map of column_name -> { column, operator, value }
  const [filterState, setFilterState] = useState<Record<string, { column: string; operator: string; value: any }>>({});

  // Runtime interactive cross-filters clicked from charts / tables
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
  };

  // Cross-filtering interactions
  const handleCrossFilter = (filter: { column: string; operator: string; value: any }) => {
    const { column, value } = filter;
    setCrossFilterState((prev) => {
      const next = { ...prev };
      // Toggle off if already selected with same value
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

  const handleClearCrossFilters = () => {
    setCrossFilterState({});
  };

  const activeCrossFilterList = useMemo(() => Object.values(crossFilterState), [crossFilterState]);

  // Combined dashboard filters + cross-filters
  const combinedFilterList = useMemo(() => {
    const map = new Map<string, { column: string; operator: string; value: any }>();
    Object.values(filterState).forEach((f) => map.set(f.column, f));
    Object.values(crossFilterState).forEach((f) => map.set(f.column, f));
    return Array.from(map.values());
  }, [filterState, crossFilterState]);

  const activeFilterList = useMemo(() => Object.values(filterState), [filterState]);

  // Widget Actions
  const handleOpenAddWidget = () => {
    setEditingWidget(null);
    setIsWidgetModalOpen(true);
  };

  const handleEditWidget = (w: DashboardWidget) => {
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

    // Update positions sequentially
    const updated = copy.map((w, i) => ({ ...w, grid_y: i }));
    setWidgets(updated);
    setIsDirty(true);
    setSaveStatus('dirty');
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

      // 1. Update metadata
      await dashboardService.updateDashboard(workspaceId, dashboardId, {
        title: dashboard.title,
        description: dashboard.description,
        visibility: dashboard.visibility,
        layout_config: dashboard.layout_config,
      });

      // 2. Persist layout
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
    <div className="space-y-6 pb-20 animate-in fade-in duration-150">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/dashboards')}
            className="w-8 h-8 rounded-xl bg-[#F5F8FA] hover:bg-[#EEF3F6] border border-[#DCE5EB] flex items-center justify-center text-[#52616C] hover:text-[#102C46] transition-colors cursor-pointer"
            title="Back to Dashboards"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={dashboard.title}
                disabled={!isEditMode}
                onChange={(e) => {
                  setDashboard({ ...dashboard, title: e.target.value });
                  setIsDirty(true);
                  setSaveStatus('dirty');
                }}
                className={`text-lg sm:text-xl font-extrabold text-[#102C46] bg-transparent focus:outline-none focus:border-b-2 focus:border-[#009F98] transition-all max-w-sm sm:max-w-md truncate ${
                  isEditMode ? 'hover:bg-[#F5F8FA] px-1 rounded' : ''
                }`}
              />
              <span className="text-[10px] font-bold text-[#009F98] bg-[#EDF7FA] px-2 py-0.5 rounded-full border border-[#BBDCE8] uppercase tracking-wider">
                {isEditMode ? 'Edit Mode' : 'View Mode'}
              </span>
            </div>
            {dashboard.description && (
              <p className="text-xs text-[#52616C] truncate mt-0.5 max-w-lg">
                {dashboard.description}
              </p>
            )}
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* View / Edit Mode Switch */}
          <div className="flex items-center bg-[#F5F8FA] p-1 rounded-xl border border-[#DCE5EB]">
            <button
              type="button"
              onClick={() => setIsEditMode(false)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
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
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isEditMode
                  ? 'bg-[#009F98] text-white shadow-2xs font-bold'
                  : 'text-[#52616C] hover:text-[#102C46]'
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" />
              Edit
            </button>
          </div>

          {/* Edit Actions: Add Widget & Filter */}
          {isEditMode && (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={handleOpenAddWidget}
                leftIcon={<Plus className="w-3.5 h-3.5" />}
              >
                Add Widget
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenAddFilter}
                leftIcon={<SlidersHorizontal className="w-3.5 h-3.5 text-[#009F98]" />}
              >
                Add Filter
              </Button>
            </>
          )}

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

          {/* Save Status & Button */}
          {isEditMode && (
            <div className="flex items-center gap-2 pl-1">
              <Button
                variant={isDirty ? 'primary' : 'outline'}
                size="sm"
                onClick={handleSaveDashboard}
                isLoading={saving}
                leftIcon={
                  saveStatus === 'saved' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )
                }
              >
                {saveStatus === 'saved'
                  ? 'Saved'
                  : isDirty
                  ? 'Save Changes'
                  : 'Saved'}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838] flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold underline">Dismiss</button>
        </div>
      )}

      {/* Interactive Filter Bar */}
      <DashboardFilterBar
        filters={filters}
        activeValues={filterState}
        onFilterChange={handleFilterChange}
        onClearFilters={handleClearFilters}
        onAddFilter={handleOpenAddFilter}
        onDeleteFilter={handleDeleteFilter}
        isEditMode={isEditMode}
      />

      {/* Active Cross-Filters Banner */}
      {activeCrossFilterList.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-[#EDF7FA] border border-[#BBDCE8] rounded-xl text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 font-bold text-[#102C46]">
              <Filter className="w-3.5 h-3.5 text-[#009F98]" />
              Interactive Cross-Filters:
            </span>
            {activeCrossFilterList.map((cf) => (
              <span
                key={cf.column}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border border-[#BBDCE8] rounded-lg text-[#102C46] font-medium shadow-2xs text-[11px]"
              >
                <strong className="text-[#009F98]">{cf.column}:</strong> {String(cf.value)}
                <button
                  type="button"
                  onClick={() => handleRemoveCrossFilter(cf.column)}
                  className="text-[#52616C] hover:text-red-500 transition-colors ml-0.5 cursor-pointer"
                  title="Remove cross-filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>

          <button
            type="button"
            onClick={handleClearCrossFilters}
            className="text-[11px] font-bold text-[#009F98] hover:text-[#007D78] underline cursor-pointer"
          >
            Clear All Cross-Filters
          </button>
        </div>
      )}

      {/* 12-Column Responsive Dashboard Grid */}
      {widgets.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-[#DCE5EB] p-8">
          <div className="w-12 h-12 bg-[#EDF7FA] rounded-xl flex items-center justify-center text-[#009F98] mx-auto mb-3">
            <Layers className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-[#102C46]">Empty Dashboard</h3>
          <p className="text-xs text-[#52616C] max-w-sm mx-auto mt-1 mb-5">
            Add KPI cards, bar charts, time-series lines, breakdown pies, or data tables to construct your dashboard.
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
        <div className="grid grid-cols-12 gap-5 items-start">
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
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            />
          ))}
        </div>
      )}

      {/* Widget Configuration Modal */}
      <WidgetConfigModal
        isOpen={isWidgetModalOpen}
        onClose={() => setIsWidgetModalOpen(false)}
        onSave={handleSaveWidget}
        workspaceId={workspaceId}
        initialWidget={editingWidget}
      />

      {/* Filter Configuration Modal */}
      <FilterConfigModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        onSave={handleSaveFilter}
        initialFilter={editingFilter}
      />
    </div>
  );
};

