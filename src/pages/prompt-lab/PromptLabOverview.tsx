import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical,
  Plus,
  Search,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  Cpu,
  Clock,
  Layers,
  Award,
  AlertTriangle,
  Play,
  Check,
  Copy,
  History,
  FileText,
  Trash2,
  RefreshCw,
  GitCompare,
  Sliders,
  DollarSign,
  Tag,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Modal } from '../../components/common/Modal';
import {
  PromptLabApi,
  PromptTemplateItem,
  PromptDetailItem,
  PromptVersionItem,
  ExperimentItem,
  PlaygroundExecuteResult,
} from '../../services/apiClient';
import { StorageService } from '../../services/storageService';

const CATEGORIES = [
  'All',
  'Business Intelligence',
  'Data Analysis',
  'Summarization',
  'Classification',
  'Information Extraction',
  'Content Generation',
  'Custom',
];

export const PromptLabOverview: React.FC = () => {
  const navigate = useNavigate();

  // Navigation tab: 'library' | 'playground' | 'experiments'
  const [activeTab, setActiveTab] = useState<'library' | 'playground' | 'experiments'>('library');

  // Workspace ID
  const currentWorkspaceId = localStorage.getItem('datalens_workspace_id') || 'default-workspace';

  // -------------------------------------------------------------------------
  // PROMPT LIBRARY STATE
  // -------------------------------------------------------------------------
  const [prompts, setPrompts] = useState<PromptTemplateItem[]>([]);
  const [loadingPrompts, setLoadingPrompts] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isCreatePromptOpen, setIsCreatePromptOpen] = useState(false);

  // New Prompt Form
  const [newPromptName, setNewPromptName] = useState('');
  const [newPromptDesc, setNewPromptDesc] = useState('');
  const [newPromptCategory, setNewPromptCategory] = useState('Business Intelligence');
  const [newPromptTags, setNewPromptTags] = useState('kpi, executive, sales');
  const [newPromptSys, setNewPromptSys] = useState('You are an expert enterprise business intelligence advisor.');
  const [newPromptUser, setNewPromptUser] = useState('Analyze the performance of {{product_line}} across {{region}} in Q{{quarter}}.');
  const [newPromptTemp, setNewPromptTemp] = useState(0.7);
  const [newPromptTokens, setNewPromptTokens] = useState(1000);
  const [isSubmittingPrompt, setIsSubmittingPrompt] = useState(false);

  // Version History Modal State
  const [selectedPromptForVersions, setSelectedPromptForVersions] = useState<PromptTemplateItem | null>(null);
  const [versionList, setVersionList] = useState<PromptVersionItem[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);

  // -------------------------------------------------------------------------
  // PLAYGROUND STATE
  // -------------------------------------------------------------------------
  const [playgroundSys, setPlaygroundSys] = useState('You are a senior data analyst.');
  const [playgroundUser, setPlaygroundUser] = useState('Summarize total revenue and profit margin for {{company}} in {{year}}.');
  const [playgroundVars, setPlaygroundVars] = useState<Record<string, string>>({
    company: 'Acme Logistics',
    year: '2025',
  });
  const [playgroundProvider, setPlaygroundProvider] = useState('gemini');
  const [playgroundModel, setPlaygroundModel] = useState('gemini-2.5-flash');
  const [playgroundTemp, setPlaygroundTemp] = useState(0.7);
  const [playgroundMaxTokens, setPlaygroundMaxTokens] = useState(1000);
  const [playgroundLoading, setPlaygroundLoading] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState<PlaygroundExecuteResult | null>(null);
  const [copiedResponse, setCopiedResponse] = useState(false);

  // -------------------------------------------------------------------------
  // EXPERIMENT MANAGER STATE
  // -------------------------------------------------------------------------
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [loadingExperiments, setLoadingExperiments] = useState(false);
  const [isNewExperimentOpen, setIsNewExperimentOpen] = useState(false);
  const [expName, setExpName] = useState('');
  const [expDesc, setExpDesc] = useState('');
  const [expSelectedPromptId, setExpSelectedPromptId] = useState('');
  const [expPromptVersions, setExpPromptVersions] = useState<PromptVersionItem[]>([]);
  const [expSelectedVersionIds, setExpSelectedVersionIds] = useState<string[]>([]);
  const [expTestCaseName, setExpTestCaseName] = useState('Enterprise Benchmark Case 1');
  const [expTestCaseVars, setExpTestCaseVars] = useState('{"product_line": "SaaS Platform", "region": "North America", "quarter": "3"}');
  const [expExpectedKeywords, setExpExpectedKeywords] = useState('performance, variance, growth');
  const [isCreatingExp, setIsCreatingExp] = useState(false);

  // -------------------------------------------------------------------------
  // DATA FETCHING
  // -------------------------------------------------------------------------
  const fetchPrompts = async () => {
    setLoadingPrompts(true);
    try {
      const data = await PromptLabApi.listPrompts(currentWorkspaceId, {
        search: searchQuery || undefined,
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
      });
      setPrompts(data || []);
    } catch {
      // Fallback sample prompts if backend not yet seeded
      setPrompts([
        {
          id: 'sample-p1',
          workspace_id: currentWorkspaceId,
          name: 'Executive KPI Summary Generator',
          description: 'Synthesizes financial and operational metrics into board-ready narrative digests.',
          category: 'Business Intelligence',
          tags: ['kpi', 'executive', 'finance'],
          is_archived: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          versions_count: 2,
          latest_version_number: 2,
        },
        {
          id: 'sample-p2',
          workspace_id: currentWorkspaceId,
          name: 'Customer Feedback Sentiment & Anomaly',
          description: 'Evaluates customer feedback transcripts to isolate churn indicators.',
          category: 'Classification',
          tags: ['sentiment', 'churn', 'customers'],
          is_archived: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          versions_count: 1,
          latest_version_number: 1,
        },
      ]);
    } finally {
      setLoadingPrompts(false);
    }
  };

  const fetchExperiments = async () => {
    setLoadingExperiments(true);
    try {
      const data = await PromptLabApi.listExperiments(currentWorkspaceId);
      setExperiments(data || []);
    } catch {
      // Fallback to local storage experiments if available
      const local = StorageService.getExperiments();
      if (local && local.length > 0) {
        setExperiments(
          local.map((e) => ({
            id: e.id,
            workspace_id: currentWorkspaceId,
            prompt_id: null,
            name: e.title,
            description: e.objective,
            version_ids: e.variants.map((v) => v.id),
            model_config_override: {},
            status: e.status === 'draft' ? 'pending' : e.status,
            created_by: null,
            created_at: e.createdAt,
            updated_at: e.updatedAt,
            test_cases: e.testCases.map((tc) => ({
              id: tc.id,
              experiment_id: e.id,
              name: tc.name,
              variables: { question: tc.businessQuestion },
              expected_output: tc.expectedKeyFact,
              expected_keywords: [],
              created_at: e.createdAt,
            })),
            runs_count: e.testCases.length * e.variants.length,
            completed_runs_count: e.testCases.length * e.variants.length,
          }))
        );
      }
    } finally {
      setLoadingExperiments(false);
    }
  };

  useEffect(() => {
    fetchPrompts();
    fetchExperiments();
  }, [currentWorkspaceId, selectedCategory]);

  // Extract variables whenever user changes playground user prompt
  useEffect(() => {
    const combined = playgroundSys + ' ' + playgroundUser;
    const matches = combined.match(/\{\{([a-zA-Z0-9_]+)\}\}/g) || [];
    const varNames = Array.from(new Set(matches.map((m) => m.replace(/\{\{|\}\}/g, ''))));
    setPlaygroundVars((prev) => {
      const next: Record<string, string> = {};
      varNames.forEach((v) => {
        next[v] = prev[v] !== undefined ? prev[v] : '';
      });
      return next;
    });
  }, [playgroundSys, playgroundUser]);

  // -------------------------------------------------------------------------
  // HANDLERS
  // -------------------------------------------------------------------------
  const handleCreatePrompt = async () => {
    if (!newPromptName.trim() || !newPromptUser.trim()) return;
    setIsSubmittingPrompt(true);
    try {
      const tagsList = newPromptTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      await PromptLabApi.createPrompt(currentWorkspaceId, {
        name: newPromptName.trim(),
        description: newPromptDesc.trim() || null,
        category: newPromptCategory,
        tags: tagsList,
        system_prompt: newPromptSys,
        user_prompt_template: newPromptUser,
        model_config_snapshot: {
          provider: 'gemini',
          model: 'gemini-2.5-flash',
          temperature: newPromptTemp,
          max_tokens: newPromptTokens,
        },
        change_description: 'Initial template creation',
      });
      setIsCreatePromptOpen(false);
      fetchPrompts();
    } catch (e: any) {
      alert(`Failed to create prompt: ${e?.message || e}`);
    } finally {
      setIsSubmittingPrompt(false);
    }
  };

  const handleDuplicatePrompt = async (id: string) => {
    try {
      await PromptLabApi.duplicatePrompt(currentWorkspaceId, id);
      fetchPrompts();
    } catch (e: any) {
      alert(`Duplicate failed: ${e?.message || e}`);
    }
  };

  const handleArchivePrompt = async (id: string) => {
    if (!confirm('Are you sure you want to archive this prompt template?')) return;
    try {
      await PromptLabApi.archivePrompt(currentWorkspaceId, id);
      fetchPrompts();
    } catch (e: any) {
      alert(`Archive failed: ${e?.message || e}`);
    }
  };

  const handleOpenVersions = async (p: PromptTemplateItem) => {
    setSelectedPromptForVersions(p);
    setIsVersionModalOpen(true);
    setLoadingVersions(true);
    try {
      const versions = await PromptLabApi.listVersions(currentWorkspaceId, p.id);
      setVersionList(versions);
    } catch {
      setVersionList([]);
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleRestoreVersion = async (promptId: string, versionId: string) => {
    if (!confirm('Restore this version? This will create a new version with its contents.')) return;
    try {
      await PromptLabApi.restoreVersion(currentWorkspaceId, promptId, versionId);
      const updated = await PromptLabApi.listVersions(currentWorkspaceId, promptId);
      setVersionList(updated);
      fetchPrompts();
    } catch (e: any) {
      alert(`Restore failed: ${e?.message || e}`);
    }
  };

  const handleLoadIntoPlayground = (p: PromptTemplateItem) => {
    PromptLabApi.getPrompt(currentWorkspaceId, p.id).then((detail) => {
      if (detail.current_version) {
        setPlaygroundSys(detail.current_version.system_prompt || '');
        setPlaygroundUser(detail.current_version.user_prompt_template || '');
        if (detail.current_version.model_config_snapshot) {
          setPlaygroundTemp(detail.current_version.model_config_snapshot.temperature || 0.7);
          setPlaygroundMaxTokens(detail.current_version.model_config_snapshot.max_tokens || 1000);
        }
      }
      setActiveTab('playground');
    });
  };

  const handleExecutePlayground = async () => {
    setPlaygroundLoading(true);
    try {
      const res = await PromptLabApi.executePlayground(currentWorkspaceId, {
        system_prompt: playgroundSys,
        user_prompt_template: playgroundUser,
        variables: playgroundVars,
        provider: playgroundProvider,
        model: playgroundModel,
        temperature: playgroundTemp,
        max_tokens: playgroundMaxTokens,
      });
      setPlaygroundResult(res);
    } catch (e: any) {
      alert(`Playground execution failed: ${e?.message || e}`);
    } finally {
      setPlaygroundLoading(false);
    }
  };

  const handleCreateExperiment = async () => {
    if (!expName.trim() || expSelectedVersionIds.length < 1) {
      alert('Please provide an experiment name and select at least 1 prompt version.');
      return;
    }

    let parsedVars = {};
    try {
      parsedVars = JSON.parse(expTestCaseVars);
    } catch {
      alert('Invalid JSON in Test Case Variables.');
      return;
    }

    setIsCreatingExp(true);
    try {
      const kwList = expExpectedKeywords.split(',').map((k) => k.trim()).filter(Boolean);
      const created = await PromptLabApi.createExperiment(currentWorkspaceId, {
        name: expName.trim(),
        description: expDesc.trim() || null,
        prompt_id: expSelectedPromptId || null,
        version_ids: expSelectedVersionIds,
        test_cases: [
          {
            name: expTestCaseName.trim(),
            variables: parsedVars,
            expected_output: null,
            expected_keywords: kwList,
          },
        ],
        model_config_override: {},
      });

      // Automatically trigger run
      await PromptLabApi.runExperiment(currentWorkspaceId, created.id);
      setIsNewExperimentOpen(false);
      fetchExperiments();
      navigate(`/prompt-lab/experiments/${created.id}`);
    } catch (e: any) {
      alert(`Experiment creation failed: ${e?.message || e}`);
    } finally {
      setIsCreatingExp(false);
    }
  };

  const handleSelectPromptForExperiment = async (pId: string) => {
    setExpSelectedPromptId(pId);
    if (!pId) {
      setExpPromptVersions([]);
      setExpSelectedVersionIds([]);
      return;
    }
    try {
      const v = await PromptLabApi.listVersions(currentWorkspaceId, pId);
      setExpPromptVersions(v);
      setExpSelectedVersionIds(v.slice(0, 2).map((item) => item.id));
    } catch {
      setExpPromptVersions([]);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#DDF0F5] border border-[#BBDCE8] flex items-center justify-center text-[#009F98]">
            <FlaskConical className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-[#102C46] tracking-tight">Prompt Lab</h1>
              <Badge variant="teal" size="sm">Enterprise AI</Badge>
            </div>
            <p className="text-xs text-[#52616C] mt-0.5">
              Author prompt templates, manage immutable versions, test in real-time, and benchmark performance.
            </p>
          </div>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center bg-[#F5F8FA] p-1 rounded-xl border border-[#DCE5EB]">
          <button
            onClick={() => setActiveTab('library')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'library'
                ? 'bg-white text-[#102C46] shadow-sm border border-[#DCE5EB]'
                : 'text-[#52616C] hover:text-[#102C46]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Prompt Library
          </button>
          <button
            onClick={() => setActiveTab('playground')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'playground'
                ? 'bg-white text-[#102C46] shadow-sm border border-[#DCE5EB]'
                : 'text-[#52616C] hover:text-[#102C46]'
            }`}
          >
            <Play className="w-3.5 h-3.5 text-[#009F98]" />
            Playground
          </button>
          <button
            onClick={() => setActiveTab('experiments')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'experiments'
                ? 'bg-white text-[#102C46] shadow-sm border border-[#DCE5EB]'
                : 'text-[#52616C] hover:text-[#102C46]'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5 text-[#39C3B8]" />
            Experiments & Benchmarks
          </button>
        </div>
      </div>

      {/* =====================================================================
          TAB 1: PROMPT LIBRARY
      ===================================================================== */}
      {activeTab === 'library' && (
        <div className="space-y-6">
          {/* Controls Bar: Search, Category Filter, New Prompt Button */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors cursor-pointer ${
                    selectedCategory === cat
                      ? 'bg-[#009F98] text-white shadow-sm'
                      : 'bg-white border border-[#DCE5EB] text-[#52616C] hover:bg-[#F5F8FA]'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search className="w-4 h-4 text-[#52616C] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search prompt templates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && fetchPrompts()}
                  className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsCreatePromptOpen(true)}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                Create Prompt
              </Button>
            </div>
          </div>

          {/* Prompts Grid */}
          {loadingPrompts ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-white rounded-2xl border border-[#DCE5EB] animate-pulse" />
              ))}
            </div>
          ) : prompts.length === 0 ? (
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-12 text-center space-y-3">
              <FlaskConical className="w-10 h-10 text-[#009F98] mx-auto opacity-40" />
              <h3 className="text-sm font-bold text-[#102C46]">No prompt templates found</h3>
              <p className="text-xs text-[#52616C] max-w-sm mx-auto">
                Create reusable prompts with dynamic variables (e.g. &#123;&#123;metric&#125;&#125;) to standardize analysis across your workspace.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsCreatePromptOpen(true)}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                Create First Prompt
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {prompts.map((p) => (
                <div
                  key={p.id}
                  className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle hover:border-[#009F98] transition-all flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-bold text-[#102C46] line-clamp-1">{p.name}</h3>
                      <Badge variant="teal" size="sm">v{p.latest_version_number}</Badge>
                    </div>

                    <p className="text-xs text-[#52616C] line-clamp-2 leading-relaxed">
                      {p.description || 'No description provided.'}
                    </p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="inline-flex items-center text-[10px] font-semibold bg-[#EDF7FA] text-[#009F98] px-2 py-0.5 rounded-md">
                        {p.category}
                      </span>
                      {p.tags?.slice(0, 3).map((tag, idx) => (
                        <span key={idx} className="inline-flex items-center text-[10px] text-[#52616C] bg-gray-100 px-2 py-0.5 rounded-md">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions Footer */}
                  <div className="pt-4 border-t border-[#DCE5EB] flex items-center justify-between mt-4">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleOpenVersions(p)}
                        className="p-1.5 text-[#52616C] hover:text-[#102C46] hover:bg-[#F5F8FA] rounded-lg transition-colors cursor-pointer"
                        title="Version History & Restore"
                      >
                        <History className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDuplicatePrompt(p.id)}
                        className="p-1.5 text-[#52616C] hover:text-[#102C46] hover:bg-[#F5F8FA] rounded-lg transition-colors cursor-pointer"
                        title="Duplicate Template"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleArchivePrompt(p.id)}
                        className="p-1.5 text-[#52616C] hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                        title="Archive Template"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleLoadIntoPlayground(p)}
                      rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      Test in Playground
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 2: INTERACTIVE PLAYGROUND
      ===================================================================== */}
      {activeTab === 'playground' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: Prompt Editor & Dynamic Variables (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-4">
              <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-3">
                <span className="text-xs font-bold text-[#102C46] uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#009F98]" />
                  System Prompt
                </span>
                <span className="text-[11px] text-[#52616C]">Defines model persona and constraints</span>
              </div>
              <textarea
                rows={3}
                value={playgroundSys}
                onChange={(e) => setPlaygroundSys(e.target.value)}
                placeholder="Enter system prompt instructions..."
                className="w-full text-xs p-3 font-mono bg-[#F8FAFB] border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
              />
            </div>

            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle space-y-4">
              <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-3">
                <span className="text-xs font-bold text-[#102C46] uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-[#009F98]" />
                  User Prompt Template
                </span>
                <span className="text-[11px] text-[#009F98] font-medium">Use &#123;&#123;variable&#125;&#125; for dynamic inputs</span>
              </div>
              <textarea
                rows={5}
                value={playgroundUser}
                onChange={(e) => setPlaygroundUser(e.target.value)}
                placeholder="E.g. Analyze sales for {{region}} in quarter {{quarter}}..."
                className="w-full text-xs p-3 font-mono bg-[#F8FAFB] border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
              />

              {/* Dynamic Variables Binding Section */}
              {Object.keys(playgroundVars).length > 0 && (
                <div className="pt-3 border-t border-[#DCE5EB] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#102C46]">Detected Prompt Variables ({Object.keys(playgroundVars).length})</span>
                    <span className="text-[11px] text-[#52616C]">Injected at runtime</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.keys(playgroundVars).map((vName) => (
                      <div key={vName} className="space-y-1">
                        <label className="text-[11px] font-mono font-medium text-[#009F98]">
                          &#123;&#123;{vName}&#125;&#125;
                        </label>
                        <input
                          type="text"
                          value={playgroundVars[vName]}
                          onChange={(e) =>
                            setPlaygroundVars((prev) => ({
                              ...prev,
                              [vName]: e.target.value,
                            }))
                          }
                          placeholder={`Enter value for ${vName}`}
                          className="w-full px-3 py-1.5 text-xs bg-[#F8FAFB] border border-[#DCE5EB] rounded-lg text-[#102C46] focus:outline-none focus:border-[#009F98]"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Execution Parameter Controls */}
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4 text-xs">
                <div>
                  <label className="block text-[11px] font-medium text-[#52616C] mb-1">Provider</label>
                  <select
                    value={playgroundProvider}
                    onChange={(e) => setPlaygroundProvider(e.target.value)}
                    className="px-2.5 py-1.5 text-xs bg-[#F8FAFB] border border-[#DCE5EB] rounded-lg text-[#102C46] focus:outline-none"
                  >
                    <option value="gemini">Google Gemini (Active Provider)</option>
                    <option value="mock">Simulated Engine (Offline)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-[#52616C] mb-1">Model</label>
                  <select
                    value={playgroundModel}
                    onChange={(e) => setPlaygroundModel(e.target.value)}
                    className="px-2.5 py-1.5 text-xs bg-[#F8FAFB] border border-[#DCE5EB] rounded-lg text-[#102C46] focus:outline-none"
                  >
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                    <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-[#52616C] mb-1">Temperature ({playgroundTemp})</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={playgroundTemp}
                    onChange={(e) => setPlaygroundTemp(parseFloat(e.target.value))}
                    className="w-24 accent-[#009F98]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-[#52616C] mb-1">Max Tokens</label>
                  <input
                    type="number"
                    min="100"
                    max="4000"
                    value={playgroundMaxTokens}
                    onChange={(e) => setPlaygroundMaxTokens(parseInt(e.target.value) || 1000)}
                    className="w-20 px-2 py-1 text-xs bg-[#F8FAFB] border border-[#DCE5EB] rounded-lg text-[#102C46]"
                  />
                </div>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={handleExecutePlayground}
                isLoading={playgroundLoading}
                leftIcon={<Play className="w-4 h-4 fill-white" />}
              >
                Execute in Playground
              </Button>
            </div>
          </div>

          {/* Right Panel: Output & Execution Telemetry (5 cols) */}
          <div className="lg:col-span-5 space-y-5">
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle flex flex-col h-[520px]">
              <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#102C46] uppercase tracking-wider">Generated Output</span>
                  {playgroundResult?.is_simulated ? (
                    <Badge variant="gold" size="sm">SIMULATED</Badge>
                  ) : playgroundResult ? (
                    <Badge variant="teal" size="sm">LIVE PROVIDER</Badge>
                  ) : null}
                </div>

                {playgroundResult && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(playgroundResult.response_text);
                      setCopiedResponse(true);
                      setTimeout(() => setCopiedResponse(false), 2000);
                    }}
                    className="text-xs text-[#009F98] hover:text-[#007D78] flex items-center gap-1 cursor-pointer font-medium"
                  >
                    {copiedResponse ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedResponse ? 'Copied' : 'Copy'}
                  </button>
                )}
              </div>

              {/* Output Content */}
              <div className="flex-1 overflow-y-auto font-mono text-xs text-[#102C46] bg-[#F8FAFB] p-4 rounded-xl border border-[#DCE5EB] whitespace-pre-wrap leading-relaxed">
                {playgroundLoading ? (
                  <div className="flex items-center justify-center h-full text-[#52616C] gap-2">
                    <div className="w-4 h-4 border-2 border-[#009F98] border-t-transparent rounded-full animate-spin" />
                    <span>Executing prompt instructions...</span>
                  </div>
                ) : playgroundResult ? (
                  playgroundResult.response_text
                ) : (
                  <span className="text-gray-400">
                    Execution results will appear here after clicking "Execute in Playground".
                  </span>
                )}
              </div>

              {/* Telemetry Metrics Bar */}
              {playgroundResult && (
                <div className="grid grid-cols-4 gap-2 pt-3 mt-3 border-t border-[#DCE5EB] text-center">
                  <div className="bg-[#EDF7FA] p-2 rounded-lg">
                    <span className="text-[10px] text-[#52616C] block flex items-center justify-center gap-1">
                      <Clock className="w-3 h-3 text-[#009F98]" /> Latency
                    </span>
                    <span className="text-xs font-bold text-[#102C46]">{playgroundResult.latency_ms} ms</span>
                  </div>

                  <div className="bg-[#EDF7FA] p-2 rounded-lg">
                    <span className="text-[10px] text-[#52616C] block flex items-center justify-center gap-1">
                      <Cpu className="w-3 h-3 text-[#009F98]" /> In Tokens
                    </span>
                    <span className="text-xs font-bold text-[#102C46]">{playgroundResult.input_tokens || 'N/A'}</span>
                  </div>

                  <div className="bg-[#EDF7FA] p-2 rounded-lg">
                    <span className="text-[10px] text-[#52616C] block flex items-center justify-center gap-1">
                      <Cpu className="w-3 h-3 text-[#39C3B8]" /> Out Tokens
                    </span>
                    <span className="text-xs font-bold text-[#102C46]">{playgroundResult.output_tokens || 'N/A'}</span>
                  </div>

                  <div className="bg-[#EDF7FA] p-2 rounded-lg">
                    <span className="text-[10px] text-[#52616C] block flex items-center justify-center gap-1">
                      <DollarSign className="w-3 h-3 text-[#009F98]" /> Est. Cost
                    </span>
                    <span className="text-xs font-bold text-[#102C46]">
                      ${playgroundResult.estimated_cost_usd !== null ? playgroundResult.estimated_cost_usd.toFixed(5) : '0.00'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 3: EXPERIMENTS & BENCHMARKS
      ===================================================================== */}
      {activeTab === 'experiments' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#102C46]">Controlled Prompt Benchmarks</h2>
              <p className="text-xs text-[#52616C]">Compare multi-version prompt strategies across standardized test cases.</p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsNewExperimentOpen(true)}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              New Experiment
            </Button>
          </div>

          {loadingExperiments ? (
            <div className="h-48 bg-white rounded-2xl border border-[#DCE5EB] animate-pulse" />
          ) : experiments.length === 0 ? (
            <div className="bg-white rounded-2xl border border-[#DCE5EB] p-12 text-center space-y-3">
              <TrendingUp className="w-10 h-10 text-[#009F98] mx-auto opacity-40" />
              <h3 className="text-sm font-bold text-[#102C46]">No experiments created yet</h3>
              <p className="text-xs text-[#52616C] max-w-sm mx-auto">
                Set up a benchmark experiment to compare two or more prompt versions against your business test cases.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsNewExperimentOpen(true)}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                Create First Benchmark
              </Button>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-subtle">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAFB] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
                  <tr>
                    <th className="py-3 px-4">Experiment Name</th>
                    <th className="py-3 px-4">Target Versions</th>
                    <th className="py-3 px-4">Test Cases</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Created Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#DCE5EB]">
                  {experiments.map((exp) => (
                    <tr
                      key={exp.id}
                      onClick={() => navigate(`/prompt-lab/experiments/${exp.id}`)}
                      className="hover:bg-[#F5F8FA] transition-colors cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <span className="font-bold text-[#102C46] block">{exp.name}</span>
                        {exp.description && (
                          <span className="text-[11px] text-[#52616C] line-clamp-1">{exp.description}</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className="inline-flex items-center gap-1 bg-[#EDF7FA] text-[#009F98] px-2 py-0.5 rounded-md font-semibold">
                          {exp.version_ids?.length || 2} versions
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[#52616C]">
                        {exp.test_cases?.length || 1} test case(s)
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                            exp.status === 'completed'
                              ? 'bg-[#E4F3EC] text-[#216548]'
                              : exp.status === 'running'
                              ? 'bg-[#EDF7FA] text-[#009F98] animate-pulse'
                              : 'bg-gray-100 text-[#52616C]'
                          }`}
                        >
                          {exp.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                          {exp.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[#52616C]">
                        {new Date(exp.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <span className="text-[#009F98] font-semibold hover:underline inline-flex items-center gap-1">
                          View Dashboard <ArrowRight className="w-3.5 h-3.5" />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          MODAL 1: CREATE PROMPT TEMPLATE
      ===================================================================== */}
      <Modal
        isOpen={isCreatePromptOpen}
        onClose={() => setIsCreatePromptOpen(false)}
        title="Create Prompt Template"
        subtitle="Define a standardized prompt template and publish Version 1."
        maxWidth="2xl"
      >
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#102C46] mb-1">Prompt Name *</label>
              <input
                type="text"
                value={newPromptName}
                onChange={(e) => setNewPromptName(e.target.value)}
                placeholder="E.g. Sales Margin Analyzer"
                className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#102C46] mb-1">Category</label>
              <select
                value={newPromptCategory}
                onChange={(e) => setNewPromptCategory(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
              >
                {CATEGORIES.filter((c) => c !== 'All').map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#102C46] mb-1">Description</label>
            <input
              type="text"
              value={newPromptDesc}
              onChange={(e) => setNewPromptDesc(e.target.value)}
              placeholder="Brief description of the prompt purpose..."
              className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#102C46] mb-1">Tags (comma separated)</label>
            <input
              type="text"
              value={newPromptTags}
              onChange={(e) => setNewPromptTags(e.target.value)}
              placeholder="kpi, quarterly, finance"
              className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#102C46] mb-1">System Instructions</label>
            <textarea
              rows={2}
              value={newPromptSys}
              onChange={(e) => setNewPromptSys(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-[#F8FAFB] border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-[#102C46]">User Prompt Template *</label>
              <span className="text-[11px] text-[#009F98]">Use &#123;&#123;variable&#125;&#125; syntax</span>
            </div>
            <textarea
              rows={4}
              value={newPromptUser}
              onChange={(e) => setNewPromptUser(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-[#F8FAFB] border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#DCE5EB]">
            <Button variant="ghost" size="sm" onClick={() => setIsCreatePromptOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleCreatePrompt}
              isLoading={isSubmittingPrompt}
            >
              Publish Version 1
            </Button>
          </div>
        </div>
      </Modal>

      {/* =====================================================================
          MODAL 2: VERSION HISTORY & RESTORE
      ===================================================================== */}
      <Modal
        isOpen={isVersionModalOpen}
        onClose={() => setIsVersionModalOpen(false)}
        title={`Version History — ${selectedPromptForVersions?.name || ''}`}
        subtitle="Immutable version timeline. Historical versions cannot be mutated."
        maxWidth="3xl"
      >
        <div className="space-y-4 pt-2">
          {loadingVersions ? (
            <div className="py-8 text-center text-xs text-[#52616C]">Loading versions...</div>
          ) : versionList.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#52616C]">No versions found.</div>
          ) : (
            <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
              {versionList.map((ver) => (
                <div
                  key={ver.id}
                  className="bg-[#F8FAFB] border border-[#DCE5EB] rounded-xl p-4 space-y-2 hover:border-[#009F98] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="teal" size="sm">Version {ver.version_number}</Badge>
                      <span className="text-xs font-bold text-[#102C46]">
                        {ver.change_description || 'Routine revision'}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-[#52616C]">
                        {new Date(ver.created_at).toLocaleString()}
                      </span>
                      {selectedPromptForVersions && (
                        <button
                          onClick={() => handleRestoreVersion(selectedPromptForVersions.id, ver.id)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-[#009F98] bg-white border border-[#DCE5EB] rounded-lg hover:bg-[#EDF7FA] cursor-pointer"
                        >
                          Restore
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="text-[11px] font-mono text-[#52616C] bg-white p-2.5 rounded-lg border border-[#DCE5EB] line-clamp-2">
                    {ver.user_prompt_template}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end pt-3 border-t border-[#DCE5EB]">
            <Button variant="secondary" size="sm" onClick={() => setIsVersionModalOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>

      {/* =====================================================================
          MODAL 3: NEW BENCHMARK EXPERIMENT
      ===================================================================== */}
      <Modal
        isOpen={isNewExperimentOpen}
        onClose={() => setIsNewExperimentOpen(false)}
        title="Create Benchmark Experiment"
        subtitle="Benchmark multiple prompt versions across standardized test inputs."
        maxWidth="2xl"
      >
        <div className="space-y-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-[#102C46] mb-1">Experiment Name *</label>
            <input
              type="text"
              value={expName}
              onChange={(e) => setExpName(e.target.value)}
              placeholder="E.g. Q3 Executive Summary Benchmark"
              className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#102C46] mb-1">Select Prompt Template</label>
            <select
              value={expSelectedPromptId}
              onChange={(e) => handleSelectPromptForExperiment(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:border-[#009F98]"
            >
              <option value="">-- Choose a Prompt Template --</option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.category})
                </option>
              ))}
            </select>
          </div>

          {expPromptVersions.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-[#102C46] mb-1">
                Select Prompt Versions to Compare ({expSelectedVersionIds.length} selected)
              </label>
              <div className="grid grid-cols-2 gap-2">
                {expPromptVersions.map((v) => {
                  const isChecked = expSelectedVersionIds.includes(v.id);
                  return (
                    <label
                      key={v.id}
                      className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs cursor-pointer ${
                        isChecked ? 'bg-[#EDF7FA] border-[#009F98] text-[#102C46]' : 'bg-white border-[#DCE5EB] text-[#52616C]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setExpSelectedVersionIds([...expSelectedVersionIds, v.id]);
                          } else {
                            setExpSelectedVersionIds(expSelectedVersionIds.filter((id) => id !== v.id));
                          }
                        }}
                        className="accent-[#009F98]"
                      />
                      <span className="font-bold">v{v.version_number}</span>
                      <span className="line-clamp-1">{v.change_description || 'Version ' + v.version_number}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="border-t border-[#DCE5EB] pt-3 space-y-3">
            <h4 className="text-xs font-bold text-[#102C46]">Standardized Test Case</h4>
            <div>
              <label className="block text-xs font-medium text-[#52616C] mb-1">Test Case Title</label>
              <input
                type="text"
                value={expTestCaseName}
                onChange={(e) => setExpTestCaseName(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-white border border-[#DCE5EB] rounded-lg text-[#102C46]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#52616C] mb-1">Input Variables (JSON Map)</label>
              <textarea
                rows={2}
                value={expTestCaseVars}
                onChange={(e) => setExpTestCaseVars(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono bg-[#F8FAFB] border border-[#DCE5EB] rounded-lg text-[#102C46]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#52616C] mb-1">Required Keywords (for evaluation)</label>
              <input
                type="text"
                value={expExpectedKeywords}
                onChange={(e) => setExpExpectedKeywords(e.target.value)}
                placeholder="performance, variance, growth"
                className="w-full px-3 py-1.5 text-xs bg-white border border-[#DCE5EB] rounded-lg text-[#102C46]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#DCE5EB]">
            <Button variant="ghost" size="sm" onClick={() => setIsNewExperimentOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleCreateExperiment}
              isLoading={isCreatingExp}
              leftIcon={<Play className="w-4 h-4 fill-white" />}
            >
              Launch Benchmark Run
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
