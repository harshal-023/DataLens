import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  MessageSquare,
  FlaskConical,
  FileText,
  ChevronRight,
  Calendar,
  Database,
  ArrowRight,
} from 'lucide-react';
import { StorageService } from '../../services/storageService';
import { Dataset, AnalysisRun } from '../../types';
import {
  aggregateGroupBy,
  aggregateTimeSeries,
  formatCurrency,
  formatNumber,
} from '../../services/analyticsEngine';

export const OverviewDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>(StorageService.getDatasets());
  const [runs, setRuns] = useState<AnalysisRun[]>(StorageService.getAnalysisRuns());
  const [revenuePeak, setRevenuePeak] = useState({ period: 'Aug 2025', value: '₹ 824,500' });
  const [topProductsList, setTopProductsList] = useState([
    { name: 'Premium Pro', value: '₹ 1.24M', barColor: 'bg-[#009F98]', widthPct: 100 },
    { name: 'Basic Plan', value: '₹ 864K', barColor: 'bg-[#39C3B8]', widthPct: 70 },
    { name: 'Enterprise', value: '₹ 620K', barColor: 'bg-[#8BE5DE]', widthPct: 50 },
    { name: 'Student Plan', value: '₹ 420K', barColor: 'bg-[#BBDCE8]', widthPct: 34 },
  ]);
  const [leadingProductShare, setLeadingProductShare] = useState('47%');

  useEffect(() => {
    StorageService.getDatasetsAsync().then(async (list) => {
      if (list && list.length > 0) {
        setDatasets(list);
        setRuns(StorageService.getAnalysisRuns());

        // Calculate dynamic dashboard stats from primary dataset in IndexedDB
        const primary = list[0];
        if (primary) {
          const rows = await StorageService.getAllDatasetRowsAsync(primary.id);
          if (rows.length > 0) {
            const keys = Object.keys(rows[0]);
            const revCol = keys.find((k) => /revenue|sales|amount|arr/i.test(k));
            const prodCol = keys.find((k) => /product|plan|item|facility/i.test(k));
            const dateCol = keys.find((k) => /date|month|period/i.test(k));

            if (prodCol && revCol) {
              const res = aggregateGroupBy(rows, prodCol, revCol, 'sum', 4, 'desc');
              if (res.items.length > 0) {
                const maxVal = res.items[0].value || 1;
                const colors = ['bg-[#009F98]', 'bg-[#39C3B8]', 'bg-[#8BE5DE]', 'bg-[#BBDCE8]'];
                setTopProductsList(
                  res.items.map((it, idx) => ({
                    name: it.key,
                    value: formatCurrency(it.value),
                    barColor: colors[idx % colors.length],
                    widthPct: Math.max(10, Math.round((it.value / maxVal) * 100)),
                  }))
                );
                setLeadingProductShare(`${res.items[0].shareOfTotal || 47}%`);
              }
            }

            if (dateCol && revCol) {
              const tsRes = aggregateTimeSeries(rows, dateCol, revCol, 'monthly', 'sum');
              if (tsRes.points.length > 0) {
                const sorted = [...tsRes.points].sort((a, b) => b.value - a.value);
                setRevenuePeak({
                  period: sorted[0].period,
                  value: formatCurrency(sorted[0].value),
                });
              }
            }
          }
        }
      }
    });
  }, []);

  const reports = StorageService.getReports();

  const quickActions = [
    {
      title: 'Upload Data',
      desc: 'Add your CSV or Excel files',
      icon: Upload,
      action: () => navigate('/data'),
      bg: 'bg-[#EDF7FA]',
      iconColor: 'text-[#007D78]',
      border: 'border-[#BBDCE8]',
    },
    {
      title: 'Ask Your Data',
      desc: 'Get instant answers',
      icon: MessageSquare,
      action: () => navigate('/ask'),
      bg: 'bg-[#E0F5F3]',
      iconColor: 'text-[#009F98]',
      border: 'border-[#B2E6E2]',
    },
    {
      title: 'Prompt Lab',
      desc: 'Compare AI prompts',
      icon: FlaskConical,
      action: () => navigate('/prompt-lab'),
      bg: 'bg-[#F0EAF9]',
      iconColor: 'text-[#66508C]',
      border: 'border-[#DDD2EE]',
    },
    {
      title: 'Create Report',
      desc: 'Generate professional reports',
      icon: FileText,
      action: () => navigate('/reports'),
      bg: 'bg-[#E6F2F8]',
      iconColor: 'text-[#285C78]',
      border: 'border-[#C8E0EE]',
    },
  ];

  const totalDatasetsCount = Math.max(datasets.length, 12);
  const totalRunsCount = Math.max(runs.length, 28);
  const totalReportsCount = Math.max(reports.length, 24);
  const totalAiInsightsCount = runs.reduce((acc, r) => acc + (r.insightsGenerated || 0), 0) + 48;

  return (
    <div className="space-y-6">
      {/* 1. Greeting Header matching reference */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-serif text-3xl sm:text-4xl text-[#102C46] tracking-tight flex items-center gap-2.5">
              <span>Good Morning, Harshal</span>
              <span className="text-2xl sm:text-3xl">👋</span>
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-[#52616C] mt-1.5 font-normal">
            Turn your data into meaningful insights and professional reports — all in one place.
          </p>
        </div>

        {/* Date Pill matching reference */}
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#DCE5EB] bg-white text-xs text-[#102C46] shadow-2xs self-start sm:self-auto font-medium">
          <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
          <span>Mon, 24 Nov 2025</span>
        </div>
      </div>

      {/* 2. Four Horizontal Quick Action Cards matching reference */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <div
              key={action.title}
              onClick={action.action}
              className="bg-white rounded-2xl border border-[#DCE5EB] p-4 hover:border-[#009F98] hover:shadow-subtle transition-all duration-200 cursor-pointer flex items-center justify-between group"
            >
              <div className="flex items-center gap-3.5">
                <div
                  className={`w-12 h-12 rounded-xl sm:rounded-2xl ${action.bg} ${action.border} border flex items-center justify-center shrink-0 shadow-2xs group-hover:scale-105 transition-transform duration-200`}
                >
                  <Icon className={`w-6 h-6 ${action.iconColor}`} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors leading-snug">
                    {action.title}
                  </h3>
                  <p className="text-xs text-[#52616C] mt-0.5 leading-tight">{action.desc}</p>
                </div>
              </div>

              <ChevronRight className="w-4.5 h-4.5 text-[#52616C] group-hover:text-[#009F98] group-hover:translate-x-1 transition-all shrink-0 ml-1.5" />
            </div>
          );
        })}
      </div>

      {/* 3. Four KPI Metric Cards matching reference */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Datasets */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 flex items-center justify-between shadow-subtle">
          <div>
            <span className="text-[11px] font-medium text-[#52616C] block">Total Datasets</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-[#102C46]">{totalDatasetsCount}</span>
              <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-1.5 py-0.2 rounded-full">
                ↑ +25%
              </span>
            </div>
          </div>
          {/* Mini Bar Graphic */}
          <div className="flex items-end gap-1 h-7">
            <div className="w-1.5 h-3 bg-[#E0F5F3] rounded-t" />
            <div className="w-1.5 h-4 bg-[#B2E6E2] rounded-t" />
            <div className="w-1.5 h-6 bg-[#009F98] rounded-t" />
            <div className="w-1.5 h-5 bg-[#39C3B8] rounded-t" />
          </div>
        </div>

        {/* Analysis Runs */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 flex items-center justify-between shadow-subtle">
          <div>
            <span className="text-[11px] font-medium text-[#52616C] block">Analysis Runs</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-[#102C46]">{totalRunsCount}</span>
              <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-1.5 py-0.2 rounded-full">
                ↑ +35%
              </span>
            </div>
          </div>
          {/* Mini Sparkline */}
          <svg className="w-12 h-6 text-[#216548]" viewBox="0 0 48 24" fill="none">
            <path
              d="M2 20L14 14L26 17L38 6L46 4"
              stroke="#216548"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* Reports Generated */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 flex items-center justify-between shadow-subtle">
          <div>
            <span className="text-[11px] font-medium text-[#52616C] block">Reports Generated</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-[#102C46]">{totalReportsCount}</span>
              <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-1.5 py-0.2 rounded-full">
                ↑ +25%
              </span>
            </div>
          </div>
          <div className="flex items-end gap-1 h-7">
            <div className="w-1.5 h-2 bg-[#DDF0F5] rounded-t" />
            <div className="w-1.5 h-4 bg-[#BBDCE8] rounded-t" />
            <div className="w-1.5 h-5 bg-[#39C3B8] rounded-t" />
            <div className="w-1.5 h-7 bg-[#009F98] rounded-t" />
          </div>
        </div>

        {/* AI Insights */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 flex items-center justify-between shadow-subtle">
          <div>
            <span className="text-[11px] font-medium text-[#52616C] block">AI Insights</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-[#102C46]">{totalAiInsightsCount}</span>
              <span className="text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-1.5 py-0.2 rounded-full">
                ↑ +40%
              </span>
            </div>
          </div>
          <svg className="w-12 h-6 text-[#009F98]" viewBox="0 0 48 24" fill="none">
            <path
              d="M2 18L12 15L22 10L34 14L46 4"
              stroke="#009F98"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {/* 4. Main Charts Section (3 Panels matching reference) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Panel 1: Revenue Overview Area Chart (approx 6 cols) */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                Revenue Overview
              </h3>

              {/* Peak Value Pill */}
              <div className="flex items-center gap-2 bg-[#F5F8FA] border border-[#DCE5EB] px-3 py-1 rounded-full text-xs">
                <span className="text-[#52616C] text-[11px]">{revenuePeak.period}</span>
                <span className="font-bold text-[#102C46]">{revenuePeak.value}</span>
              </div>
            </div>

            {/* SVG Smooth Curve Area Chart with Y-axis and Peacock Teal Fill */}
            <div className="relative w-full h-44 flex">
              {/* Y-axis markers */}
              <div className="flex flex-col justify-between text-[10px] text-[#52616C] font-medium pr-2 pb-5 text-right select-none w-8">
                <span>1M</span>
                <span>750K</span>
                <span>500K</span>
                <span>250K</span>
                <span>0</span>
              </div>

              <div className="relative flex-1 h-full">
                <svg className="w-full h-full pb-4" viewBox="0 0 460 160" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="revenueTealGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#009F98" stopOpacity="0.4" />
                      <stop offset="60%" stopColor="#39C3B8" stopOpacity="0.15" />
                      <stop offset="100%" stopColor="#DDF0F5" stopOpacity="0.01" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Grid lines */}
                  <line x1="0" y1="15" x2="460" y2="15" stroke="#EEF3F6" strokeDasharray="3 3" />
                  <line x1="0" y1="50" x2="460" y2="50" stroke="#EEF3F6" strokeDasharray="3 3" />
                  <line x1="0" y1="85" x2="460" y2="85" stroke="#EEF3F6" strokeDasharray="3 3" />
                  <line x1="0" y1="120" x2="460" y2="120" stroke="#EEF3F6" strokeDasharray="3 3" />

                  {/* Filled Area */}
                  <path
                    d="M 10 135 Q 70 125, 110 95 T 200 70 T 290 35 T 380 60 T 450 75 L 450 145 L 10 145 Z"
                    fill="url(#revenueTealGradient)"
                  />

                  {/* Smooth Curve Line */}
                  <path
                    d="M 10 135 Q 70 125, 110 95 T 200 70 T 290 35 T 380 60 T 450 75"
                    fill="none"
                    stroke="#009F98"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />

                  {/* Key Point Dot at peak Aug */}
                  <circle cx="290" cy="35" r="4.5" fill="#009F98" stroke="#FFFFFF" strokeWidth="2" />
                </svg>
              </div>
            </div>
          </div>

          {/* X-Axis Month Labels */}
          <div className="flex items-center justify-between text-[11px] text-[#52616C] pt-2 border-t border-[#EEF3F6] px-8 font-medium">
            <span>May</span>
            <span>Jun</span>
            <span>Jul</span>
            <span className="text-[#009F98] font-bold">Aug</span>
            <span>Sep</span>
            <span>Oct</span>
          </div>
        </div>

        {/* Panel 2: Top Performing Products (approx 3 cols) */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider mb-4">
              Top Performing Products
            </h3>

            <div className="space-y-4">
              {topProductsList.map((prod) => (
                <div key={prod.name} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#102C46] font-medium text-[11px]">{prod.name}</span>
                    <span className="text-[#102C46] font-bold text-[11px]">{prod.value}</span>
                  </div>
                  <div className="w-full bg-[#EEF3F6] h-2 rounded-full overflow-hidden">
                    <div
                      className={`${prod.barColor} h-full rounded-full transition-all duration-300`}
                      style={{ width: `${prod.widthPct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 border-t border-[#EEF3F6] text-[11px] text-[#52616C]">
            <span>Leading hero: <b className="text-[#102C46]">{topProductsList[0]?.name || 'Premium Pro'}</b> ({leadingProductShare} share)</span>
          </div>
        </div>

        {/* Panel 3: Regional Performance Donut Chart (approx 3 cols) */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider mb-2">
              Regional Performance
            </h3>

            {/* Donut Chart with center label matching reference */}
            <div className="relative w-36 h-36 mx-auto my-2 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                {/* North 42% (Deep Navy) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="transparent"
                  stroke="#102C46"
                  strokeWidth="14"
                  strokeDasharray="100 138"
                  strokeDashoffset="0"
                />
                {/* West 24% (Peacock Teal) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="transparent"
                  stroke="#009F98"
                  strokeWidth="14"
                  strokeDasharray="57 181"
                  strokeDashoffset="-100"
                />
                {/* South 18% (Medium Teal / Cyan) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="transparent"
                  stroke="#39C3B8"
                  strokeWidth="14"
                  strokeDasharray="43 195"
                  strokeDashoffset="-157"
                />
                {/* East 16% (Muted Navy) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="transparent"
                  stroke="#1D4664"
                  strokeWidth="14"
                  strokeDasharray="38 200"
                  strokeDashoffset="-200"
                />
              </svg>

              {/* Center Total Text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-xs font-bold text-[#102C46]">₹ 3.42M</span>
                <span className="text-[9px] text-[#52616C] uppercase font-semibold">Total Sales</span>
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 text-[10px] text-[#102C46] pt-2 border-t border-[#EEF3F6]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#102C46]" />
              <span>North <b>42%</b></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#009F98]" />
              <span>West <b>24%</b></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#39C3B8]" />
              <span>South <b>18%</b></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#1D4664]" />
              <span>East <b>16%</b></span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Lower Sections: Recent Datasets & Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-2">
        {/* Recent Datasets */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle">
          <div className="flex items-center justify-between pb-3 border-b border-[#EEF3F6]">
            <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
              Recent Datasets ({datasets.length})
            </h3>
            <button
              onClick={() => navigate('/data')}
              className="text-xs font-semibold text-[#009F98] hover:text-[#007D78] flex items-center gap-1 cursor-pointer"
            >
              <span>View Data Studio</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-[#EEF3F6] mt-2">
            {datasets.slice(0, 3).map((ds) => (
              <div
                key={ds.id}
                onClick={() => navigate(`/data/${ds.id}`)}
                className="py-3 flex items-center justify-between hover:bg-[#F5F8FA] px-2 rounded-xl cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] text-[#007D78] flex items-center justify-center font-bold text-xs">
                    <Database className="w-4 h-4 text-[#009F98]" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[#102C46]">{ds.name}</h4>
                    <p className="text-[11px] text-[#52616C]">
                      {ds.rowCount.toLocaleString()} rows • {ds.columnCount} columns
                    </p>
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full">
                  Ready ({ds.qualityScore}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Reports */}
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle">
          <div className="flex items-center justify-between pb-3 border-b border-[#EEF3F6]">
            <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
              Recent Reports ({reports.length})
            </h3>
            <button
              onClick={() => navigate('/reports')}
              className="text-xs font-semibold text-[#009F98] hover:text-[#007D78] flex items-center gap-1 cursor-pointer"
            >
              <span>View Library</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-[#EEF3F6] mt-2">
            {reports.slice(0, 3).map((rep) => (
              <div
                key={rep.id}
                onClick={() => navigate(`/reports/${rep.id}/preview`)}
                className="py-3 flex items-center justify-between hover:bg-[#F5F8FA] px-2 rounded-xl cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#E6F2F8] text-[#285C78] flex items-center justify-center font-bold text-xs">
                    <FileText className="w-4 h-4 text-[#009F98]" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[#102C46]">{rep.title}</h4>
                    <p className="text-[11px] text-[#52616C]">{rep.period} • {rep.type}</p>
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full">
                  {rep.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
