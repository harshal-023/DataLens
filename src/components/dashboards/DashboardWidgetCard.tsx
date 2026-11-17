import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  GripVertical,
  MoreVertical,
  Edit3,
  Copy,
  ArrowUp,
  ArrowDown,
  Palette,
  Trash2,
  RefreshCw,
  AlertCircle,
  Clock,
  ChevronRight,
  Maximize2,
  Minimize2,
  Sparkles,
  Settings,
} from 'lucide-react';
import { DashboardWidget, dashboardService, WidgetQueryResponse } from '../../services/dashboardService';
import { WidgetVisualization } from './WidgetVisualizations';
import { COLOR_PALETTES } from './DashboardThemes';

export interface DashboardWidgetCardProps {
  widget: DashboardWidget;
  workspaceId: string;
  isEditMode: boolean;
  activeFilters: any[];
  onEditWidget: (widget: DashboardWidget) => void;
  onDeleteWidget: (widgetId: string) => void;
  onResizeWidget: (widgetId: string, deltaW: number, deltaH: number) => void;
  onMoveWidget?: (widgetId: string, direction: 'up' | 'down') => void;
  onDuplicateWidget?: (widget: DashboardWidget) => void;
  onUpdateWidgetSettings?: (widgetId: string, displaySettings: Record<string, any>) => void;
  onDragStart?: (e: React.DragEvent, widgetId: string) => void;
  onDragOver?: (e: React.DragEvent, widgetId: string) => void;
  onDrop?: (e: React.DragEvent, targetWidgetId: string) => void;
  onCrossFilter?: (filter: { column: string; operator: string; value: any }) => void;
  activeCrossFilters?: Array<{ column: string; value: any }>;
  cardBg?: string;
  borderColor?: string;
}

