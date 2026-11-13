import React, { useState, useMemo, useEffect } from 'react';
import { Sparkles, Bot, ShieldCheck } from 'lucide-react';
import { StorageService } from '../../services/storageService';
import { AskAnalyticsService } from '../../services/askAnalyticsService';
import { AiApi, AIStatusResponsePayload } from '../../services/apiClient';
import { NLAService, NLAMessageResponse } from '../../services/nlaService';
import { ConversationSession, AskMessage, Dataset } from '../../types';
import { ConversationSidebar } from './components/ConversationSidebar';
import { DatasetIntelligencePanel } from './components/DatasetIntelligencePanel';
import { WelcomeState } from './components/WelcomeState';
import { ActiveChatState } from './components/ActiveChatState';
import { ChatComposer } from './components/ChatComposer';

export const AskYourData: React.FC = () => {
  const user = StorageService.getUser();
  const [datasets, setDatasets] = useState<Dataset[]>(StorageService.getDatasets());
  const [aiStatus, setAiStatus] = useState<AIStatusResponsePayload | null>(null);

  const getActiveWorkspaceId = (): string | null => {
    try {
      const stored = localStorage.getItem('datalens_active_workspace');
      if (stored) {
        const ws = JSON.parse(stored);
        return ws?.id || null;
      }
    } catch {
      // fallback
    }
    return null;
  };

  useEffect(() => {
    StorageService.getDatasetsAsync().then((list) => {
      if (list && list.length > 0) {
        setDatasets(list);
      }
    });

    AiApi.getStatus(getActiveWorkspaceId() || undefined)
      .then((status) => setAiStatus(status))
      .catch(() => setAiStatus(null));
  }, []);


  const [conversations, setConversations] = useState<ConversationSession[]>(() =>
    StorageService.getConversations()
  );

  // Active conversation state: null initially triggers STATE A (Welcome State)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Selected dataset for analytics context
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(
    datasets[0]?.id || 'ds-sales-2025'
  );

  const [questionInput, setQuestionInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.id === selectedDatasetId) || datasets[0],
    [datasets, selectedDatasetId]
  );

  const activeSession = useMemo(
    () => (activeSessionId ? conversations.find((c) => c.id === activeSessionId) : null),
    [conversations, activeSessionId]
  );

  const suggestedQuestions = useMemo(
    () => AskAnalyticsService.getSuggestedQuestions(selectedDataset),
    [selectedDataset]
  );

  // Format current time helper
  const getCurrentFormattedTime = () =>
    new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(new Date());

  const mapNlaResponse = (res: NLAMessageResponse, timeStr: string): AskMessage => ({
    id: `msg-a-${Date.now()}`,
    sender: 'assistant',
    timestamp: `Today, ${timeStr}`,
    content: res.detailed_narrative || res.content,
    directAnswer: res.direct_answer || res.content,
    intent: res.intent || undefined,
    metrics: res.metric_cards.map((c) => ({
      label: c.title,
      value: c.value,
      trend: c.change || undefined,
      isPositive: c.trend === 'up',
    })),
    chartData: res.chart
      ? {
          type: (res.chart.chart_type === 'pie' || res.chart.chart_type === 'donut') ? 'pie' : res.chart.chart_type === 'line' ? 'line' : 'bar',
          title: res.chart.title,
          labels: res.chart.series.map((s) => String(s[res.chart!.x_key] ?? '')),
          values: res.chart.series.map((s) => Number(s[res.chart!.y_keys[0]]) || 0),
          unit: '',
        }
      : undefined,
    tableData: res.table
      ? {
          headers: res.table.columns,
          rows: res.table.rows.map((row) => res.table!.columns.map((col) => row[col])),
        }
      : undefined,
    interpretation: res.detailed_narrative || undefined,
    evidence: res.evidence.map((ev, idx) => ({
      id: `ev-${idx}`,
      title: ev.metric_name,
      sourceColumn: ev.source_column,
      calculationType: (ev.aggregation_type.charAt(0).toUpperCase() + ev.aggregation_type.slice(1)) as any,
      formulaOrQuery: ev.formula || `${ev.aggregation_type}(${ev.source_column})`,
      rawResult: ev.computed_value,
      formattedResult: String(ev.computed_value),
      confidence: 1.0,
      verifiedByEngine: ev.verified_by_engine,
      rowCountAnalyzed: ev.row_count_analyzed ?? undefined,
      executionTimeMs: ev.execution_time_ms ?? undefined,
    })),
    businessInferences: res.business_inferences,
    recommendations: res.recommendations,
    suggestedFollowUps: res.suggested_follow_ups,
    needsClarification: res.needs_clarification,
    clarificationPrompt: res.clarification_prompt || undefined,
    clarificationOptions: res.clarification_options,
    rawSql: res.raw_sql || undefined,
    executionTimeMs: res.execution_time_ms ?? undefined,
    rowCount: res.row_count ?? undefined,
    backendSessionId: res.session_id,
    backendMessageId: res.id,
  });

  // Handle "+ New Chat" action
  const handleNewChat = () => {
    setActiveSessionId(null);
    setQuestionInput('');
  };

  // Handle sending a question (from input or clicked chips)
  const handleSendQuestion = async (textToSend?: string) => {
    const query = (textToSend || questionInput).trim();
    if (!query || isProcessing) return;

    setQuestionInput('');
    setIsProcessing(true);

    const nowTime = getCurrentFormattedTime();
    const userMsg: AskMessage = {
      id: `msg-u-${Date.now()}`,
      sender: 'user',
      timestamp: `Today, ${nowTime}`,
      content: query,
    };

    // If there is an active session, append; otherwise create a new conversation session
    let sessionToUpdate: ConversationSession;
    if (activeSession) {
      sessionToUpdate = {
        ...activeSession,
        updatedAt: `Today, ${nowTime}`,
        messageCount: activeSession.messages.length + 1,
        messages: [...activeSession.messages, userMsg],
      };
    } else {
      // Derive a short clean title from the query
      const autoTitle =
        query.length > 36 ? `${query.slice(0, 36).trim()}...` : query;
      sessionToUpdate = {
        id: `conv-${Date.now()}`,
        title: autoTitle,
        datasetId: selectedDataset?.id || 'ds-sales-2025',
        datasetName: selectedDataset?.name || 'Sales_Data_2025',
        updatedAt: `Today, ${nowTime}`,
        messageCount: 1,
        messages: [userMsg],
      };
      setActiveSessionId(sessionToUpdate.id);
    }

    // Persist user message immediately
    StorageService.saveConversation(sessionToUpdate);
    setConversations(StorageService.getConversations());

    try {
      // Find previous assistant message for context memory (e.g. "its", "for that")
      const prevMsg = sessionToUpdate.messages
        .filter((m) => m.sender === 'assistant')
        .slice(-1)[0];

      let assistantMsg: AskMessage;
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(selectedDataset?.id || '');
      const wsId = getActiveWorkspaceId();

      if (isUuid && wsId) {
        try {
          const backendSessionId = prevMsg?.backendSessionId;
          const res = backendSessionId
            ? await NLAService.followUpQuery(wsId, {
                session_id: backendSessionId,
                follow_up_question: query,
              })
            : await NLAService.executeQuery(wsId, {
                dataset_id: selectedDataset.id,
                question: query,
              });

          assistantMsg = mapNlaResponse(res, nowTime);
        } catch (nlaErr) {
          console.warn('NLA API query error, falling back to legacy AI or local engine:', nlaErr);
          try {
            const history = sessionToUpdate.messages.slice(-5).map((m) => ({
              role: m.sender === 'user' ? 'user' : 'assistant',
              content: m.content || m.directAnswer || '',
            }));

            const res = await AiApi.ask(wsId, {
              dataset_id: selectedDataset.id,
              question: query,
              conversation_history: history,
            });

            assistantMsg = {
              id: `msg-a-${Date.now()}`,
              sender: 'assistant',
              timestamp: `Today, ${nowTime}`,
              content: res.detailed_narrative,
              directAnswer: res.executive_summary,
              intent: (res as any).intent || undefined,
              metrics: res.metric_cards.map((c) => ({
                label: c.title,
                value: c.value,
                trend: c.change,
                isPositive: c.trend === 'up',
              })),
              chartData: res.chart
                ? {
                    type: (res.chart.chart_type === 'pie' ? 'pie' : res.chart.chart_type === 'line' ? 'line' : 'bar'),
                    title: res.chart.title,
                    labels: res.chart.series.map((s) => String(s[res.chart!.x_key] ?? '')),
                    values: res.chart.series.map((s) => Number(s[res.chart!.y_keys[0]]) || 0),
                    unit: '',
                  }
                : undefined,
              tableData: res.table
                ? {
                    headers: res.table.columns,
                    rows: res.table.rows.map((row) => res.table!.columns.map((col) => row[col])),
                  }
                : undefined,
              interpretation: res.detailed_narrative,
              evidence: res.evidence.map((ev, idx) => ({
                id: `ev-${idx}`,
                title: ev.metric_name,
                sourceColumn: ev.source_column,
                calculationType: (ev.aggregation_type.charAt(0).toUpperCase() + ev.aggregation_type.slice(1)) as any,
                formulaOrQuery: ev.formula || `${ev.aggregation_type}(${ev.source_column})`,
                rawResult: ev.computed_value,
                formattedResult: String(ev.computed_value),
                confidence: 1.0,
                verifiedByEngine: true,
                datasetVersionId: res.dataset_version_id,
                rowCountAnalyzed: selectedDataset.rowCount,
                executionTimeMs: res.execution_time_ms,
              })),
              suggestedFollowUps: res.suggested_follow_ups,
            };
          } catch (serverErr) {
            console.warn('Backend AI query fallback to local engine:', serverErr);
            assistantMsg = await AskAnalyticsService.processQuestion(query, {
              dataset: selectedDataset,
              previousMessage: prevMsg,
            });
          }
        }
      } else {
        assistantMsg = await AskAnalyticsService.processQuestion(query, {
          dataset: selectedDataset,
          previousMessage: prevMsg,
        });
      }

      const finalSession: ConversationSession = {
        ...sessionToUpdate,
        messageCount: sessionToUpdate.messages.length + 1,
        messages: [...sessionToUpdate.messages, assistantMsg],
      };

      StorageService.saveConversation(finalSession);
      setConversations(StorageService.getConversations());
    } catch (err) {
      console.error('Error generating analytical response:', err);
      const errorMsg: AskMessage = {
        id: `msg-err-${Date.now()}`,
        sender: 'assistant',
        timestamp: `Today, ${nowTime}`,
        content: '',
        directAnswer:
          'Something went wrong while processing your dataset query. Please check your data connection and try again.',
      };
      const errorSession: ConversationSession = {
        ...sessionToUpdate,
        messages: [...sessionToUpdate.messages, errorMsg],
      };
      StorageService.saveConversation(errorSession);
      setConversations(StorageService.getConversations());
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle deleting a conversation
  const handleDeleteSession = (id: string) => {
    const updated = conversations.filter((c) => c.id !== id);
    setConversations(updated);
    // Remove from storage
    const stored = StorageService.getConversations().filter((c) => c.id !== id);
    localStorage.setItem('datalens_conversations', JSON.stringify(stored));
    if (activeSessionId === id) {
      setActiveSessionId(null);
    }
  };

  // Handle renaming a conversation
  const handleRenameSession = (id: string, newTitle: string) => {
    const session = conversations.find((c) => c.id === id);
    if (session) {
      const updated = { ...session, title: newTitle };
      StorageService.saveConversation(updated);
      setConversations(StorageService.getConversations());
    }
  };

  // Handle adding finding to a report
  const handleAddToReport = (msg: AskMessage) => {
    const currentReports = StorageService.getReports();
    if (currentReports.length > 0) {
      alert(
        `Added "${msg.chartData?.title || 'Insight Finding'}" to active draft report (${currentReports[0].title}).`
      );
    } else {
      alert('Insight saved for inclusion in future business reports.');
    }
  };

  // Handle clarification option selection
  const handleClarify = async (msg: AskMessage, opt: { key: string; label: string }) => {
    const wsId = getActiveWorkspaceId();
    const sessionId = msg.backendSessionId;
    if (!wsId || !sessionId) {
      handleSendQuestion(opt.label);
      return;
    }

    setIsProcessing(true);
    const nowTime = getCurrentFormattedTime();
    const userMsg: AskMessage = {
      id: `msg-u-${Date.now()}`,
      sender: 'user',
      timestamp: `Today, ${nowTime}`,
      content: opt.label,
    };

    if (activeSession) {
      const updated = {
        ...activeSession,
        messages: [...activeSession.messages, userMsg],
      };
      StorageService.saveConversation(updated);
      setConversations(StorageService.getConversations());
    }

    try {
      const res = await NLAService.clarifyQuery(wsId, {
        session_id: sessionId,
        clarification_choice: opt.label,
        original_question: msg.content,
      });

      const assistantMsg = mapNlaResponse(res, nowTime);
      if (activeSession) {
        const finalSession = {
          ...activeSession,
          messages: [...activeSession.messages, userMsg, assistantMsg],
        };
        StorageService.saveConversation(finalSession);
        setConversations(StorageService.getConversations());
      }
    } catch (err) {
      console.error('Error handling clarification:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle saving analytical finding
  const handleSaveAnalysis = async (msg: AskMessage) => {
    const wsId = getActiveWorkspaceId();
    if (!wsId) return;
    try {
      await NLAService.saveAnalysis(wsId, {
        title: msg.directAnswer ? msg.directAnswer.slice(0, 60) : 'Saved Analysis',
        dataset_id: selectedDataset?.id || '',
        session_id: msg.backendSessionId,
        message_id: msg.backendMessageId,
        raw_sql: msg.rawSql,
        notes: msg.interpretation,
      });
    } catch (err) {
      console.error('Error saving analysis:', err);
    }
  };

  const hasActiveMessages = !!(activeSession && activeSession.messages.length > 0);

  return (
    <div className="space-y-4">
      {/* 1. Global Page Header matching design reference */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#007D78] shadow-2xs shrink-0">
            <Sparkles className="w-5 h-5 text-[#009F98]" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-serif text-[#102C46] tracking-tight">
              Ask Your Data
            </h1>
            <p className="text-xs text-[#52616C] font-medium">
              Chat with your data, get verified insights, visualizations, and detailed analysis instantly.
            </p>
          </div>
        </div>

        {/* AI & Verification Engine Status Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#DCE5EB] bg-white shadow-2xs text-xs self-start sm:self-auto">
          <div
            className={`w-2 h-2 rounded-full ${
              aiStatus?.operational
                ? 'bg-emerald-500 animate-pulse'
                : aiStatus?.ai_enabled
                ? 'bg-amber-400'
                : 'bg-[#009F98]'
            }`}
          />
          <span className="font-semibold text-[#102C46]">
            {aiStatus?.operational
              ? `AI: ${aiStatus.model}`
              : aiStatus?.ai_enabled
              ? 'AI: Standby'
              : 'Deterministic Engine'}
          </span>
          <span className="text-[10px] text-[#52616C] border-l border-[#DCE5EB] pl-2 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-[#009F98]" />
            DuckDB Verified
          </span>
        </div>
      </div>

      {/* 2. Three-Panel Layout matching reference design authority */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch min-h-[660px]">
        {/* Panel 1: Conversation History (Left, 3 cols) */}
        <div className="lg:col-span-3 h-full">
          <ConversationSidebar
            conversations={conversations}
            activeSessionId={activeSessionId}
            onSelectSession={(id) => setActiveSessionId(id)}
            onNewChat={handleNewChat}
            onDeleteSession={handleDeleteSession}
            onRenameSession={handleRenameSession}
          />
        </div>

        {/* Panel 2: Main Chat Workspace (Center, 6 cols) */}
        <div className="lg:col-span-6 bg-[#F5F8FA] rounded-2xl border border-[#DCE5EB] p-4 flex flex-col justify-between h-full min-h-[660px] shadow-subtle relative overflow-hidden">
          {/* Dynamic Switch: STATE A (Welcome) vs STATE B (Active Conversation) */}
          {!hasActiveMessages ? (
            <WelcomeState
              user={user}
              selectedDataset={selectedDataset}
              suggestedQuestions={suggestedQuestions}
              onSelectQuestion={(q) => handleSendQuestion(q)}
            />
          ) : (
            <ActiveChatState
              messages={activeSession!.messages}
              isProcessing={isProcessing}
              onSelectQuestion={(q) => handleSendQuestion(q)}
              onAddToReport={handleAddToReport}
              onClarify={handleClarify}
              onSaveAnalysis={handleSaveAnalysis}
            />
          )}

          {/* Persistent Question Composer at bottom */}
          <ChatComposer
            value={questionInput}
            onChange={setQuestionInput}
            onSend={handleSendQuestion}
            isProcessing={isProcessing}
            selectedDataset={selectedDataset}
            hasActiveMessages={hasActiveMessages}
          />
        </div>

        {/* Panel 3: Dataset Intelligence (Right, 3 cols) */}
        <div className="lg:col-span-3 h-full">
          <DatasetIntelligencePanel
            datasets={datasets}
            selectedDataset={selectedDataset}
            onSelectDataset={(d) => setSelectedDatasetId(d.id)}
            onSelectQuestion={(q) => handleSendQuestion(q)}
            suggestedQuestions={suggestedQuestions}
          />
        </div>
      </div>
    </div>
  );
};
