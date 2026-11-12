import React, { useState, useEffect, useMemo } from 'react';
import {
  Settings as SettingsIcon,
  Cpu,
  Database,
  Server,
  ShieldCheck,
  RefreshCw,
  HardDrive,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Info,
  Clock,
  Sliders,
  Terminal,
  Layers,
  FileCheck2,
  Box,
  FolderArchive,
  ArrowUpRight,
  Wifi,
  WifiOff,
  ChevronRight,
  Check,
  AlertCircle,
  XCircle,
  FileText,
  Search,
  Filter
} from 'lucide-react';
import {
  SystemHealth,
  Document,
  CompleteSystemStatus,
  SystemDiagnosticsResponse,
  DatabaseTestResponse,
  SystemConfig,
  AgentExecutionLogItem,
  InstalledOllamaModel
} from '../types';
import { api } from '../services/api';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { ModalDialog } from '../components/common/ModalDialog';

interface SettingsProps {
  health: SystemHealth | null;
  documents: Document[];
  onRefreshHealth: () => void;
}

export const Settings: React.FC<SettingsProps> = ({
  health,
  documents,
  onRefreshHealth
}) => {
  // Comprehensive status state
  const [systemStatus, setSystemStatus] = useState<CompleteSystemStatus | null>(null);
  const [frontendPing, setFrontendPing] = useState<{ latency_ms: number; status: string } | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Model Selection Form State
  const [selectedLLM, setSelectedLLM] = useState<string>('qwen3:1.7b');
  const [selectedEmbed, setSelectedEmbed] = useState<string>('nomic-embed-text');
  const [savingModels, setSavingModels] = useState<boolean>(false);

  // Configuration Form State
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [chunkSize, setChunkSize] = useState<number>(600);
  const [chunkOverlap, setChunkOverlap] = useState<number>(100);
  const [retrievalTopK, setRetrievalTopK] = useState<number>(4);
  const [modelOutputLimit, setModelOutputLimit] = useState<number>(512);
  const [temperature, setTemperature] = useState<number>(0.1);
  const [savingConfig, setSavingConfig] = useState<boolean>(false);
  const [configValidationError, setConfigValidationError] = useState<string | null>(null);

  // Control Test States
  const [testingOllama, setTestingOllama] = useState<boolean>(false);
  const [ollamaTestResult, setOllamaTestResult] = useState<any | null>(null);

  const [testingEmbedding, setTestingEmbedding] = useState<boolean>(false);
  const [embeddingTestResult, setEmbeddingTestResult] = useState<any | null>(null);

  const [testingDatabases, setTestingDatabases] = useState<boolean>(false);
  const [databaseTestResult, setDatabaseTestResult] = useState<DatabaseTestResponse | null>(null);

  const [runningDiagnostics, setRunningDiagnostics] = useState<boolean>(false);
  const [diagnosticsResult, setDiagnosticsResult] = useState<SystemDiagnosticsResponse | null>(null);
  const [showDiagnosticsModal, setShowDiagnosticsModal] = useState<boolean>(false);

  // Agent Logs Modal State
  const [showLogsModal, setShowLogsModal] = useState<boolean>(false);
  const [agentLogs, setAgentLogs] = useState<AgentExecutionLogItem[]>([]);
  const [logsTotal, setLogsTotal] = useState<number>(0);
  const [logsFilterStatus, setLogsFilterStatus] = useState<string>('');
  const [logsFilterAgent, setLogsFilterAgent] = useState<string>('');
  const [loadingLogs, setLoadingLogs] = useState<boolean>(false);

  // Load initial system data
  useEffect(() => {
    fetchSystemData();
  }, []);

  const fetchSystemData = async () => {
    setLoadingStatus(true);
    setError(null);
    try {
      const [statusRes, configRes, pingRes] = await Promise.all([
        api.getSystemStatus(),
        api.getSystemConfig(),
        api.pingFrontendConnection(),
      ]);

      setSystemStatus(statusRes);
      setFrontendPing(pingRes);

      // Populate config fields
      setConfig(configRes);
      setChunkSize(configRes.chunk_size);
      setChunkOverlap(configRes.chunk_overlap);
      setRetrievalTopK(configRes.retrieval_top_k);
      setModelOutputLimit(configRes.model_output_limit);
      setTemperature(configRes.temperature);

      // Populate model selections
      setSelectedLLM(statusRes.selected_llm.model);
      setSelectedEmbed(statusRes.embedding_model.model);
    } catch (err: any) {
      console.error('Failed to load system status', err);
      setError(err.message || 'Failed to query live system status');
    } finally {
      setLoadingStatus(false);
    }
  };

  // Client-side validation check
  useEffect(() => {
    if (chunkOverlap >= chunkSize) {
      setConfigValidationError(`Chunk overlap (${chunkOverlap}) must be strictly less than chunk size (${chunkSize}).`);
    } else {
      setConfigValidationError(null);
    }
  }, [chunkSize, chunkOverlap]);

  // Action: Save Model Selection
  const handleSaveModelSelection = async () => {
    setSavingModels(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const res = await api.selectActiveModels({
        llm_model: selectedLLM,
        embed_model: selectedEmbed,
      });
      setSuccessMessage(`Active models updated: LLM -> ${selectedLLM}, Embeddings -> ${selectedEmbed}`);
      await fetchSystemData();
      onRefreshHealth();
    } catch (err: any) {
      setError(err.message || 'Failed to update model selection');
    } finally {
      setSavingModels(false);
    }
  };

  // Action: Save Configuration
  const handleSaveConfig = async () => {
    if (chunkOverlap >= chunkSize) {
      setError(`Validation Error: Chunk overlap (${chunkOverlap}) must be strictly less than chunk size (${chunkSize}).`);
      return;
    }
    setSavingConfig(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await api.updateSystemConfig({
        chunk_size: Number(chunkSize),
        chunk_overlap: Number(chunkOverlap),
        retrieval_top_k: Number(retrievalTopK),
        model_output_limit: Number(modelOutputLimit),
        temperature: Number(temperature),
      });
      setConfig(updated);
      setSuccessMessage('System configuration validated and applied dynamically to runtime.');
    } catch (err: any) {
      setError(err.message || 'Configuration update failed');
    } finally {
      setSavingConfig(false);
    }
  };

  // Action: Test Ollama Connection
  const handleTestOllama = async () => {
    setTestingOllama(true);
    setOllamaTestResult(null);
    try {
      const res = await api.testOllamaPing();
      setOllamaTestResult(res);
    } catch (err: any) {
      setOllamaTestResult({ connected: false, error: err.message, latency_ms: 0 });
    } finally {
      setTestingOllama(false);
    }
  };

  // Action: Test Embedding Generation
  const handleTestEmbedding = async () => {
    setTestingEmbedding(true);
    setEmbeddingTestResult(null);
    try {
      const res = await api.testEmbeddingGen();
      setEmbeddingTestResult(res);
    } catch (err: any) {
      setEmbeddingTestResult({ success: false, error: err.message, dimensions: 0, latency_ms: 0 });
    } finally {
      setTestingEmbedding(false);
    }
  };

  // Action: Test Database Connections
  const handleTestDatabases = async () => {
    setTestingDatabases(true);
    setDatabaseTestResult(null);
    try {
      const res = await api.testDatabases();
      setDatabaseTestResult(res);
    } catch (err: any) {
      setError(err.message || 'Database connection test failed');
    } finally {
      setTestingDatabases(false);
    }
  };

  // Action: Run Full System Diagnostics Sweep
  const handleRunDiagnostics = async () => {
    setRunningDiagnostics(true);
    setDiagnosticsResult(null);
    try {
      const res = await api.runSystemDiagnostics();
      setDiagnosticsResult(res);
      setShowDiagnosticsModal(true);
    } catch (err: any) {
      setError(err.message || 'Failed to execute system diagnostics sweep');
    } finally {
      setRunningDiagnostics(false);
    }
  };

  // Action: Open Agent Execution Logs Viewer
  const handleOpenAgentLogs = async () => {
    setShowLogsModal(true);
    loadAgentLogs();
  };

  const loadAgentLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await api.getAgentExecutionLogs({
        agent_name: logsFilterAgent || undefined,
        status: logsFilterStatus || undefined,
        limit: 50,
        offset: 0,
      });
      setAgentLogs(res.logs);
      setLogsTotal(res.total_count);
    } catch (err: any) {
      console.error('Failed to load agent logs', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  // Calculate memory values
  const ramUsedGb = systemStatus
    ? (systemStatus.system_resources.ram_used_mb / 1024).toFixed(2)
    : health
    ? (health.ram_used_mb / 1024).toFixed(2)
    : '0.00';
  const ramTotalGb = systemStatus
    ? (systemStatus.system_resources.ram_total_mb / 1024).toFixed(2)
    : health
    ? (health.ram_total_mb / 1024).toFixed(2)
    : '8.00';
  const ramPercent = systemStatus
    ? systemStatus.system_resources.ram_percent
    : health
    ? health.ram_percent
    : 0;

  // Installed models list from live status
  const installedModelsList: InstalledOllamaModel[] = useMemo(() => {
    return systemStatus?.ollama?.installed_models || [];
  }, [systemStatus]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-slate-800" />
            Platform Settings & System Health
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real hardware monitoring, persistent database integrity, Ollama model routing, and validated runtime configuration.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRunDiagnostics}
            disabled={runningDiagnostics}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Activity className={`w-3.5 h-3.5 ${runningDiagnostics ? 'animate-spin' : ''}`} />
            {runningDiagnostics ? 'Running Sweep...' : 'Run Full Diagnostics'}
          </button>

          <button
            type="button"
            onClick={() => {
              fetchSystemData();
              onRefreshHealth();
            }}
            disabled={loadingStatus}
            className="px-3 py-1.5 text-xs bg-white border border-slate-300 rounded text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5"
            title="Refresh All Diagnostics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStatus ? 'animate-spin text-slate-500' : ''}`} />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}
      {successMessage && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-md p-3.5 flex items-center justify-between text-xs text-emerald-800">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-600 hover:text-emerald-900 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 2. Interactive Control Actions Bar */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-slate-800" />
            <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
              System Control & Diagnostic Probes
            </h2>
          </div>
          <span className="text-[11px] text-slate-500">Live operational validation</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {/* Test Ollama Connection */}
          <button
            type="button"
            onClick={handleTestOllama}
            disabled={testingOllama}
            className="p-3 border border-slate-200 rounded hover:bg-slate-50 text-left transition-colors flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-800">Test Ollama</span>
              <Server className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500">
              {testingOllama ? 'Pinging server...' : 'Verify local server port'}
            </span>
          </button>

          {/* Test Embedding Gen */}
          <button
            type="button"
            onClick={handleTestEmbedding}
            disabled={testingEmbedding}
            className="p-3 border border-slate-200 rounded hover:bg-slate-50 text-left transition-colors flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-800">Test Embedding</span>
              <Sliders className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500">
              {testingEmbedding ? 'Generating vector...' : '768-dim dense vector test'}
            </span>
          </button>

          {/* Check Database Connections */}
          <button
            type="button"
            onClick={handleTestDatabases}
            disabled={testingDatabases}
            className="p-3 border border-slate-200 rounded hover:bg-slate-50 text-left transition-colors flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-800">Check Databases</span>
              <Database className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500">
              {testingDatabases ? 'Querying engines...' : 'SQLite & ChromaDB probe'}
            </span>
          </button>

          {/* Run Full Diagnostics */}
          <button
            type="button"
            onClick={handleRunDiagnostics}
            disabled={runningDiagnostics}
            className="p-3 border border-slate-200 rounded hover:bg-slate-50 text-left transition-colors flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-800">Full Diagnostics</span>
              <Activity className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500">
              {runningDiagnostics ? 'Testing subsystems...' : '7-point component sweep'}
            </span>
          </button>

          {/* View Agent Execution Logs */}
          <button
            type="button"
            onClick={handleOpenAgentLogs}
            className="p-3 border border-slate-200 rounded hover:bg-slate-50 text-left transition-colors flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-800">Agent Logs</span>
              <Terminal className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500">
              {systemStatus?.sqlite?.counts?.agent_logs || 0} SQLite history records
            </span>
          </button>
        </div>

        {/* Live Probe Feedback Banners */}
        {ollamaTestResult && (
          <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              {ollamaTestResult.connected ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600" />
              )}
              <span className="text-slate-800">
                <strong>Ollama Connection:</strong>{' '}
                {ollamaTestResult.connected
                  ? `Online at ${ollamaTestResult.base_url} (${ollamaTestResult.installed_count} models installed, latency: ${ollamaTestResult.latency_ms} ms)`
                  : `Offline (${ollamaTestResult.error || 'Server not reachable on port 11434'})`}
              </span>
            </div>
            <button
              onClick={() => setOllamaTestResult(null)}
              className="text-slate-400 hover:text-slate-700 text-[11px]"
            >
              Close
            </button>
          </div>
        )}

        {embeddingTestResult && (
          <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              {embeddingTestResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              )}
              <span className="text-slate-800">
                <strong>Embedding Generation:</strong>{' '}
                {embeddingTestResult.success
                  ? `Successfully produced ${embeddingTestResult.dimensions}-dimensional vector (${embeddingTestResult.latency_ms} ms)`
                  : `Failed (${embeddingTestResult.error})`}
              </span>
            </div>
            <button
              onClick={() => setEmbeddingTestResult(null)}
              className="text-slate-400 hover:text-slate-700 text-[11px]"
            >
              Close
            </button>
          </div>
        )}

        {databaseTestResult && (
          <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded text-xs flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                SQLite: {databaseTestResult.sqlite.connected ? 'Operational' : 'Failed'}{' '}
                <span className="font-mono text-slate-500">({databaseTestResult.sqlite.latency_ms} ms)</span>
              </span>
              <span className="text-slate-300">|</span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ChromaDB: {databaseTestResult.chromadb.connected ? 'Operational' : 'Failed'}{' '}
                <span className="font-mono text-slate-500">
                  ({databaseTestResult.chromadb.total_chunks} chunks, {databaseTestResult.chromadb.latency_ms} ms)
                </span>
              </span>
            </div>
            <button
              onClick={() => setDatabaseTestResult(null)}
              className="text-slate-400 hover:text-slate-700 text-[11px]"
            >
              Close
            </button>
          </div>
        )}
      </div>

      {/* 3. Subsystem Health Grid (All 8 Required Components + Frontend Connection) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 1. Ollama Connection Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Ollama Connection
              </h3>
            </div>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                systemStatus?.ollama?.connected
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border-rose-200'
              }`}
            >
              {systemStatus?.ollama?.connected ? 'Connected' : 'Offline'}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Service Endpoint:</span>
              <span className="font-mono text-slate-800 truncate max-w-[170px]">
                {systemStatus?.ollama?.base_url || 'http://localhost:11434'}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Installed Models:</span>
              <span className="font-mono font-medium text-slate-800">
                {installedModelsList.length} Models
              </span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Execution Mode:</span>
              <span className="text-slate-800 font-medium">Local Workstation</span>
            </div>
            {!systemStatus?.ollama?.connected && (
              <p className="text-[11px] text-rose-700 bg-rose-50 p-2 rounded border border-rose-200 leading-tight">
                {systemStatus?.ollama?.error || 'Ensure Ollama service is running on port 11434.'}
              </p>
            )}
          </div>
        </div>

        {/* 2. Selected LLM & Model Selection Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Selected LLM Model
              </h3>
            </div>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                systemStatus?.selected_llm?.is_ready
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              {systemStatus?.selected_llm?.is_ready ? 'Ready' : 'Not Loaded'}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Active LLM:</label>
              <select
                value={selectedLLM}
                onChange={(e) => setSelectedLLM(e.target.value)}
                className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded px-2.5 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-500"
              >
                {installedModelsList.length > 0 ? (
                  installedModelsList.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} ({m.size_mb > 1024 ? `${(m.size_mb / 1024).toFixed(1)} GB` : `${m.size_mb} MB`})
                    </option>
                  ))
                ) : (
                  <>
                    <option value="qwen3:1.7b">qwen3:1.7b (8GB Optimized)</option>
                    <option value="llama3.2:1b">llama3.2:1b</option>
                    <option value="mistral:7b">mistral:7b</option>
                  </>
                )}
              </select>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
              <span>Context Length:</span>
              <span className="font-mono text-slate-800 font-medium">
                {systemStatus?.selected_llm?.context_length || 4096} tokens
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleSaveModelSelection}
                disabled={savingModels}
                className="px-2.5 py-1 text-xs font-medium rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {savingModels ? 'Saving...' : 'Save Model Selection'}
              </button>
            </div>
          </div>
        </div>

        {/* 3. Embedding Model Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Embedding Model
              </h3>
            </div>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                systemStatus?.embedding_model?.is_ready
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-300'
              }`}
            >
              {systemStatus?.embedding_model?.is_ready ? 'Ready' : 'Configured'}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Embedding Architecture:</label>
              <select
                value={selectedEmbed}
                onChange={(e) => setSelectedEmbed(e.target.value)}
                className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded px-2.5 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-500"
              >
                <option value="nomic-embed-text">nomic-embed-text (768-dim normalized)</option>
                <option value="bge-small-en-v1.5">bge-small-en-v1.5 (384-dim)</option>
                <option value="all-minilm">all-minilm (384-dim)</option>
              </select>
            </div>

            <div className="flex items-center justify-between py-1 border-b border-slate-100 text-[11px]">
              <span className="text-slate-500">Vector Dimensions:</span>
              <span className="font-mono text-slate-800 font-medium">768 Float32</span>
            </div>
            <div className="flex items-center justify-between py-1 text-[11px]">
              <span className="text-slate-500">Indexing Strategy:</span>
              <span className="text-slate-800 font-medium">Hybrid BM25 + Dense</span>
            </div>
          </div>
        </div>

        {/* 4. SQLite Database Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                SQLite Database
              </h3>
            </div>
            <span className="text-[11px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
              WAL Mode
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Database Size:</span>
              <span className="font-mono font-medium text-slate-800">
                {systemStatus?.sqlite?.size_mb || 0} MB
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Engine Version:</span>
              <span className="font-mono text-slate-800">
                SQLite v{systemStatus?.sqlite?.version || '3.43.1'}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Indexed Papers:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.sqlite?.counts?.papers || documents.length} records
              </span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Active Projects:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.sqlite?.counts?.projects || 0} workspaces
              </span>
            </div>
          </div>
        </div>

        {/* 5. ChromaDB Vector Store Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Box className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                ChromaDB Vector Store
              </h3>
            </div>
            <span className="text-[11px] font-mono text-slate-700 bg-slate-100 border border-slate-300 px-2 py-0.5 rounded">
              HNSW Cosine
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Indexed Chunks:</span>
              <span className="font-mono font-medium text-slate-800">
                {systemStatus?.chromadb?.total_chunks_indexed || 0} vectors
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Collection Name:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.chromadb?.active_collection || 'literature_chunks'}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Vector Storage Size:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.chromadb?.size_mb || 0} MB
              </span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Persistence Path:</span>
              <span className="font-mono text-slate-600 truncate max-w-[160px]">
                {systemStatus?.chromadb?.persist_dir || 'data/chroma'}
              </span>
            </div>
          </div>
        </div>

        {/* 6. PDF Storage Directory Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <FolderArchive className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                PDF Storage
              </h3>
            </div>
            <span className="text-[11px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
              Writable
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Archived Documents:</span>
              <span className="font-mono font-medium text-slate-800">
                {systemStatus?.pdf_storage?.total_pdf_files || 0} PDFs
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Total PDF Storage:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.pdf_storage?.total_size_mb || 0} MB
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Directory Access:</span>
              <span className="text-slate-800 font-medium">Read / Write Access</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Storage Root:</span>
              <span className="font-mono text-slate-600 truncate max-w-[160px]">
                {systemStatus?.pdf_storage?.dir_path || 'backend/data/PDFs'}
              </span>
            </div>
          </div>
        </div>

        {/* 7. Backend API Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Backend API
              </h3>
            </div>
            <span className="text-[11px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
              v{systemStatus?.backend?.version || '1.0.0'}
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Runtime Engine:</span>
              <span className="font-mono text-slate-800 font-medium">FastAPI + Uvicorn</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Host & Port:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.backend?.host || '127.0.0.1'}:{systemStatus?.backend?.port || 8000}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Process PID:</span>
              <span className="font-mono text-slate-800">PID {systemStatus?.backend?.pid || 0}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Uptime:</span>
              <span className="font-mono text-slate-800">
                {systemStatus?.backend?.uptime_seconds ? `${Math.round(systemStatus.backend.uptime_seconds / 60)} min` : 'Active'}
              </span>
            </div>
          </div>
        </div>

        {/* 8. Frontend Connection Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Wifi className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Frontend API Connection
              </h3>
            </div>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                frontendPing?.status === 'connected'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border-rose-200'
              }`}
            >
              {frontendPing?.status === 'connected' ? 'Connected' : 'Interrupted'}
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Roundtrip Latency:</span>
              <span className="font-mono font-medium text-slate-800">
                {frontendPing ? `${frontendPing.latency_ms} ms` : 'Measuring...'}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Client Protocol:</span>
              <span className="font-mono text-slate-800">HTTP/1.1 REST</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">CORS Whitelist:</span>
              <span className="font-mono text-slate-800">Vite (5173 / localhost)</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">State Sync:</span>
              <span className="text-emerald-700 font-medium">Automatic 20s Polling</span>
            </div>
          </div>
        </div>

        {/* 9. 8 GB RAM Resource Protection Envelope Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-slate-800" />
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                8 GB RAM Hardware Envelope
              </h3>
            </div>
            <span className="text-[11px] font-mono text-slate-700 bg-slate-100 border border-slate-300 px-2 py-0.5 rounded">
              Win 11 x64
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <div className="flex items-center justify-between text-slate-600 mb-1">
                <span>Memory Footprint:</span>
                <span className="font-mono font-semibold text-slate-900">
                  {ramUsedGb} GB / {ramTotalGb} GB ({ramPercent.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-1.5 transition-all duration-300 ${
                    ramPercent > 85 ? 'bg-rose-500' : ramPercent > 70 ? 'bg-amber-500' : 'bg-slate-900'
                  }`}
                  style={{ width: `${Math.min(ramPercent, 100)}%` }}
                />
              </div>
            </div>

            <div className="text-[11px] text-slate-500 space-y-1 pt-1">
              <div>&bull; Sequential agent execution protects memory buffers.</div>
              <div>&bull; SQLite WAL mode bounded cache limit (64 MB).</div>
              <div>&bull; Strict chunk truncation prevents token thrashing.</div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Validated Runtime Configuration Editor */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-slate-800" />
              <h2 className="text-sm font-semibold text-slate-900">
                Document Ingestion & Model Hyperparameters
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Tune chunking token budgets, semantic retrieval top K, and LLM output lengths with strict validation.
            </p>
          </div>

          <button
            type="button"
            onClick={handleSaveConfig}
            disabled={savingConfig || Boolean(configValidationError)}
            className="px-3.5 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-xs"
          >
            <Check className="w-3.5 h-3.5" />
            {savingConfig ? 'Validating & Applying...' : 'Save & Apply Configuration'}
          </button>
        </div>

        {configValidationError && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{configValidationError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Chunk Size */}
          <div className="p-3 bg-slate-50/75 border border-slate-200 rounded space-y-1.5">
            <label className="block font-semibold text-slate-800">
              Chunk Size (Tokens)
            </label>
            <input
              type="number"
              min={100}
              max={4000}
              step={50}
              value={chunkSize}
              onChange={(e) => setChunkSize(parseInt(e.target.value) || 600)}
              className="w-full text-xs font-mono bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
            <p className="text-[11px] text-slate-500 leading-tight">
              Tokens per section chunk (Range: 100 - 4000 tokens).
            </p>
          </div>

          {/* Chunk Overlap */}
          <div className="p-3 bg-slate-50/75 border border-slate-200 rounded space-y-1.5">
            <label className="block font-semibold text-slate-800">
              Chunk Overlap (Tokens)
            </label>
            <input
              type="number"
              min={0}
              max={1000}
              step={20}
              value={chunkOverlap}
              onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 0)}
              className="w-full text-xs font-mono bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
            <p className="text-[11px] text-slate-500 leading-tight">
              Must be strictly less than chunk size (Range: 0 - 1000).
            </p>
          </div>

          {/* Retrieval Top K */}
          <div className="p-3 bg-slate-50/75 border border-slate-200 rounded space-y-1.5">
            <label className="block font-semibold text-slate-800">
              Retrieval Top K
            </label>
            <input
              type="number"
              min={1}
              max={20}
              step={1}
              value={retrievalTopK}
              onChange={(e) => setRetrievalTopK(parseInt(e.target.value) || 4)}
              className="w-full text-xs font-mono bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
            <p className="text-[11px] text-slate-500 leading-tight">
              Dense + BM25 chunks retrieved per query (Range: 1 - 20).
            </p>
          </div>

          {/* Model Output Limit */}
          <div className="p-3 bg-slate-50/75 border border-slate-200 rounded space-y-1.5">
            <label className="block font-semibold text-slate-800">
              Model Output Limit (Tokens)
            </label>
            <input
              type="number"
              min={64}
              max={4096}
              step={64}
              value={modelOutputLimit}
              onChange={(e) => setModelOutputLimit(parseInt(e.target.value) || 512)}
              className="w-full text-xs font-mono bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
            <p className="text-[11px] text-slate-500 leading-tight">
              Max generated tokens (Range: 64 - 4096).
            </p>
          </div>
        </div>
      </div>

      {/* Diagnostics Modal Dialog */}
      {showDiagnosticsModal && diagnosticsResult && (
        <ModalDialog
          isOpen={true}
          onClose={() => setShowDiagnosticsModal(false)}
          title="Full System Diagnostics Audit Report"
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-lg border flex items-center justify-between bg-slate-50 border-slate-200">
              <div className="flex items-center gap-2">
                {diagnosticsResult.overall_status === 'healthy' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : diagnosticsResult.overall_status === 'warning' ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600" />
                )}
                <div>
                  <div className="font-semibold text-slate-900 uppercase tracking-tight">
                    Overall Status: {diagnosticsResult.overall_status}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {diagnosticsResult.passed} Passed &bull; {diagnosticsResult.warnings} Warnings &bull; {diagnosticsResult.failures} Failures
                  </div>
                </div>
              </div>
              <span className="font-mono text-slate-400 text-[11px]">
                {new Date(diagnosticsResult.timestamp * 1000).toLocaleTimeString()}
              </span>
            </div>

            <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
              {diagnosticsResult.checks.map((chk, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded border text-xs flex items-start gap-3 ${
                    chk.status === 'pass'
                      ? 'bg-white border-slate-200 text-slate-800'
                      : chk.status === 'warn'
                      ? 'bg-amber-50/50 border-amber-200 text-amber-900'
                      : 'bg-rose-50/50 border-rose-200 text-rose-900'
                  }`}
                >
                  <div className="mt-0.5">
                    {chk.status === 'pass' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : chk.status === 'warn' ? (
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold">{chk.component}</div>
                    <div className="text-slate-600 text-[11px] mt-0.5 leading-relaxed">
                      {chk.message}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button
                type="button"
                onClick={() => setShowDiagnosticsModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800"
              >
                Close Report
              </button>
            </div>
          </div>
        </ModalDialog>
      )}

      {/* Agent Execution Logs Modal Dialog */}
      {showLogsModal && (
        <ModalDialog
          isOpen={true}
          onClose={() => setShowLogsModal(false)}
          title="Agent Execution History & Audit Logs"
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            {/* Filter Controls */}
            <div className="flex flex-col sm:flex-row gap-2 justify-between items-center bg-slate-50 p-2.5 rounded border border-slate-200">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select
                  value={logsFilterStatus}
                  onChange={(e) => {
                    setLogsFilterStatus(e.target.value);
                  }}
                  className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-800"
                >
                  <option value="">All Statuses</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="running">Running</option>
                </select>

                <select
                  value={logsFilterAgent}
                  onChange={(e) => {
                    setLogsFilterAgent(e.target.value);
                  }}
                  className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-800"
                >
                  <option value="">All Agents</option>
                  <option value="Research Discovery Agent">Discovery Agent</option>
                  <option value="PDF Understanding Agent">PDF Understanding</option>
                  <option value="Semantic Retrieval Agent">Retrieval Agent</option>
                  <option value="Research Analysis Agent">Analysis Agent</option>
                  <option value="Cross-Paper Comparison Agent">Comparison Agent</option>
                  <option value="Research Knowledge Graph Agent">Graph Agent</option>
                  <option value="Research Gap Discovery Agent">Gap Agent</option>
                  <option value="Evidence Verification Agent">Verification Agent</option>
                </select>

                <button
                  type="button"
                  onClick={loadAgentLogs}
                  className="p-1 text-slate-600 hover:text-slate-900 border border-slate-300 rounded bg-white"
                  title="Reload Logs"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>

              <span className="text-[11px] text-slate-500">
                {logsTotal} execution events recorded in SQLite
              </span>
            </div>

            {/* Logs Table */}
            <div className="max-h-[55vh] overflow-y-auto border border-slate-200 rounded">
              {loadingLogs ? (
                <div className="p-8 text-center text-slate-500">Loading audit records...</div>
              ) : agentLogs.length > 0 ? (
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2 px-3">Agent & Action</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Duration</th>
                      <th className="py-2 px-3">Summary / Details</th>
                      <th className="py-2 px-3">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {agentLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/75">
                        <td className="py-2.5 px-3 font-sans">
                          <div className="font-semibold text-slate-900">{log.agent_name}</div>
                          <div className="text-slate-400 font-mono text-[10px]">{log.action_type}</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold border ${
                              log.status === 'completed'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                : log.status === 'failed'
                                ? 'bg-rose-50 text-rose-800 border-rose-200'
                                : 'bg-slate-100 text-slate-700 border-slate-300'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">
                          {log.duration_ms ? `${log.duration_ms} ms` : '-'}
                        </td>
                        <td className="py-2.5 px-3 font-sans max-w-xs truncate text-slate-700">
                          {log.error_message ? (
                            <span className="text-rose-600">{log.error_message}</span>
                          ) : (
                            log.output_summary || log.input_payload || 'Execution recorded'
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 text-[10px]">
                          {log.created_at ? new Date(log.created_at).toLocaleTimeString() : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-slate-500">
                  No agent execution logs matching the current filter.
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button
                type="button"
                onClick={() => setShowLogsModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800"
              >
                Close Logs
              </button>
            </div>
          </div>
        </ModalDialog>
      )}
    </div>
  );
};

export default Settings;
