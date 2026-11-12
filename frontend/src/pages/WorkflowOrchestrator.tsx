import React, { useState, useEffect, useRef } from 'react';
import {
  PlayCircle,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Terminal,
  FileText,
  Download,
  Copy,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Layers,
  ArrowRight,
  ShieldAlert,
  FastForward,
  Check,
  Search,
  BookOpen
} from 'lucide-react';
import {
  Document,
  ResearchProjectItem,
  WorkflowStatusResponse,
  WorkflowStageInfo,
  WorkflowHistoryItem
} from '../types';
import { api } from '../services/api';

interface WorkflowOrchestratorProps {
  documents: Document[];
}

export const WorkflowOrchestrator: React.FC<WorkflowOrchestratorProps> = ({ documents }) => {
  // Inputs
  const [topic, setTopic] = useState('Multi-Agent Reinforcement Learning and Graph Attention Routing');
  const [projectId, setProjectId] = useState<string>('');
  const [projectTitle, setProjectTitle] = useState('');
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [skippedStages, setSkippedStages] = useState<string[]>([]);
  const [forceRestart, setForceRestart] = useState(false);

  // Workflow State
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowStatusResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [executingStageId, setExecutingStageId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [history, setHistory] = useState<WorkflowHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Expanded Stage Cards
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({});
  const [copiedReport, setCopiedReport] = useState(false);

  // Console Logs auto-scroll
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const [autoScrollLogs, setAutoScrollLogs] = useState(true);

  // Polling ref
  const pollingRef = useRef<any>(null);

  // Initial load
  useEffect(() => {
    loadProjects();
    loadHistory();
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const loadProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0 && !projectId) {
        setProjectId(projs[0].id);
      }
    } catch (e) {
      console.warn('Could not load projects', e);
    }
  };

  const loadHistory = async () => {
    try {
      const hist = await api.getWorkflowHistory();
      setHistory(hist);
    } catch (e) {
      console.warn('Could not load history', e);
    }
  };

  // Start polling when an active workflow is running
  useEffect(() => {
    if (activeWorkflow && (activeWorkflow.status === 'running' || activeWorkflow.status === 'pending')) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(pollWorkflowStatus, 2000);
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  }, [activeWorkflow?.status, activeWorkflow?.workflow_id]);

  // Auto-scroll logs
  useEffect(() => {
    if (autoScrollLogs && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeWorkflow?.logs, autoScrollLogs]);

  const pollWorkflowStatus = async () => {
    if (!activeWorkflow?.workflow_id) return;
    try {
      const updated = await api.getWorkflowStatus(activeWorkflow.workflow_id);
      setActiveWorkflow(updated);
      if (updated.status === 'completed' || updated.status === 'failed') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        loadHistory();
      }
    } catch (err: any) {
      console.error('Error polling workflow status', err);
    }
  };

  // Launch Full Workflow
  const handleStartWorkflow = async () => {
    setIsStarting(true);
    setErrorMsg(null);
    try {
      const response = await api.startWorkflow({
        project_id: projectId || undefined,
        project_title: projectTitle || (!projectId ? `Project: ${topic.slice(0, 30)}` : undefined),
        topic: topic.trim() || undefined,
        paper_ids: selectedPaperIds.length > 0 ? selectedPaperIds : undefined,
        skip_stages: skippedStages.length > 0 ? skippedStages : undefined,
        force_restart: forceRestart,
      });
      setActiveWorkflow(response);
      loadHistory();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start multi-agent workflow');
    } finally {
      setIsStarting(false);
    }
  };

  // Resume Workflow
  const handleResumeWorkflow = async () => {
    if (!activeWorkflow?.workflow_id) return;
    setIsResuming(true);
    setErrorMsg(null);
    try {
      const response = await api.resumeWorkflow(activeWorkflow.workflow_id);
      setActiveWorkflow(response);
      loadHistory();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to resume workflow');
    } finally {
      setIsResuming(false);
    }
  };

  // Run Single Stage
  const handleRunSingleStage = async (stageId: string) => {
    if (!activeWorkflow?.project_id && !projectId) {
      setErrorMsg('A project must be selected to run an individual stage.');
      return;
    }
    const targetProjId = activeWorkflow?.project_id || projectId;
    setExecutingStageId(stageId);
    setErrorMsg(null);
    try {
      await api.runWorkflowStage({
        project_id: targetProjId,
        stage_id: stageId,
        paper_ids: selectedPaperIds.length > 0 ? selectedPaperIds : undefined,
        topic: topic.trim() || undefined,
        force: true,
      });
      // Refresh current workflow status if loaded
      if (activeWorkflow?.workflow_id) {
        await pollWorkflowStatus();
      }
      loadHistory();
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to run stage ${stageId}`);
    } finally {
      setExecutingStageId(null);
    }
  };

  // Load a historic workflow
  const handleLoadHistoricWorkflow = async (workflowId: string) => {
    setErrorMsg(null);
    try {
      const wf = await api.getWorkflowStatus(workflowId);
      setActiveWorkflow(wf);
      setShowHistory(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load workflow run');
    }
  };

  const togglePaperSelection = (docId: string) => {
    setSelectedPaperIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const toggleStageExpand = (stageId: string) => {
    setExpandedStages((prev) => ({
      ...prev,
      [stageId]: !prev[stageId],
    }));
  };

  const toggleSkipStage = (stageId: string) => {
    setSkippedStages((prev) =>
      prev.includes(stageId) ? prev.filter((id) => id !== stageId) : [...prev, stageId]
    );
  };

  const handleCopyReport = () => {
    if (activeWorkflow?.final_report_markdown) {
      navigator.clipboard.writeText(activeWorkflow.final_report_markdown);
      setCopiedReport(true);
      setTimeout(() => setCopiedReport(false), 2500);
    }
  };

  const handleDownloadReport = () => {
    if (!activeWorkflow?.final_report_markdown) return;
    const blob = new Blob([activeWorkflow.final_report_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `literature_intelligence_dossier_${activeWorkflow.workflow_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isWorkflowActive = activeWorkflow?.status === 'running' || activeWorkflow?.status === 'pending';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              8-Agent Autonomous Pipeline
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              Sequential 8 GB RAM Protection
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 mt-1">Multi-Agent Workflow Orchestrator</h1>
          <p className="text-sm text-slate-400">
            Execute the complete literature intelligence workflow with one button: Discovery, Document Understanding, Vector Retrieval, 14-Dimension Analysis, Cross-Paper Matrix, Knowledge Graph, Gap Discovery, Evidence Verification, and Publication-Grade Dossier.
          </p>
        </div>

        {/* History & Status button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition-colors"
          >
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            Execution Runs ({history.length})
          </button>
          {activeWorkflow?.workflow_id && (
            <button
              onClick={pollWorkflowStatus}
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors"
              title="Refresh status"
            >
              <RefreshCw className={`w-4 h-4 ${isWorkflowActive ? 'animate-spin text-emerald-400' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* History Drawer Modal */}
      {showHistory && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Prior Orchestrator Runs
            </h3>
            <button
              onClick={() => setShowHistory(false)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Close
            </button>
          </div>
          {history.length === 0 ? (
            <p className="text-xs text-slate-400">No previous workflows found.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-60 overflow-y-auto">
              {history.map((h) => (
                <div
                  key={h.workflow_id}
                  onClick={() => handleLoadHistoricWorkflow(h.workflow_id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    activeWorkflow?.workflow_id === h.workflow_id
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="truncate max-w-[160px]">{h.topic || 'Untitled Workflow'}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                        h.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : h.status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}
                    >
                      {h.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                    <span>
                      Stages: {h.completed_stages} / {h.total_stages} ({h.progress_percent}%)
                    </span>
                    <span>{new Date(h.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Workflow Configuration & One-Button Execution Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Workflow Execution Console</h2>
              <p className="text-xs text-slate-400">
                Configure topic or select target PDFs, then launch the end-to-end pipeline.
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors"
          >
            {showAdvanced ? 'Hide Stage Toggles' : 'Configure Stages'}
            {showAdvanced ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Input Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Research Topic */}
          <div className="lg:col-span-2 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5 text-emerald-400" />
              Research Topic or Scientific Question
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Self-supervised learning for biomedical image segmentation"
              disabled={isWorkflowActive}
              className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all disabled:opacity-50"
            />
          </div>

          {/* Project Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
              Target Research Project
            </label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              disabled={isWorkflowActive}
              className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all disabled:opacity-50"
            >
              <option value="">-- Create Auto Project from Topic --</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} ({p.paper_count || 0} papers)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Paper Multi-Selection from Ingested Documents */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300">
              Target Documents ({selectedPaperIds.length} of {documents.length} selected)
            </span>
            <div className="space-x-2">
              <button
                type="button"
                onClick={() => setSelectedPaperIds(documents.map((d) => d.id))}
                disabled={isWorkflowActive}
                className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
              >
                Select All
              </button>
              <span className="text-slate-600">|</span>
              <button
                type="button"
                onClick={() => setSelectedPaperIds([])}
                disabled={isWorkflowActive}
                className="text-slate-400 hover:text-slate-300 disabled:opacity-50"
              >
                Clear Selection (Use Topic Discovery)
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 max-h-28 overflow-y-auto p-2 bg-slate-950/50 border border-slate-800 rounded-xl">
            {documents.length === 0 ? (
              <span className="text-xs text-slate-500 italic p-1">
                No local documents uploaded yet. Workflow will discover open-access academic papers using arXiv, OpenAlex, and Semantic Scholar.
              </span>
            ) : (
              documents.map((doc) => {
                const isSelected = selectedPaperIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => togglePaperSelection(doc.id)}
                    disabled={isWorkflowActive}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isSelected
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-slate-900 border border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <FileText className={`w-3.5 h-3.5 ${isSelected ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span className="truncate max-w-[200px]">{doc.title || doc.filename}</span>
                    {isSelected && <Check className="w-3 h-3 text-emerald-400" />}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Advanced Stage Skipping Toggle */}
        {showAdvanced && (
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Stage Configuration (Select stages to skip)
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 text-xs">
              {[
                { id: 'discovery', label: '1. Discovery Agent' },
                { id: 'document_understanding', label: '2. PDF Understanding' },
                { id: 'semantic_retrieval', label: '3. Vector Retrieval' },
                { id: 'research_analysis', label: '4. Research Analysis' },
                { id: 'cross_paper_comparison', label: '5. Cross Comparison' },
                { id: 'knowledge_graph', label: '6. Knowledge Graph' },
                { id: 'research_gap_discovery', label: '7. Gap Discovery' },
                { id: 'evidence_verification', label: '8. Evidence Verification' },
                { id: 'final_report', label: '9. Final Report' },
              ].map((st) => {
                const isSkipped = skippedStages.includes(st.id);
                return (
                  <label
                    key={st.id}
                    className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:bg-slate-900"
                  >
                    <input
                      type="checkbox"
                      checked={isSkipped}
                      onChange={() => toggleSkipStage(st.id)}
                      disabled={isWorkflowActive}
                      className="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-0"
                    />
                    <span className={isSkipped ? 'line-through text-slate-500' : 'text-slate-300'}>
                      {st.label}
                    </span>
                  </label>
                );
              })}
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800 text-xs">
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceRestart}
                  onChange={(e) => setForceRestart(e.target.checked)}
                  disabled={isWorkflowActive}
                  className="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0"
                />
                Force re-computation of already cached stage artifacts
              </label>
            </div>
          </div>
        )}

        {/* Action Buttons Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          {/* ONE-BUTTON PRIMARY EXECUTION */}
          <button
            onClick={handleStartWorkflow}
            disabled={isStarting || isWorkflowActive}
            className={`flex-1 min-w-[280px] flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl font-bold text-sm tracking-wide shadow-lg transition-all ${
              isWorkflowActive
                ? 'bg-emerald-600/50 text-emerald-200 cursor-wait'
                : 'bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 shadow-emerald-500/20 hover:shadow-emerald-500/30 active:scale-[0.99]'
            }`}
          >
            {isStarting || isWorkflowActive ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Autonomous Workflow In Progress...</span>
              </>
            ) : (
              <>
                <PlayCircle className="w-5 h-5" />
                <span>Run Complete Literature Intelligence Workflow</span>
              </>
            )}
          </button>

          {/* RESUME BUTTON (IF FAILED) */}
          {activeWorkflow?.status === 'failed' && (
            <button
              onClick={handleResumeWorkflow}
              disabled={isResuming || isWorkflowActive}
              className="flex items-center gap-2 px-5 py-3.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-xl font-semibold text-sm transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${isResuming ? 'animate-spin' : ''}`} />
              <span>Resume Failed Workflow</span>
            </button>
          )}
        </div>

        {/* Error message banner */}
        {errorMsg && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-400 text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Real Honest Progress Bar & Status Metric Card */}
      {activeWorkflow && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${
                    activeWorkflow.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : activeWorkflow.status === 'failed'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-teal-500/20 text-teal-300 border border-teal-500/30 animate-pulse'
                  }`}
                >
                  {activeWorkflow.status}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  ID: {activeWorkflow.workflow_id}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-200">
                {activeWorkflow.current_stage
                  ? `Active Stage: ${activeWorkflow.current_stage}`
                  : activeWorkflow.status === 'completed'
                  ? 'Complete Research Dossier Generated & Verified'
                  : 'Workflow Pending'}
              </p>
            </div>

            {/* Stage Counter & Honest Percentage */}
            <div className="text-right">
              <span className="text-2xl font-extrabold text-emerald-400 font-mono">
                {activeWorkflow.progress_percent.toFixed(1)}%
              </span>
              <span className="block text-xs text-slate-400">
                Honest Stage Progress ({activeWorkflow.completed_stages} of {activeWorkflow.total_stages} stages)
              </span>
            </div>
          </div>

          {/* Honest Progress Bar */}
          <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
            <div
              className={`h-full transition-all duration-700 rounded-full ${
                activeWorkflow.status === 'completed'
                  ? 'bg-emerald-400'
                  : activeWorkflow.status === 'failed'
                  ? 'bg-red-400'
                  : 'bg-gradient-to-r from-emerald-500 to-teal-400'
              }`}
              style={{ width: `${Math.min(activeWorkflow.progress_percent, 100)}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
              Real stage calculation: ((Completed + Skipped) / Total) × 100%
            </span>
            <span>Last Updated: {new Date(activeWorkflow.updated_at).toLocaleTimeString()}</span>
          </div>
        </div>
      )}

      {/* 9-Stage Visual Sequential Timeline */}
      {activeWorkflow && activeWorkflow.stages && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Multi-Agent Execution Pipeline (9 Sequential Stages)
            </h3>
            <span className="text-xs text-slate-400">
              Click any stage to view inputs, outputs, or re-run independently
            </span>
          </div>

          <div className="space-y-2.5">
            {activeWorkflow.stages.map((stage: WorkflowStageInfo, index: number) => {
              const isExpanded = Boolean(expandedStages[stage.stage_id]);
              const isExecutingThis = executingStageId === stage.stage_id;

              return (
                <div
                  key={stage.stage_id}
                  className={`border rounded-xl transition-all overflow-hidden ${
                    stage.status === 'running'
                      ? 'bg-slate-900/90 border-teal-500/60 shadow-lg shadow-teal-500/5'
                      : stage.status === 'completed'
                      ? 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                      : stage.status === 'failed'
                      ? 'bg-red-950/20 border-red-500/40'
                      : stage.status === 'skipped'
                      ? 'bg-slate-950/40 border-slate-800/60 opacity-60'
                      : 'bg-slate-950/60 border-slate-800/80'
                  }`}
                >
                  {/* Stage Summary Bar */}
                  <div
                    onClick={() => toggleStageExpand(stage.stage_id)}
                    className="p-4 flex items-center justify-between cursor-pointer select-none gap-3"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {/* Status Icon */}
                      <div className="shrink-0">
                        {stage.status === 'completed' && (
                          <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                            <CheckCircle2 className="w-4 h-4" />
                          </div>
                        )}
                        {stage.status === 'running' && (
                          <div className="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300">
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          </div>
                        )}
                        {stage.status === 'failed' && (
                          <div className="w-7 h-7 rounded-lg bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400">
                            <AlertTriangle className="w-4 h-4" />
                          </div>
                        )}
                        {stage.status === 'skipped' && (
                          <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
                            <FastForward className="w-3.5 h-3.5" />
                          </div>
                        )}
                        {stage.status === 'pending' && (
                          <div className="w-7 h-7 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 font-mono text-xs font-bold">
                            {index + 1}
                          </div>
                        )}
                      </div>

                      {/* Stage Name & Details */}
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-200">
                            {index + 1}. {stage.stage_name}
                          </span>
                          <span className="text-xs text-slate-400 font-mono bg-slate-800/60 px-1.5 py-0.5 rounded">
                            {stage.agent_name}
                          </span>
                          {stage.retry_count > 0 && (
                            <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.2 rounded font-semibold">
                              Retried {stage.retry_count}x
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 truncate mt-0.5">
                          {stage.message || 'Waiting to execute'}
                        </p>
                      </div>
                    </div>

                    {/* Right Meta & Action */}
                    <div className="flex items-center gap-3 shrink-0">
                      {stage.duration_ms > 0 && (
                        <span className="text-xs text-slate-400 font-mono">
                          {stage.duration_ms < 1000
                            ? `${stage.duration_ms} ms`
                            : `${(stage.duration_ms / 1000).toFixed(2)} s`}
                        </span>
                      )}

                      {/* Run Individual Stage Button */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRunSingleStage(stage.stage_id);
                        }}
                        disabled={isExecutingThis || isWorkflowActive}
                        className="px-2.5 py-1 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-md transition-colors disabled:opacity-50 flex items-center gap-1"
                        title="Execute this single agent stage"
                      >
                        {isExecutingThis ? (
                          <RefreshCw className="w-3 h-3 animate-spin text-emerald-400" />
                        ) : (
                          <PlayCircle className="w-3 h-3 text-emerald-400" />
                        )}
                        <span>Run Stage</span>
                      </button>

                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Collapsible Details Drawer */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-1 border-t border-slate-800/80 bg-slate-950/50 space-y-3 text-xs">
                      {stage.error_message && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
                          <span className="font-semibold block mb-1">Error Diagnostics:</span>
                          <p className="font-mono">{stage.error_message}</p>
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
                          <span className="font-semibold text-slate-300 block">Input Summary:</span>
                          <p className="text-slate-400">
                            {stage.input_summary || 'Default workflow inputs and preceding agent outputs.'}
                          </p>
                        </div>
                        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
                          <span className="font-semibold text-slate-300 block">Output Summary:</span>
                          <p className="text-slate-400">
                            {stage.output_summary || 'Stage has not produced outputs yet.'}
                          </p>
                        </div>
                      </div>

                      {stage.completed_at && (
                        <div className="text-[11px] text-slate-500">
                          Completed at: {new Date(stage.completed_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Terminal / Live Logs Viewer */}
      {activeWorkflow && activeWorkflow.logs && activeWorkflow.logs.length > 0 && (
        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Orchestrator Execution Logs ({activeWorkflow.logs.length} entries)</span>
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScrollLogs}
                onChange={(e) => setAutoScrollLogs(e.target.checked)}
                className="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0"
              />
              Auto-scroll
            </label>
          </div>

          <div className="font-mono text-xs text-slate-300 bg-slate-900/90 p-3 rounded-xl max-h-56 overflow-y-auto space-y-1 border border-slate-800/80">
            {activeWorkflow.logs.map((log, idx) => (
              <div key={idx} className="flex gap-2 leading-relaxed">
                <span className="text-slate-600 select-none">[{idx + 1}]</span>
                <span
                  className={
                    log.includes('CRITICAL') || log.includes('failed')
                      ? 'text-red-400'
                      : log.includes('Successfully') || log.includes('completed')
                      ? 'text-emerald-400'
                      : log.includes('Executing') || log.includes('Started')
                      ? 'text-teal-300'
                      : 'text-slate-300'
                  }
                >
                  {log}
                </span>
              </div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>
      )}

      {/* Final Research Dossier Viewer */}
      {activeWorkflow?.final_report_markdown && (
        <div className="bg-slate-900/95 border border-emerald-500/30 rounded-2xl p-6 shadow-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-100">
                  Publication-Grade Synthesis Dossier
                </h2>
                <p className="text-xs text-slate-400">
                  Synthesized across all 8 agents with cross-paper matrix, knowledge graph, empirical gaps, and verified claims.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyReport}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition-colors"
              >
                {copiedReport ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Markdown</span>
                  </>
                )}
              </button>

              <button
                onClick={handleDownloadReport}
                className="flex items-center gap-1.5 px-3 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg text-xs shadow-md transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Dossier (.md)</span>
              </button>
            </div>
          </div>

          {/* Markdown Content Viewer */}
          <div className="p-5 bg-slate-950/80 border border-slate-800/80 rounded-xl max-h-[600px] overflow-y-auto text-slate-200 text-xs font-mono leading-relaxed whitespace-pre-wrap select-text">
            {activeWorkflow.final_report_markdown}
          </div>
        </div>
      )}
    </div>
  );
};

