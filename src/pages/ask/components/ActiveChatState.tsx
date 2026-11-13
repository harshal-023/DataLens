import React, { useState } from 'react';
import {
  Sparkles,
  Lightbulb,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  BarChart2,
  LineChart,
  PieChart,
  Table as TableIcon,
  Download,
  FilePlus,
  Loader2,
  Code2,
  Bookmark,
  HelpCircle,
} from 'lucide-react';
import { AskMessage } from '../../../types';
import { BarChart, DonutChart } from '../../../components/charts/Charts';

interface ActiveChatStateProps {
  messages: AskMessage[];
  isProcessing: boolean;
  onSelectQuestion: (question: string) => void;
  onAddToReport?: (message: AskMessage) => void;
  onClarify?: (message: AskMessage, option: { key: string; label: string }) => void;
  onSaveAnalysis?: (message: AskMessage) => void;
}

export const ActiveChatState: React.FC<ActiveChatStateProps> = ({
  messages,
  isProcessing,
  onSelectQuestion,
  onAddToReport,
  onClarify,
  onSaveAnalysis,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [savedMessageId, setSavedMessageId] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const [activeChartViews, setActiveChartViews] = useState<Record<string, 'bar' | 'line' | 'pie' | 'table'>>({});

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleExportCSV = (msg: AskMessage) => {
    if (!msg.tableData) {
      alert('Exported analytical summary.');
      return;
    }
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [msg.tableData.headers.join(','), ...msg.tableData.rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `datalens_analytics_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-1 overflow-y-auto space-y-6 pr-1 pb-4">
      {messages.map((msg) => {
        if (msg.sender === 'user') {
          return (
            <div key={msg.id} className="flex justify-end items-end gap-2">
              <div className="bg-[#EDF7FA] text-[#102C46] px-4 py-2.5 rounded-2xl rounded-tr-xs text-xs font-semibold max-w-lg shadow-2xs border border-[#BBDCE8]">
                <p>{msg.content}</p>
                <span className="text-[10px] text-[#52616C] font-normal block text-right mt-1">
                  {msg.timestamp}
                </span>
              </div>
            </div>
          );
        }

        // Assistant Message
        const isEvidenceOpen = !!expandedEvidence[msg.id];
        const currentChartView = activeChartViews[msg.id] || msg.chartData?.type || 'bar';

        const isConversational =
          ['GREETING', 'CASUAL_CONVERSATION', 'CAPABILITY_QUERY', 'UNSUPPORTED_REQUEST', 'greeting', 'casual_conversation', 'capability_query', 'unsupported_request'].includes(msg.intent || '') ||
          ((!msg.metrics || msg.metrics.length === 0) && !msg.chartData && !msg.tableData && (!msg.evidence || msg.evidence.length === 0) && !msg.needsClarification);

        if (isConversational) {
          return (
            <div key={msg.id} className="space-y-2">
              {/* Assistant Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#009F98] text-white flex items-center justify-center shadow-2xs">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-bold text-[#102C46]">DataLens AI</span>
                  <span className="text-[10px] text-[#52616C]">{msg.timestamp}</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs">
                  <button
                    onClick={() => handleCopy(msg.id, msg.directAnswer || msg.content)}
                    className="p-1 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] transition-colors cursor-pointer"
                    title="Copy response"
                  >
                    {copiedId === msg.id ? (
                      <Check className="w-3.5 h-3.5 text-[#216548]" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Conversational Bubble */}
              <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle max-w-2xl text-xs sm:text-sm text-[#102C46] leading-relaxed space-y-3">
                <div className="whitespace-pre-line">
                  {msg.directAnswer || msg.content}
                </div>

                {/* Follow-up Suggestions Chips */}
                {msg.suggestedFollowUps && msg.suggestedFollowUps.length > 0 && (
                  <div className="pt-2 border-t border-[#EEF3F6]">
                    <span className="text-[10px] text-[#52616C] uppercase font-bold tracking-wider block mb-2">
                      Suggested Questions
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggestedFollowUps.map((sug, sIdx) => (
                        <button
                          key={sIdx}
                          onClick={() => onSelectQuestion(sug)}
                          className="px-3 py-1 rounded-full border border-[#DCE5EB] bg-[#F5F8FA] hover:border-[#009F98] hover:bg-[#E0F5F3] text-xs text-[#102C46] font-medium transition-colors cursor-pointer shadow-2xs text-left"
                        >
                          {sug}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        }

        return (
          <div key={msg.id} className="space-y-3">
            {/* Assistant Header matching reference */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-[#009F98] text-white flex items-center justify-center shadow-2xs">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-bold text-[#102C46]">DataLens AI</span>
                <span className="text-[10px] text-[#52616C]">{msg.timestamp}</span>
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  onClick={() => handleCopy(msg.id, msg.directAnswer || msg.content)}
                  className="p-1 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] transition-colors cursor-pointer"
                  title="Copy answer"
                >
                  {copiedId === msg.id ? (
                    <Check className="w-3.5 h-3.5 text-[#216548]" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
                {onSaveAnalysis && (
                  <button
                    onClick={() => {
                      onSaveAnalysis(msg);
                      setSavedMessageId(msg.id);
                      setTimeout(() => setSavedMessageId(null), 2500);
                    }}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#E0F5F3] text-[11px] font-medium transition-colors cursor-pointer"
                    title="Save this analysis finding"
                  >
                    {savedMessageId === msg.id ? (
                      <>
                        <Check className="w-3 h-3 text-[#216548]" />
                        <span className="text-[#216548]">Saved</span>
                      </>
                    ) : (
                      <>
                        <Bookmark className="w-3 h-3" />
                        <span>Save</span>
                      </>
                    )}
                  </button>
                )}
                {onAddToReport && (
                  <button
                    onClick={() => onAddToReport(msg)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#E0F5F3] text-[11px] font-medium transition-colors cursor-pointer"
                    title="Add to business report"
                  >
                    <FilePlus className="w-3 h-3" />
                    <span>Add to Report</span>
                  </button>
                )}
              </div>
            </div>

            {/* AI Structured Answer Card matching reference image */}
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-4">
              {/* 1. Direct Answer Sentence */}
              {msg.directAnswer && (
                <p className="text-xs sm:text-sm text-[#102C46] font-medium leading-relaxed">
                  {msg.directAnswer}
                </p>
              )}

              {/* Clarification Prompt & Interactive Option Pills */}
              {msg.needsClarification && msg.clarificationOptions && msg.clarificationOptions.length > 0 && (
                <div className="bg-[#FFF8EE] border border-[#F5D899] p-3.5 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-2 text-[#995A00]">
                    <HelpCircle className="w-4 h-4 text-[#C27803] shrink-0" />
                    <span className="text-xs font-bold text-[#995A00]">
                      {msg.clarificationPrompt || 'Please clarify your analytical goal:'}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {msg.clarificationOptions.map((opt) => (
                      <button
                        key={opt.key}
                        onClick={() => onClarify?.(msg, opt)}
                        className="px-3 py-1.5 rounded-lg border border-[#E0A838] bg-white hover:bg-[#FEF1D6] text-xs font-semibold text-[#663C00] shadow-2xs transition-colors cursor-pointer text-left"
                      >
                        <div>{opt.label}</div>
                        {opt.explanation && (
                          <div className="text-[10px] font-normal text-[#995A00]">
                            {opt.explanation}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. Key Metrics (KPI Cards) matching reference */}
              {msg.metrics && msg.metrics.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {msg.metrics.map((m, idx) => (
                    <div
                      key={idx}
                      className="bg-[#F5F8FA] p-3 rounded-xl border border-[#DCE5EB] flex flex-col justify-between"
                    >
                      <span className="text-[10px] text-[#52616C] font-medium uppercase tracking-wider block">
                        {m.label}
                      </span>
                      <span className="text-sm font-bold text-[#102C46] mt-1 block truncate">
                        {m.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* 3. Visualizations / Table Switcher */}
              {msg.chartData && (
                <div className="pt-2 border-t border-[#EEF3F6] space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-[#102C46]">{msg.chartData.title}</h4>

                    {/* Chart / Table View Switcher */}
                    <div className="flex items-center gap-1 bg-[#F5F8FA] p-1 rounded-xl border border-[#DCE5EB]">
                      <button
                        onClick={() =>
                          setActiveChartViews((prev) => ({ ...prev, [msg.id]: 'bar' }))
                        }
                        className={`p-1 rounded-lg text-xs cursor-pointer ${
                          currentChartView === 'bar' ? 'bg-white shadow-2xs text-[#009F98]' : 'text-[#52616C]'
                        }`}
                        title="Bar Chart"
                      >
                        <BarChart2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          setActiveChartViews((prev) => ({ ...prev, [msg.id]: 'line' }))
                        }
                        className={`p-1 rounded-lg text-xs cursor-pointer ${
                          currentChartView === 'line' ? 'bg-white shadow-2xs text-[#009F98]' : 'text-[#52616C]'
                        }`}
                        title="Line Chart"
                      >
                        <LineChart className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          setActiveChartViews((prev) => ({ ...prev, [msg.id]: 'pie' }))
                        }
                        className={`p-1 rounded-lg text-xs cursor-pointer ${
                          currentChartView === 'pie' ? 'bg-white shadow-2xs text-[#009F98]' : 'text-[#52616C]'
                        }`}
                        title="Donut Chart"
                      >
                        <PieChart className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          setActiveChartViews((prev) => ({ ...prev, [msg.id]: 'table' }))
                        }
                        className={`p-1 rounded-lg text-xs cursor-pointer ${
                          currentChartView === 'table' ? 'bg-white shadow-2xs text-[#009F98]' : 'text-[#52616C]'
                        }`}
                        title="Data Table"
                      >
                        <TableIcon className="w-3.5 h-3.5" />
                      </button>
                      {msg.tableData && (
                        <button
                          onClick={() => handleExportCSV(msg)}
                          className="p-1 rounded-lg text-xs text-[#52616C] hover:text-[#009F98] cursor-pointer"
                          title="Export CSV"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Chart Rendering */}
                  {currentChartView === 'bar' && (
                    <BarChart
                      labels={msg.chartData.labels}
                      values={msg.chartData.values}
                      unit={msg.chartData.unit}
                      height={180}
                      barColor="#009F98"
                    />
                  )}

                  {currentChartView === 'line' && (
                    <div className="h-44 flex flex-col justify-end pt-4 pb-2">
                      <div className="relative h-32 flex items-end justify-between px-4">
                        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-30">
                          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
                          <div className="border-b border-dashed border-[#DCE5EB] w-full" />
                          <div className="border-b border-[#DCE5EB] w-full" />
                        </div>
                        {msg.chartData.labels.map((lbl, idx) => {
                          const val = msg.chartData!.values[idx];
                          const max = Math.max(...msg.chartData!.values, 1);
                          const hPct = (val / max) * 80;
                          return (
                            <div key={lbl} className="flex-1 flex flex-col items-center justify-end h-full relative z-10">
                              <span className="text-[10px] font-bold text-[#102C46] mb-1">
                                {val} {msg.chartData!.unit}
                              </span>
                              <div
                                className="w-3 bg-gradient-to-t from-[#007D78] to-[#009F98] rounded-t-full shadow-2xs"
                                style={{ height: `${hPct}%` }}
                              />
                              <span className="text-[10px] text-[#52616C] mt-2 font-medium truncate">
                                {lbl}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {currentChartView === 'pie' && (
                    <DonutChart
                      labels={msg.chartData.labels}
                      values={msg.chartData.values}
                      size={150}
                    />
                  )}

                  {/* 4. Structured Data Table View */}
                  {currentChartView === 'table' && msg.tableData && (
                    <div className="overflow-x-auto rounded-xl border border-[#DCE5EB]">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-[#F5F8FA] text-[#52616C] uppercase text-[10px] font-bold border-b border-[#DCE5EB]">
                          <tr>
                            {msg.tableData.headers.map((h, i) => (
                              <th key={i} className="px-3 py-2">
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#EEF3F6] text-[#102C46]">
                          {msg.tableData.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-[#F5F8FA]">
                              {row.map((cell, cIdx) => (
                                <td
                                  key={cIdx}
                                  className={`px-3 py-2 ${
                                    cIdx === 0 ? 'font-semibold' : ''
                                  } ${cIdx === 1 ? 'text-[#009F98] font-bold' : ''}`}
                                >
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* 5. Insight / Interpretation Banner matching reference */}
              {msg.interpretation && (
                <div className="bg-[#E0F5F3] p-3 rounded-xl border border-[#B2E6E2] text-xs">
                  <div className="flex items-start gap-2 text-[#007D78]">
                    <Lightbulb className="w-4 h-4 shrink-0 mt-0.5 text-[#007D78]" />
                    <div>
                      <span className="font-bold block text-[#007D78] mb-0.5">
                        Insight / Interpretation
                      </span>
                      <p className="text-[11px] leading-relaxed text-[#102C46]">
                        {msg.interpretation}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Business Inferences */}
              {msg.businessInferences && msg.businessInferences.length > 0 && (
                <div className="bg-[#F8FAFC] p-3 rounded-xl border border-[#E2E8F0] text-xs">
                  <span className="font-bold text-[#1E293B] block mb-1">Key Business Inferences:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-[#475569]">
                    {msg.businessInferences.map((inf, i) => (
                      <li key={i}>{inf}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Strategic Recommendations */}
              {msg.recommendations && msg.recommendations.length > 0 && (
                <div className="bg-[#F0FDF4] p-3 rounded-xl border border-[#BBF7D0] text-xs">
                  <span className="font-bold text-[#166534] block mb-1">Strategic Recommendations:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-[#15803D]">
                    {msg.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 6. Calculation and Verified Evidence Accordion matching reference */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="pt-2 border-t border-[#EEF3F6]">
                  <button
                    onClick={() => toggleEvidence(msg.id)}
                    className="flex items-center justify-between w-full text-xs font-bold text-[#102C46] hover:text-[#009F98] py-1 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Code2 className="w-3.5 h-3.5 text-[#009F98]" />
                      <span>How this was calculated</span>
                    </div>
                    {isEvidenceOpen ? (
                      <ChevronUp className="w-3.5 h-3.5 text-[#52616C]" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-[#52616C]" />
                    )}
                  </button>

                  {isEvidenceOpen && (
                    <div className="mt-2.5 p-3 rounded-xl bg-[#F5F8FA] border border-[#DCE5EB] space-y-2 text-xs">
                      {msg.evidence.map((ev) => (
                        <div key={ev.id} className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-[#52616C] uppercase font-medium">
                              Source Column
                            </span>
                            <code className="text-[11px] bg-white px-2 py-0.5 rounded border border-[#DCE5EB] text-[#102C46] font-mono">
                              {ev.sourceColumn}
                            </code>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-[#52616C] uppercase font-medium">
                              Calculation
                            </span>
                            <code className="text-[11px] bg-white px-2 py-0.5 rounded border border-[#DCE5EB] text-[#102C46] font-mono">
                              {ev.formulaOrQuery}
                            </code>
                          </div>

                          {ev.rowCountAnalyzed !== undefined && (
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] text-[#52616C] uppercase font-medium">
                                Records Analyzed
                              </span>
                              <span className="text-[11px] font-semibold text-[#102C46]">
                                {ev.rowCountAnalyzed.toLocaleString()} rows (IndexedDB)
                              </span>
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-1">
                            <span className="text-[10px] text-[#52616C] uppercase font-medium">
                              Verification
                            </span>
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full">
                              <CheckCircle2 className="w-3 h-3 text-[#216548]" />
                              100% deterministic match
                            </span>
                          </div>
                        </div>
                      ))}

                      {/* Compiled DuckDB Query Transparency */}
                      {msg.rawSql && (
                        <div className="pt-2 border-t border-[#DCE5EB] space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-[#52616C] uppercase font-bold">
                              Compiled DuckDB Query
                            </span>
                            {msg.executionTimeMs !== undefined && (
                              <span className="text-[10px] text-[#009F98] font-bold">
                                {msg.executionTimeMs} ms
                              </span>
                            )}
                          </div>
                          <pre className="p-2 rounded-lg bg-[#102C46] text-[#A6E8E4] font-mono text-[10px] overflow-x-auto whitespace-pre-wrap">
                            {msg.rawSql}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* 7. Follow-up Suggestions Chips matching reference */}
              {msg.suggestedFollowUps && msg.suggestedFollowUps.length > 0 && (
                <div className="pt-2 border-t border-[#EEF3F6]">
                  <span className="text-[10px] text-[#52616C] uppercase font-bold tracking-wider block mb-2">
                    Follow-up Suggestions
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.suggestedFollowUps.map((sug, sIdx) => (
                      <button
                        key={sIdx}
                        onClick={() => onSelectQuestion(sug)}
                        className="px-3 py-1 rounded-full border border-[#DCE5EB] bg-[#F5F8FA] hover:border-[#009F98] hover:bg-[#E0F5F3] text-xs text-[#102C46] font-medium transition-colors cursor-pointer shadow-2xs"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Processing Loader State */}
      {isProcessing && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#009F98] text-white flex items-center justify-center shadow-2xs">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            </div>
            <span className="text-xs font-bold text-[#102C46]">DataLens AI</span>
            <span className="text-[10px] text-[#52616C]">Analyzing...</span>
          </div>

          <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-[#009F98] animate-spin shrink-0" />
            <div>
              <p className="text-xs font-bold text-[#102C46]">Analyzing your dataset...</p>
              <p className="text-[11px] text-[#52616C] mt-0.5">
                Executing deterministic calculations and preparing visual insights...
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