export const DashboardWidgetCard: React.FC<DashboardWidgetCardProps> = ({
  widget,
  workspaceId,
  isEditMode,
  activeFilters,
  onEditWidget,
  onDeleteWidget,
  onResizeWidget,
  onMoveWidget,
  onDuplicateWidget,
  onUpdateWidgetSettings,
  onDragStart,
  onDragOver,
  onDrop,
  onCrossFilter,
  activeCrossFilters,
  cardBg,
  borderColor,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [queryData, setQueryData] = useState<any>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  // 3-Dots Menu Dropdown state
  const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
  const [isPalettePickerOpen, setIsPalettePickerOpen] = useState<boolean>(false);
  const [isConfirmDeleteOpen, setIsConfirmDeleteOpen] = useState<boolean>(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Drill-down hierarchy state
  const [drillDepth, setDrillDepth] = useState<number>(0);
  const [drillFilters, setDrillFilters] = useState<any[]>([]);
  const [drillHistory, setDrillHistory] = useState<string[]>([]);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
        setIsPalettePickerOpen(false);
      }
    };
    if (isMenuOpen || isPalettePickerOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMenuOpen, isPalettePickerOpen]);

  const fetchWidgetData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res: WidgetQueryResponse = await dashboardService.queryWidget(
        workspaceId,
        widget.dashboard_id,
        widget.id,
        activeFilters,
        {
          drillLevel: drillDepth,
          drillFilters,
          compareTo: widget.query_config?.compare_to,
          targetValue: widget.query_config?.target_value,
        }
      );
      setQueryData(res.data);
      setLatencyMs(res.execution_time_ms);
    } catch (err: any) {
      // If no data or not yet configured, set clean fallback query data rather than blocking UI
      setError(err?.message || 'Widget configuration incomplete.');
    } finally {
      setLoading(false);
    }
  }, [
    workspaceId,
    widget.dashboard_id,
    widget.id,
    activeFilters,
    drillDepth,
    drillFilters,
    widget.query_config?.compare_to,
    widget.query_config?.target_value,
  ]);

  useEffect(() => {
    fetchWidgetData();
  }, [fetchWidgetData]);

  const handleDrillDown = (column: string, value: any) => {
    const levels = widget.query_config?.hierarchy_levels || [];
    if (levels.length > 0 && drillDepth < levels.length - 1) {
      setDrillDepth((d) => d + 1);
      setDrillFilters((f) => [...f, { column, operator: 'eq', value }]);
      setDrillHistory((h) => [...h, String(value)]);
    } else if (onCrossFilter) {
      onCrossFilter({ column, operator: 'eq', value });
    }
  };

  const handleDrillUp = () => {
    if (drillDepth > 0) {
      setDrillDepth((d) => d - 1);
      setDrillFilters((f) => f.slice(0, -1));
      setDrillHistory((h) => h.slice(0, -1));
    }
  };

  const handleResetDrill = () => {
    setDrillDepth(0);
    setDrillFilters([]);
    setDrillHistory([]);
  };

  // Quick Palette Switcher
  const handleSelectPalette = (palId: string) => {
    if (onUpdateWidgetSettings) {
      onUpdateWidgetSettings(widget.id, {
        ...(widget.display_settings || {}),
        color_palette: palId,
        custom_color: undefined,
      });
    }
    setIsPalettePickerOpen(false);
    setIsMenuOpen(false);
  };

  // Width in 12-column grid
  const colSpan = Math.min(Math.max(widget.grid_w, 3), 12);
  const colSpanClass = `col-span-12 lg:col-span-${colSpan}`;

  // For KPI widgets, render clean borderless or pastel-washed presentation
  const isKpi = widget.widget_type.toLowerCase() === 'kpi';

  return (
    <div
      draggable={isEditMode}
      onDragStart={(e) => onDragStart && onDragStart(e, widget.id)}
      onDragOver={(e) => onDragOver && onDragOver(e, widget.id)}
      onDrop={(e) => onDrop && onDrop(e, widget.id)}
      className={`rounded-2xl transition-all duration-200 flex flex-col justify-between overflow-hidden relative shadow-2xs group ${
        isEditMode
          ? 'hover:shadow-md border border-[#DCE5EB] hover:border-[#009F98]'
          : 'border border-[#DCE5EB]/80 hover:shadow-sm'
      } ${colSpanClass}`}
      style={{
        backgroundColor: cardBg || '#FFFFFF',
        borderColor: borderColor || undefined,
        minHeight: `${Math.max(widget.grid_h * 52, isKpi ? 140 : 200)}px`,
      }}
    >
      {/* Widget Header (Cleaner and Non-Technical) */}
      {!isKpi && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#DCE5EB]/60 bg-white">
          <div className="flex items-center gap-2 min-w-0">
            {isEditMode && (
              <div
                className="cursor-grab active:cursor-grabbing text-[#52616C] hover:text-[#102C46] transition-colors p-0.5 rounded"
                title="Drag to rearrange widget"
              >
                <GripVertical className="w-4 h-4" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-[#102C46] truncate leading-tight">
                  {widget.title}
                </h3>

                {/* Drill-Down Breadcrumbs */}
                {drillHistory.length > 0 && (
                  <div className="flex items-center gap-1 text-[10px] text-[#009F98] bg-[#EDF7FA] px-2 py-0.5 rounded-full font-bold">
                    <button onClick={handleResetDrill} className="hover:underline">
                      All
                    </button>
                    {drillHistory.map((h, i) => (
                      <span key={i} className="flex items-center gap-1">
                        <ChevronRight className="w-3 h-3 text-slate-400" />
                        <span>{h}</span>
                      </span>
                    ))}
                    <button
                      onClick={handleDrillUp}
                      className="ml-1 text-[#52616C] hover:text-[#102C46] hover:underline"
                    >
                      (Back)
                    </button>
                  </div>
                )}
              </div>

              {widget.description && (
                <p className="text-[11px] text-[#52616C] truncate mt-0.5">
                  {widget.description}
                </p>
              )}
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-1 shrink-0 ml-2">
            {latencyMs !== null && !loading && (
              <span
                className="hidden sm:inline-flex items-center gap-1 text-[10px] text-[#52616C] bg-[#F5F8FA] px-2 py-0.5 rounded border border-[#DCE5EB]/60 font-mono"
                title={`Execution Latency: ${latencyMs}ms`}
              >
                <Clock className="w-3 h-3 text-[#009F98]" />
                {latencyMs}ms
              </span>
            )}

            {/* Refresh */}
            <button
              type="button"
              onClick={fetchWidgetData}
              disabled={loading}
              className="p-1.5 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] transition-colors cursor-pointer disabled:opacity-40"
              title="Refresh Data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#009F98]' : ''}`} />
            </button>

            {/* 3-Dot Card Menu (Only in Edit Mode) */}
            {isEditMode && (
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="p-1.5 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] transition-colors cursor-pointer"
                  title="Widget Options"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>

                {isMenuOpen && (
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-xl shadow-lg border border-[#DCE5EB] py-1.5 z-40 animate-in fade-in duration-100">
                    {/* Edit */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsMenuOpen(false);
                        onEditWidget(widget);
                      }}
                      className="w-full text-left px-3 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5 text-[#009F98]" />
                      Edit Widget
                    </button>

                    {/* Change Color */}
                    <button
                      type="button"
                      onClick={() => setIsPalettePickerOpen(!isPalettePickerOpen)}
                      className="w-full text-left px-3 py-2 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <Palette className="w-3.5 h-3.5 text-[#8B5CF6]" />
                        <span>Color Theme</span>
                      </div>
                      <ChevronRight className="w-3 h-3 text-slate-400" />
                    </button>

                    {/* Palette Submenu */}
                    {isPalettePickerOpen && (
                      <div className="p-2 border-y border-[#DCE5EB] bg-[#F5F8FA] grid grid-cols-4 gap-1">
                        {Object.values(COLOR_PALETTES).map((p) => (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => handleSelectPalette(p.id)}
                            className="w-6 h-6 rounded-full border border-black/10 shadow-2xs hover:scale-110 transition-transform cursor-pointer mx-auto"
                            style={{ backgroundColor: p.primary }}
                            title={p.name}
                          />
                        ))}
                      </div>
                    )}

                    {/* Move Up / Down */}
                    {onMoveWidget && (
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            setIsMenuOpen(false);
                            onMoveWidget(widget.id, 'up');
                          }}
                          className="w-full text-left px-3 py-2 text-xs font-medium text-[#52616C] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                          Move Up
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setIsMenuOpen(false);
                            onMoveWidget(widget.id, 'down');
                          }}
                          className="w-full text-left px-3 py-2 text-xs font-medium text-[#52616C] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                          Move Down
                        </button>
                      </>
                    )}

                    {/* Resize toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsMenuOpen(false);
                        const nextW = widget.grid_w >= 12 ? 3 : widget.grid_w === 3 ? 6 : 12;
                        onResizeWidget(widget.id, nextW - widget.grid_w, 0);
                      }}
                      className="w-full text-left px-3 py-2 text-xs font-medium text-[#52616C] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
                    >
                      <Maximize2 className="w-3.5 h-3.5 text-[#2563EB]" />
                      Cycle Width ({widget.grid_w} cols)
                    </button>

                    <div className="border-t border-[#DCE5EB] my-1" />

                    {/* Delete */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsMenuOpen(false);
                        setIsConfirmDeleteOpen(true);
                      }}
                      className="w-full text-left px-3 py-2 text-xs font-bold text-rose-600 hover:bg-rose-50 flex items-center gap-2 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Remove Widget
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating 3-Dot Menu for KPI Cards in Edit Mode */}
      {isKpi && isEditMode && (
        <div className="absolute top-2 right-2 z-20" ref={menuRef}>
          <button
            type="button"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-7 h-7 rounded-lg bg-white/80 hover:bg-white text-[#52616C] hover:text-[#102C46] shadow-xs flex items-center justify-center transition-all cursor-pointer"
            title="Widget Options"
          >
            <MoreVertical className="w-3.5 h-3.5" />
          </button>

          {isMenuOpen && (
            <div className="absolute right-0 mt-1 w-44 bg-white rounded-xl shadow-lg border border-[#DCE5EB] py-1 z-40 animate-in fade-in duration-100">
              <button
                type="button"
                onClick={() => {
                  setIsMenuOpen(false);
                  onEditWidget(widget);
                }}
                className="w-full text-left px-3 py-1.5 text-xs font-semibold text-[#102C46] hover:bg-[#F5F8FA] flex items-center gap-2 cursor-pointer"
              >
                <Edit3 className="w-3.5 h-3.5 text-[#009F98]" />
                Edit KPI
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsMenuOpen(false);
                  setIsConfirmDeleteOpen(true);
                }}
                className="w-full text-left px-3 py-1.5 text-xs font-bold text-rose-600 hover:bg-rose-50 flex items-center gap-2 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Remove
              </button>
            </div>
          )}
        </div>
      )}

      {/* Widget Body */}
      <div className={`flex-1 flex flex-col justify-center min-h-[140px] ${isKpi ? 'p-0' : 'p-4'}`}>
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8">
            <div className="w-6 h-6 border-2 border-[#009F98] border-t-transparent rounded-full animate-spin" />
            <span className="text-[11px] text-[#52616C] font-medium">Computing analytics...</span>
          </div>
        ) : error ? (
          // Friendly Empty State when configuration is incomplete
          <div className="p-6 text-center flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EDF7FA] text-[#009F98] flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-[#102C46]">Configure your widget</h4>
              <p className="text-[11px] text-[#52616C] max-w-[240px] mx-auto mt-0.5">
                {error.includes('incomplete') || error.includes('no column')
                  ? 'This widget needs a metric and category selected to display data.'
                  : error}
              </p>
            </div>
            {isEditMode && (
              <button
                type="button"
                onClick={() => onEditWidget(widget)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#009F98] text-white text-xs font-bold rounded-xl shadow-xs hover:bg-[#007D78] transition-colors cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5" />
                Configure Widget
              </button>
            )}
          </div>
        ) : (
          <WidgetVisualization
            widgetType={widget.widget_type}
            data={queryData}
            displaySettings={widget.display_settings}
            height={Math.max(widget.grid_h * 42, 160)}
            onCrossFilter={onCrossFilter}
            activeCrossFilters={activeCrossFilters}
            onDrillDown={handleDrillDown}
            currentDrillDepth={drillDepth}
            hierarchyLevels={widget.query_config?.hierarchy_levels}
            onDrillUp={handleDrillUp}
          />
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      {isConfirmDeleteOpen && (
        <div className="absolute inset-0 bg-white/95 backdrop-blur-xs rounded-2xl z-30 p-4 flex flex-col items-center justify-center text-center animate-in fade-in duration-150">
          <div className="w-9 h-9 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mb-2">
            <Trash2 className="w-5 h-5" />
          </div>
          <h4 className="text-xs font-bold text-[#102C46]">Remove this widget?</h4>
          <p className="text-[11px] text-[#52616C] mt-0.5 mb-3 max-w-[200px]">
            "{widget.title}" will be permanently removed from this dashboard.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsConfirmDeleteOpen(false)}
              className="px-3 py-1 bg-slate-100 text-[#102C46] text-xs font-semibold rounded-lg hover:bg-slate-200 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                setIsConfirmDeleteOpen(false);
                onDeleteWidget(widget.id);
              }}
              className="px-3 py-1 bg-rose-600 text-white text-xs font-bold rounded-lg hover:bg-rose-700 shadow-xs cursor-pointer"
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
