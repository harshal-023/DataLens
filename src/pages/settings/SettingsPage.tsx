import React, { useState, useEffect } from 'react';
import {
  User as UserIcon,
  Building,
  Shield,
  Sliders,
  FlaskConical,
  Share2,
  CheckCircle2,
  Key,
  Database,
  Lock,
  Save,
  Trash2,
  ExternalLink,
  Edit2,
  Crown,
  HardDrive,
  Calendar,
  FileText,
  Settings as SettingsIcon,
  Cpu,
  Server,
  Zap,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Tabs } from '../../components/common/Tabs';
import { StorageService } from '../../services/storageService';
import { aiService, AIProviderInfo, AIPrivacyPolicy } from '../../services/aiService';

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('profile');
  const [user, setUser] = useState(StorageService.getUser());
  const [workspace, setWorkspace] = useState(StorageService.getWorkspace());
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Form states
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState('Analyst (Enterprise Permission)');
  const [workspaceName, setWorkspaceName] = useState(workspace.name);

  // AI Providers state
  const [aiProviders, setAiProviders] = useState<AIProviderInfo[]>([]);
  const [routingMode, setRoutingMode] = useState('HYBRID');
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [aiPrivacy, setAiPrivacy] = useState<AIPrivacyPolicy | null>(null);

  useEffect(() => {
    aiService.getProviders().then((res) => {
      setAiProviders(res.providers || []);
      setRoutingMode(res.active_routing_mode || 'HYBRID');
    }).catch(() => {});

    aiService.getOllamaModels().then((res) => {
      setOllamaOnline(res.is_online);
      setOllamaModels(res.models || []);
    }).catch(() => {});
  }, []);

  const tabs = [
    { id: 'profile', label: 'User Profile', icon: <UserIcon className="w-3.5 h-3.5" /> },
    { id: 'workspace', label: 'Workspace', icon: <Building className="w-3.5 h-3.5" /> },
    { id: 'ai', label: 'AI Architecture & Hybrid Routing', icon: <Cpu className="w-3.5 h-3.5" /> },
    { id: 'security', label: 'Security & Access', icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'templates', label: 'Prompt Templates', icon: <FlaskConical className="w-3.5 h-3.5" /> },
    { id: 'sharing', label: 'Sharing Governance', icon: <Share2 className="w-3.5 h-3.5" /> },
  ];

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    const updated = { ...user, name, email };
    StorageService.setUser(updated);
    setUser(updated);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  const handleSaveWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    const updated = { ...workspace, name: workspaceName };
    StorageService.setWorkspace(updated);
    setWorkspace(updated);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header matching reference */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs">
            <SettingsIcon className="w-6 h-6 text-[#009F98]" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-serif text-[#102C46] tracking-tight">
              Settings & Governance
            </h1>
            <p className="text-xs text-[#52616C] mt-1 font-medium">
              Manage your personal profile, workspace parameters, prompt templates, and security controls.
            </p>
          </div>
        </div>

        {savedSuccess && (
          <span className="text-xs font-semibold text-[#216548] bg-[#E4F3EC] px-3 py-1.5 rounded-full border border-[#C3E7D5] flex items-center gap-1.5 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4" />
            Changes saved successfully!
          </span>
        )}
      </div>

      {/* 2. Navigation Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* 3. Tab 1: Profile (3-Card Layout matching Screen 6 of reference) */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {/* Left Card: Avatar & Role Summary (approx 3 cols) */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle flex flex-col items-center justify-between text-center relative overflow-hidden">
            {/* Flowing soft ice-blue wave gradient at the bottom matching reference */}
            <div className="absolute -bottom-6 -left-6 -right-6 h-28 bg-gradient-to-t from-[#DDF0F5] to-transparent pointer-events-none rounded-b-2xl" />

            <div className="flex flex-col items-center w-full z-10 pt-4">
              {/* Large circular teal avatar with edit pencil badge */}
              <div className="relative mb-4">
                <div className="w-24 h-24 rounded-full bg-[#009F98] text-white flex items-center justify-center text-3xl font-bold shadow-elevated">
                  HS
                </div>
                <button
                  type="button"
                  onClick={() => alert('Change avatar: Select image from files.')}
                  className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-white border border-[#DCE5EB] shadow-subtle flex items-center justify-center text-[#52616C] hover:text-[#009F98] transition-colors cursor-pointer"
                  title="Change avatar"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              </div>

              <h3 className="text-base font-bold text-[#102C46]">Harshal Sharma</h3>
              <p className="text-xs text-[#52616C] mt-0.5 font-medium">Analyst</p>
            </div>

            <div className="w-full z-10 pt-8 pb-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#007D78] bg-[#EDF7FA] px-3 py-1 rounded-full border border-[#BBDCE8]">
                Enterprise Account Active
              </span>
            </div>
          </div>

          {/* Middle Card: Profile Form (approx 6 cols) */}
          <div className="lg:col-span-6 bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle flex flex-col justify-between">
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#102C46] mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98] shadow-2xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#102C46] mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98] shadow-2xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#102C46] mb-1.5">
                  Assigned Role
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] font-medium focus:outline-none focus:ring-2 focus:ring-[#009F98] cursor-pointer shadow-2xs"
                >
                  <option value="Analyst (Enterprise Permission)">
                    Analyst (Enterprise Permission)
                  </option>
                  <option value="Executive Viewer">Executive Viewer</option>
                  <option value="Workspace Admin">Workspace Admin</option>
                </select>
              </div>

              {/* Form Buttons: Cancel & Save Changes in Peacock Teal */}
              <div className="flex items-center justify-end gap-2.5 pt-6 border-t border-[#EEF3F6]">
                <button
                  type="button"
                  onClick={() => {
                    setName(user.name);
                    setEmail(user.email);
                  }}
                  className="px-4 py-2 rounded-xl border border-[#DCE5EB] bg-white text-xs font-medium text-[#52616C] hover:bg-[#EEF3F6] hover:text-[#102C46] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#009F98] hover:bg-[#007D78] active:bg-[#086E73] text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>

          {/* Right Card: Account Status matching Screen 6 (approx 3 cols) */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold text-[#102C46] uppercase tracking-wider mb-4">
                Account Status
              </h3>

              <div className="space-y-4">
                {/* Workspace Tier */}
                <div className="flex items-center gap-2 p-3 rounded-xl bg-[#F5F8FA] border border-[#DCE5EB]">
                  <span className="text-sm">👑</span>
                  <div>
                    <span className="text-xs font-bold text-[#102C46] block">Pro Workspace</span>
                    <span className="text-[10px] text-[#52616C]">Tier: Enterprise Annual</span>
                  </div>
                </div>

                {/* Reports Quota */}
                <div className="flex items-center justify-between text-xs py-1 border-b border-[#EEF3F6]">
                  <span className="text-[#52616C] flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>Reports Quota</span>
                  </span>
                  <span className="font-bold text-[#102C46]">12 / 50</span>
                </div>

                {/* Storage Used */}
                <div className="flex items-center justify-between text-xs py-1 border-b border-[#EEF3F6]">
                  <span className="text-[#52616C] flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>Storage Used</span>
                  </span>
                  <span className="font-bold text-[#102C46]">4.2 GB / 10 GB</span>
                </div>

                {/* Member Since */}
                <div className="flex items-center justify-between text-xs py-1 border-b border-[#EEF3F6]">
                  <span className="text-[#52616C] flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>Member Since</span>
                  </span>
                  <span className="font-semibold text-[#102C46]">Mar 10, 2025</span>
                </div>
              </div>
            </div>

            <div className="pt-4">
              <span className="text-[10px] text-[#52616C] block leading-relaxed">
                Billing managed by organization administrator.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Workspace */}
      {activeTab === 'workspace' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-4 max-w-2xl">
          <h3 className="text-sm font-bold text-[#102C46]">Workspace Parameters</h3>
          <form onSubmit={handleSaveWorkspace} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#102C46] mb-1">Workspace Name</label>
              <input
                type="text"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] focus:outline-none focus:ring-1 focus:ring-[#009F98]"
              />
            </div>
            <Button variant="primary" size="sm" type="submit">
              Save Workspace
            </Button>
          </form>
        </div>
      )}

      {/* Tab 3: Security */}
      {activeTab === 'security' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-4 max-w-2xl">
          <h3 className="text-sm font-bold text-[#102C46]">Security & Access Controls</h3>
          <div className="p-4 rounded-xl bg-[#F5F8FA] border border-[#DCE5EB] space-y-2 text-xs text-[#52616C]">
            <p className="font-semibold text-[#102C46]">Multi-Factor Authentication</p>
            <p>SSO integration enforced via enterprise identity provider.</p>
          </div>
        </div>
      )}

      {/* Tab 4: Prompt Templates */}
      {activeTab === 'templates' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-3 max-w-3xl">
          <h3 className="text-sm font-bold text-[#102C46]">Production Prompt Templates</h3>
          <div className="p-3.5 rounded-xl border border-[#DCE5EB] flex items-center justify-between text-xs">
            <div>
              <span className="font-bold text-[#102C46] block">Few-Shot Executive Brief v3</span>
              <span className="text-[#52616C]">Cites deterministic calculations with 97% accuracy score</span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-[#E4F3EC] text-[#216548] font-bold text-[10px]">
              ACTIVE
            </span>
          </div>
        </div>
      )}

      {/* Tab: AI Architecture & Hybrid Routing */}
      {activeTab === 'ai' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-6 max-w-3xl">
          <div className="flex justify-between items-center border-b border-[#DCE5EB] pb-4">
            <div>
              <h3 className="text-base font-bold text-[#102C46]">Unified AI Architecture & Hybrid Routing</h3>
              <p className="text-xs text-[#52616C]">
                Configure Google Gemini cloud intelligence, local Ollama models, task-based routing, and zero-leak privacy policies.
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full bg-[#EAF5F8] text-[#009F98] font-bold text-xs">
              {routingMode}
            </span>
          </div>

          {/* Active Providers Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Google Gemini Card */}
            <div className="p-4 rounded-xl border border-[#DCE5EB] bg-slate-50/50 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-xs text-[#102C46] flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  Google Gemini (Cloud)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold">
                  API Connected
                </span>
              </div>
              <p className="text-[11px] text-[#52616C]">
                Official Google Gen AI SDK. Configured model: <code className="text-[#009F98]">gemini-3.5-flash</code>.
              </p>
              <div className="text-[10px] text-slate-400">
                Context window: 1M tokens. Zero raw row cell data sent.
              </div>
            </div>

            {/* Local Ollama Card */}
            <div className="p-4 rounded-xl border border-[#DCE5EB] bg-slate-50/50 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-xs text-[#102C46] flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5 text-[#009F98]" />
                  Ollama (Local AI)
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                  ollamaOnline ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-200 text-slate-600'
                }`}>
                  {ollamaOnline ? 'Running' : 'Endpoint Standby'}
                </span>
              </div>
              <p className="text-[11px] text-[#52616C]">
                Endpoint: <code className="text-slate-700">http://localhost:11434</code>. Recommended model: <code className="text-[#009F98]">gemma3:4b</code>.
              </p>
              <div className="text-[10px] text-slate-400">
                {ollamaModels.length > 0
                  ? `Installed models: ${ollamaModels.join(', ')}`
                  : 'Start via "ollama serve" and pull with "ollama pull gemma3:4b"'}
              </div>
            </div>
          </div>

          {/* Routing Configuration */}
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-bold uppercase text-[#102C46]">Provider Routing Mode</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                { id: 'HYBRID', title: 'Hybrid (Smart)', desc: 'Local for simple/sensitive, Gemini for deep reasoning' },
                { id: 'GEMINI_ONLY', title: 'Gemini Cloud Only', desc: 'All requests processed by Google Gemini' },
                { id: 'LOCAL_ONLY', title: 'Local Ollama Only', desc: '100% sovereign air-gapped processing' },
                { id: 'DETERMINISTIC_ONLY', title: 'Deterministic', desc: 'Zero-LLM verified heuristic rules' },
              ].map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setRoutingMode(mode.id)}
                  className={`p-3 rounded-xl border text-left transition ${
                    routingMode === mode.id
                      ? 'border-[#009F98] bg-[#EAF5F8]/40 shadow-xs'
                      : 'border-[#DCE5EB] hover:bg-slate-50'
                  }`}
                >
                  <span className="font-bold text-xs text-[#102C46] block">{mode.title}</span>
                  <span className="text-[10px] text-[#52616C] leading-snug block mt-0.5">{mode.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Privacy & Governance Boundary */}
          <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200/60 text-xs text-amber-900 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Privacy & Data Egress Safeguards
            </div>
            <p className="text-[11px] leading-relaxed">
              Datasets classified as <strong>CONFIDENTIAL</strong> or <strong>RESTRICTED</strong> are strictly barred from cloud AI egress, automatically executing via local Ollama or deterministic fallback regardless of the selected global mode.
            </p>
          </div>
        </div>
      )}

      {/* Tab 5: Sharing Governance */}
      {activeTab === 'sharing' && (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-6 shadow-subtle space-y-3 max-w-3xl">
          <h3 className="text-sm font-bold text-[#102C46]">Sharing Governance</h3>
          <p className="text-xs text-[#52616C]">
            All shared report links are encrypted, read-only, and automatically expire after their scheduled TTL.
          </p>
        </div>
      )}
    </div>
  );
};
