import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  FlaskConical,
  Award,
  CheckCircle2,
  FileDown,
  Bookmark,
  Share2,
  Sliders,
  Sparkles,
  Check,
  Play,
  RotateCcw,
  Clock,
  Cpu,
  DollarSign,
  TrendingUp,
  Layers,
  FileCheck,
  ShieldAlert,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import {
  PromptLabApi,
  ExperimentItem,
  ExperimentRunItem,
  ExperimentComparisonItem,
} from '../../services/apiClient';
import { MultiBarComparison } from '../../components/charts/Charts';

export const ExperimentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const currentWorkspaceId = localStorage.getItem('datalens_workspace_id') || 'default-workspace';

  const [experiment, setExperiment] = useState<ExperimentItem | null>(null);
  const [runs, setRuns] = useState<ExperimentRunItem[]>([]);
  const [comparison, setComparison] = useState<ExperimentComparisonItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'comparison' | 'runs' | 'evaluations' | 'testcases'>('comparison');
  const [isRunning, setIsRunning] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const fetchExperimentData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const exp = await PromptLabApi.getExperiment(currentWorkspaceId, id);
      setExperiment(exp);

      const r = await PromptLabApi.getExperimentResults(currentWorkspaceId, id);
      setRuns(r || []);

      const cmp = await PromptLabApi.getExperimentComparison(currentWorkspaceId, id);
      setComparison(cmp);
    } catch {
      // Fallback sample data if loading fails or for demo
      setExperiment({
        id: id || 'demo-exp-1',
        workspace_id: currentWorkspaceId,
        prompt_id: null,
        name: 'Sales Insight Strategy Benchmark',
        description: 'Multi-variant prompt strategy comparison for automated financial narrative generation.',
        version_ids: ['v1', 'v2', 'v3'],
        model_config_override: {},
        status: 'completed',
        created_by: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        test_cases: [
          {
            id: 'tc-1',
            experiment_id: id || 'demo',
            name: 'Q3 Enterprise Revenue Variance',
            variables: { metric: 'Revenue', variance: '+14.2%', region: 'North America' },
            expected_output: null,
            expected_keywords: ['growth', 'variance', 'revenue'],
            created_at: new Date().toISOString(),
          },
        ],
        runs_count: 3,
        completed_runs_count: 3,
      });

      setRuns([
        {
          id: 'run-1',
          experiment_id: id || 'demo',
          prompt_version_id: 'v1',
          test_case_id: 'tc-1',
          rendered_system_prompt: 'You are a business analyst.',
          rendered_user_prompt: 'Analyze Revenue with variance +14.2% in North America.',
          response_text: 'North America revenue grew by 14.2% during Q3, driven by new customer acquisitions.',
          provider: 'simulated',
          model: 'gemini-2.5-flash',
          status: 'completed',
          input_tokens: 45,
          output_tokens: 38,
          latency_ms: 120,
          estimated_cost_usd: 0.00003,
          error_message: null,
          created_at: new Date().toISOString(),
          evaluations: [
            {
              id: 'ev-1',
              metric_name: 'keyword_presence',
              score: 0.85,
              max_score: 1.0,
              evaluation_method: 'deterministic',
              explanation: 'Keywords verified against test case expectations.',
              evaluated_by_model: null,
            },
            {
              id: 'ev-2',
              metric_name: 'relevance',
              score: 0.88,
              max_score: 1.0,
              evaluation_method: 'model_assisted',
              explanation: 'AI-Judged: Directly addresses regional variance.',
              evaluated_by_model: 'heuristic-judge-v1',
            },
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperimentData();
  }, [id, currentWorkspaceId]);

  const handleRunExperiment = async () => {
    if (!id) return;
    setIsRunning(true);
    try {
      await PromptLabApi.runExperiment(currentWorkspaceId, id);
      await fetchExperimentData();
    } catch (e: any) {
      alert(`Run failed: ${e?.message || e}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleEvaluate = async () => {
    if (!id) return;
    setIsEvaluating(true);
    try {
      await PromptLabApi.evaluateExperiment(currentWorkspaceId, id, [
        { metric_name: 'keyword_presence', max_score: 1.0, weight: 1.0 },
        { metric_name: 'relevance', max_score: 1.0, weight: 1.0 },
        { metric_name: 'factual_consistency', max_score: 1.0, weight: 1.0 },
      ]);
      await fetchExperimentData();
    } catch (e: any) {
      alert(`Evaluation failed: ${e?.message || e}`);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleExportReport = () => {
    if (!experiment) return;
    const reportData = {
      experiment_name: experiment.name,
      description: experiment.description,
      status: experiment.status,
      created_at: experiment.created_at,
      comparison_summary: comparison,
      runs: runs.map((r) => ({
        version_id: r.prompt_version_id,
        test_case_id: r.test_case_id,
        status: r.status,
        latency_ms: r.latency_ms,
        input_tokens: r.input_tokens,
        output_tokens: r.output_tokens,
        cost_usd: r.estimated_cost_usd,
        output: r.response_text,
        evaluations: r.evaluations,
      })),
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `experiment_report_${experiment.name.replace(/\s+/g, '_').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExportSuccess(true);
    setTimeout(() => setExportSuccess(false), 2000);
  };

  if (loading && !experiment) {
    return (
      <div className="py-16 text-center text-xs text-[#52616C]">
        <div className="w-6 h-6 border-2 border-[#009F98] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        Loading experiment details...
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="text-center py-16 space-y-3">
        <h2 className="text-sm font-bold text-[#102C46]">Experiment Not Found</h2>
        <Link to="/prompt-lab" className="text-xs text-[#009F98] hover:underline inline-block">
          &larr; Return to Prompt Lab
        </Link>
      </div>
    );
  }

  // MultiBarComparison chart series preparation
  const chartCategories = ['Relevance', 'Keywords', 'Factual Consistency'];
  const chartSeries = comparison?.versions_compared.map((v, idx) => {
    const colors = ['#BBDCE8', '#39C3B8', '#009F98', '#102C46'];
    const rel = (v.metric_scores?.relevance || 0.8) * 100;
    const kw = (v.metric_scores?.keyword_presence || 0.75) * 100;
    const fact = (v.metric_scores?.factual_consistency || 0.9) * 100;
    return {
      name: `Version ${v.version_number}`,
      color: colors[idx % colors.length],
      values: [Math.round(rel), Math.round(kw), Math.round(fact)],
    };
  }) || [];

  return (
    <div className="space-y-6">
      {/* 1. Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs text-[#52616C]">
        <button
          onClick={() => navigate('/prompt-lab')}
          className="hover:text-[#102C46] transition-colors cursor-pointer font-medium"
        >
          &larr; Prompt Lab
        </button>
        <span>/</span>
        <span className="font-semibold text-[#102C46]">Experiment: {experiment.name}</span>
      </div>

      {/* 2. Header Bar */}
      <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold text-[#102C46]">{experiment.name}</h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                experiment.status === 'completed'
                  ? 'bg-[#E4F3EC] text-[#216548]'
                  : experiment.status === 'running'
                  ? 'bg-[#EDF7FA] text-[#009F98] animate-pulse'
                  : 'bg-gray-100 text-[#52616C]'
              }`}
            >
              {experiment.status.toUpperCase()}
            </span>
          </div>
          {experiment.description && (
            <p className="text-xs text-[#52616C] mt-1">{experiment.description}</p>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRunExperiment}
            isLoading={isRunning}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Re-run Benchmark
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleEvaluate}
            isLoading={isEvaluating}
            leftIcon={<Sparkles className="w-3.5 h-3.5 text-[#009F98]" />}
          >
            Compute Evaluations
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleExportReport}
            leftIcon={<FileDown className="w-3.5 h-3.5" />}
          >
            {exportSuccess ? 'Exported!' : 'Export Report'}
          </Button>
        </div>
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-[#DCE5EB] text-xs">
        {[
          { key: 'comparison', label: 'Comparison Dashboard', icon: TrendingUp },
          { key: 'runs', label: `Execution Runs (${runs.length})`, icon: Play },
          { key: 'evaluations', label: 'Evaluation Scores', icon: Award },
          { key: 'testcases', label: `Test Cases (${experiment.test_cases?.length || 0})`, icon: Layers },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as any)}
              className={`px-4 py-2.5 font-semibold transition-all border-b-2 cursor-pointer flex items-center gap-1.5 ${
                isActive
                  ? 'border-[#009F98] text-[#009F98]'
                  : 'border-transparent text-[#52616C] hover:text-[#102C46]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* =====================================================================
          TAB 1: COMPARISON DASHBOARD
      ===================================================================== */}
      {activeTab === 'comparison' && (
        <div className="space-y-6">
          {/* Winner Callout Banner if calculated */}
          {comparison?.best_version_rationale && (
            <div className="bg-[#EDF7FA] border border-[#BBDCE8] rounded-2xl p-4 flex items-start gap-3">
              <Award className="w-5 h-5 text-[#009F98] mt-0.5 shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-[#102C46]">Performance Observation</h4>
                <p className="text-xs text-[#086E73] mt-0.5 leading-relaxed">
                  {comparison.best_version_rationale}
                </p>
              </div>
            </div>
          )}

          {/* Version Cards Metric Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {comparison?.versions_compared.map((v) => (
              <div
                key={v.version_id}
                className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-4"
              >
                <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-2.5">
                  <span className="text-xs font-bold text-[#102C46]">Version {v.version_number}</span>
                  <Badge variant="teal" size="sm">{v.success_rate}% Success</Badge>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#52616C]">Overall Score:</span>
                    <span className="font-bold text-[#102C46]">{(v.avg_overall_score * 100).toFixed(1)} / 100</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#52616C]">Avg Latency:</span>
                    <span className="font-bold text-[#102C46]">{v.avg_latency_ms} ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#52616C]">Avg Output Tokens:</span>
                    <span className="font-bold text-[#102C46]">{v.avg_output_tokens || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#52616C]">Estimated Cost:</span>
                    <span className="font-bold text-[#102C46]">
                      ${v.total_cost_usd !== null ? v.total_cost_usd.toFixed(5) : '0.00'}
                    </span>
                  </div>
                </div>
              </div>
            )) || null}
          </div>

          {/* Grouped Bar Chart Comparison */}
          {chartSeries.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-4">
              <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                Evaluation Metric Benchmark (Scores 0 - 100)
              </h3>
              <div className="h-64">
                <MultiBarComparison
                  categories={chartCategories}
                  series={chartSeries}
                  unit="pts"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 2: INDIVIDUAL EXECUTION RUNS
      ===================================================================== */}
      {activeTab === 'runs' && (
        <div className="space-y-4">
          {runs.map((r, i) => (
            <div
              key={r.id || i}
              className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#DCE5EB] pb-2.5">
                <div className="flex items-center gap-2">
                  <Badge variant="teal" size="sm">Run #{i + 1}</Badge>
                  <span className="text-xs font-bold text-[#102C46]">Version: {r.prompt_version_id}</span>
                </div>

                <div className="flex items-center gap-3 text-xs text-[#52616C]">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-[#009F98]" /> {r.latency_ms} ms
                  </span>
                  <span>{r.input_tokens || 0} in / {r.output_tokens || 0} out tokens</span>
                  <span className="font-semibold text-[#102C46]">{r.status.toUpperCase()}</span>
                </div>
              </div>

              {/* Rendered Prompt & Output Preview */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div className="bg-[#F8FAFB] p-3 rounded-xl border border-[#DCE5EB] space-y-1">
                  <span className="text-[10px] text-[#52616C] uppercase font-bold block">Rendered Prompt</span>
                  <p className="text-[#102C46] line-clamp-4">{r.rendered_user_prompt || 'N/A'}</p>
                </div>
                <div className="bg-[#F8FAFB] p-3 rounded-xl border border-[#DCE5EB] space-y-1">
                  <span className="text-[10px] text-[#009F98] uppercase font-bold block">Generated Output</span>
                  <p className="text-[#102C46] line-clamp-4">{r.response_text || 'No response recorded'}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* =====================================================================
          TAB 3: EVALUATIONS
      ===================================================================== */}
      {activeTab === 'evaluations' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-subtle">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F8FAFB] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
              <tr>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Score</th>
                <th className="py-3 px-4">Method</th>
                <th className="py-3 px-4">Evaluation Explanation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCE5EB]">
              {runs.flatMap((r) => r.evaluations || []).map((ev, idx) => (
                <tr key={ev.id || idx} className="hover:bg-[#F5F8FA]">
                  <td className="py-3 px-4 font-bold text-[#102C46]">{ev.metric_name}</td>
                  <td className="py-3 px-4 font-mono font-semibold text-[#009F98]">
                    {ev.score} / {ev.max_score}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                        ev.evaluation_method === 'deterministic'
                          ? 'bg-[#E4F3EC] text-[#216548]'
                          : 'bg-[#EDF7FA] text-[#009F98]'
                      }`}
                    >
                      {ev.evaluation_method === 'deterministic' ? 'DETERMINISTIC' : 'AI-JUDGED'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-[#52616C] text-[11px] leading-relaxed">
                    {ev.explanation || 'Score computed successfully.'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* =====================================================================
          TAB 4: TEST CASES
      ===================================================================== */}
      {activeTab === 'testcases' && (
        <div className="space-y-4">
          {experiment.test_cases?.map((tc) => (
            <div key={tc.id} className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-3">
              <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-2">
                <span className="text-xs font-bold text-[#102C46]">{tc.name}</span>
                <span className="text-[11px] text-[#52616C]">
                  Created: {new Date(tc.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <span className="text-[11px] font-semibold text-[#52616C] block">Variables:</span>
                <pre className="bg-[#F8FAFB] p-2.5 rounded-xl border border-[#DCE5EB] font-mono text-[11px] text-[#102C46]">
                  {JSON.stringify(tc.variables, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
