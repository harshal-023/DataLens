import React, { useState, useEffect, useCallback } from 'react';
import {
  GripVertical,
  Settings2,
  Trash2,
  RefreshCw,
  AlertCircle,
  Clock,
  ChevronRight,
} from 'lucide-react';
import { DashboardWidget, dashboardService, WidgetQueryResponse } from '../../services/dashboardService';
import { WidgetVisualization } from './WidgetVisualizations';

export interface DashboardWidgetCardProps {
  widget: DashboardWidget;
  workspaceId: string;
  isEditMode: boolean;
  activeFilters: any[];
  onEditWidget: (widget: DashboardWidget) => void;
  onDeleteWidget: (widgetId: string) => void;
  onResizeWidget: (widgetId: string, deltaW: number, deltaH: number) => void;
  onMoveWidget?: (widgetId: string, direction: 'up' | 'down') => void;
  onDragStart?: (e: React.DragEvent, widgetId: string) => void;
  onDragOver?: (e: React.DragEvent, widgetId: string) => void;
  onDrop?: (e: React.DragEvent, targetWidgetId: string) => void;
  onCrossFilter?: (filter: { column: string; operator: string; value: any }) => void;
  activeCrossFilters?: Array<{ column: string; value: any }>;
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
  onDragStart,
  onDragOver,
  onDrop,
  onCrossFilter,
  activeCrossFilters,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [queryData, setQueryData] = useState<any>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  // Drill-down hierarchy state
  const [drillDepth, setDrillDepth] = useState<number>(0);
  const [drillFilters, setDrillFilters] = useState<any[]>([]);
  const [drillHistory, setDrillHistory] = useState<string[]>([]);

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
      setError(err?.message || 'Failed to load calculation results.');
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

  // Width in 12-column grid: on mobile full width, on desktop `lg:col-span-${grid_w}`
  const colSpanClass = `col-span-12 lg:col-span-${Math.min(Math.max(widget.grid_w, 3), 12)}`;

  return (
    <div
      draggable={isEditMode}
      onDragStart={(e) => onDragStart && onDragStart(e, widget.id)}
      onDragOver={(e) => onDragOver && onDragOver(e, widget.id)}
      onDrop={(e) => onDrop && onDrop(e, widget.id)}
      className={`bg-white rounded-2xl border transition-all duration-200 flex flex-col justify-between overflow-hidden relative shadow-2xs group ${
        isEditMode
          ? 'border-[#DCE5EB] hover:border-[#009F98] hover:shadow-md'
          : 'border-[#DCE5EB]/80 hover:shadow-sm'
      } ${colSpanClass}`}
      style={{
        minHeight: `${Math.max(widget.grid_h * 50, 180)}px`,
      }}
    >
      {/* Widget Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#DCE5EB]/60 bg-gradient-to-r from-white to-[#F5F8FA]/50">
        <div className="flex items-center gap-2 min-w-0">
          {isEditMode && (
            <div
              className="cursor-grab active:cursor-grabbing text-[#52616C] hover:text-[#102C46] transition-colors p-0.5 rounded"
              title="Drag to rearrange"
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
                    title="Back to parent level"
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
        <div className="flex items-center gap-1.5 shrink-0 ml-2">
          {latencyMs !== null && !loading && (
            <span
              className="hidden sm:inline-flex items-center gap-1 text-[10px] text-[#52616C] bg-[#F5F8FA] px-2 py-0.5 rounded border border-[#DCE5EB]/60"
              title={`DuckDB Execution Latency: ${latencyMs}ms`}
            >
              <Clock className="w-3 h-3 text-[#009F98]" />
              {latencyMs}ms
            </span>
          )}

          {isEditMode && (
            <>
              {/* Width Sizing Controls */}
              <div className="hidden sm:flex items-center bg-[#F5F8FA] rounded-lg border border-[#DCE5EB]/60 p-0.5">
                <button
                  type="button"
                  onClick={() => onResizeWidget(widget.id, -2, 0)}
                  disabled={widget.grid_w <= 3}
                  className="px-1.5 py-0.5 text-[10px] font-bold text-[#52616C] hover:text-[#102C46] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  title="Shrink Width (-2 cols)"
                >
                  W-
                </button>
                <span className="text-[10px] font-semibold text-[#102C46] px-1 border-x border-[#DCE5EB]">
                  {widget.grid_w}
                </span>
                <button
                  type="button"
                  onClick={() => onResizeWidget(widget.id, 2, 0)}
                  disabled={widget.grid_w >= 12}
                  className="px-1.5 py-0.5 text-[10px] font-bold text-[#52616C] hover:text-[#102C46] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  title="Expand Width (+2 cols)"
                >
                  W+
                </button>
              </div>

              {/* Height Sizing Controls */}
              <div className="hidden sm:flex items-center bg-[#F5F8FA] rounded-lg border border-[#DCE5EB]/60 p-0.5">
                <button
                  type="button"
                  onClick={() => onResizeWidget(widget.id, 0, -1)}
                  disabled={widget.grid_h <= 3}
                  className="px-1.5 py-0.5 text-[10px] font-bold text-[#52616C] hover:text-[#102C46] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  title="Shrink Height (-1 row)"
                >
                  H-
                </button>
                <span className="text-[10px] font-semibold text-[#102C46] px-1 border-x border-[#DCE5EB]">
                  {widget.grid_h}
                </span>
                <button
                  type="button"
                  onClick={() => onResizeWidget(widget.id, 0, 1)}
                  disabled={widget.grid_h >= 12}
                  className="px-1.5 py-0.5 text-[10px] font-bold text-[#52616C] hover:text-[#102C46] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  title="Expand Height (+1 row)"
                >
                  H+
                </button>
              </div>

              {/* Edit Settings */}
              <button
                type="button"
                onClick={() => onEditWidget(widget)}
                className="p-1.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#EEF3F6] transition-colors cursor-pointer"
                title="Configure Widget"
              >
                <Settings2 className="w-3.5 h-3.5" />
              </button>

              {/* Delete Widget */}
              <button
                type="button"
                onClick={() => onDeleteWidget(widget.id)}
                className="p-1.5 rounded-lg text-[#52616C] hover:text-[#A63838] hover:bg-[#FCE9E9] transition-colors cursor-pointer"
                title="Delete Widget"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {/* Refresh Action */}
          <button
            type="button"
            onClick={fetchWidgetData}
            disabled={loading}
            className="p-1.5 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] transition-colors cursor-pointer disabled:opacity-40"
            title="Refresh Data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#009F98]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Widget Body */}
      <div className="flex-1 p-4 flex flex-col justify-center min-h-[140px]">
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8">
            <div className="w-6 h-6 border-2 border-[#009F98] border-t-transparent rounded-full animate-spin" />
            <span className="text-[11px] text-[#52616C] font-medium">Computing analytics...</span>
          </div>
        ) : error ? (
          <div className="flex items-start gap-2 p-3 bg-[#FCE9E9]/60 rounded-xl border border-[#F7C9C5] text-xs text-[#A63838]">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold">Error evaluating query: </span>
              <span>{error}</span>
            </div>
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
    </div>
  );
};
