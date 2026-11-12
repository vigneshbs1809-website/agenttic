import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  AlertTriangle,
  RefreshCw,
  Filter,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Split,
  Layers,
  Sparkles,
  BookOpen,
  Trash2,
  Info
} from 'lucide-react';
import {
  Document,
  ResearchProjectItem,
  ContradictionItem,
  DetectContradictionsResponse,
  ContradictionCategory,
  ContradictionNature
} from '../types';
import { api } from '../services/api';

interface ContradictionDetectionProps {
  documents: Document[];
}

export const ContradictionDetection: React.FC<ContradictionDetectionProps> = ({ documents }) => {
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedNature, setSelectedNature] = useState<string>('all');
  const [data, setData] = useState<DetectContradictionsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0) {
        setSelectedProjectId(projs[0].id);
        loadContradictions(projs[0].id);
      } else {
        loadContradictions();
      }
    } catch (err) {
      console.warn('Failed to load projects', err);
      loadContradictions();
    }
  };

  const loadContradictions = async (projId?: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const targetProj = projId !== undefined ? projId : selectedProjectId;
      let res: DetectContradictionsResponse;

      if (targetProj) {
        res = await api.getProjectContradictions(targetProj, {
          category: selectedCategory !== 'all' ? selectedCategory : undefined,
          nature: selectedNature !== 'all' ? selectedNature : undefined,
        });
      } else {
        res = await api.detectContradictions({
          force_redetect: false,
        });
      }
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load contradiction data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunDetection = async () => {
    setIsDetecting(true);
    setErrorMsg(null);
    try {
      const res = await api.detectContradictions({
        project_id: selectedProjectId || undefined,
        force_redetect: true,
      });
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Contradiction detection failed');
    } finally {
      setIsDetecting(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to dismiss this contradiction?')) return;
    try {
      await api.deleteContradiction(id);
      if (data) {
        const updated = data.contradictions.filter((c) => c.id !== id);
        setData({
          ...data,
          total_contradictions: updated.length,
          contradictions: updated,
        });
      }
    } catch (err: any) {
      alert('Failed to delete contradiction');
    }
  };

  // Filtered in-memory list if needed
  const filteredContradictions = (data?.contradictions || []).filter((c) => {
    if (selectedCategory !== 'all' && c.category !== selectedCategory) return false;
    if (selectedNature !== 'all' && c.nature !== selectedNature) return false;
    return true;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Module A: Conflict Dissection Engine
            </span>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Split className="w-3.5 h-3.5 text-amber-400" />
              Condition-Dependent vs Genuine Distinction
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 mt-1">Cross-Paper Contradiction Detection</h1>
          <p className="text-sm text-slate-400">
            Dissects conflicting experimental results, divergent conclusions, architectural differences, dataset inconsistencies, and opposing algorithmic claims across literature papers.
          </p>
        </div>

        {/* Action Button */}
        <button
          onClick={handleRunDetection}
          disabled={isDetecting || isLoading}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isDetecting ? 'animate-spin' : ''}`} />
          <span>{isDetecting ? 'Detecting Conflicts...' : 'Detect Contradictions'}</span>
        </button>
      </div>

      {/* Control Bar: Filters & Project Selector */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Project Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-slate-300">
            <BookOpen className="w-4 h-4 text-amber-400" />
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                loadContradictions(e.target.value);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="">-- All Literature Corpus --</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          <div className="h-4 w-px bg-slate-800 hidden sm:block" />

          {/* Category Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-300">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="all">All Categories</option>
              <option value="experimental_results">Experimental Results</option>
              <option value="conclusions">Conclusions</option>
              <option value="methodology">Methodology</option>
              <option value="dataset_findings">Dataset Findings</option>
              <option value="algorithmic_claims">Algorithmic Claims</option>
            </select>
          </div>

          {/* Nature Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-300">
            <select
              value={selectedNature}
              onChange={(e) => setSelectedNature(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="all">All Conflict Natures</option>
              <option value="genuine_contradiction">Genuine Contradiction</option>
              <option value="condition_dependent_difference">Condition-Dependent Difference</option>
              <option value="methodological_divergence">Methodological Divergence</option>
            </select>
          </div>
        </div>

        {/* Counter Badge */}
        <div className="text-xs text-slate-400">
          Showing <span className="text-slate-100 font-semibold">{filteredContradictions.length}</span> of{' '}
          <span className="text-slate-100 font-semibold">{data?.total_contradictions || 0}</span> conflicts
        </div>
      </div>

      {/* Summary KPI Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 uppercase font-semibold">Total Contradictions</span>
            <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">{data.total_contradictions}</div>
            <span className="text-[11px] text-slate-500">Cross-examined across corpus</span>
          </div>

          <div className="bg-slate-900/60 border border-red-500/20 rounded-xl p-4">
            <span className="text-xs text-red-400 uppercase font-semibold">Genuine Contradictions</span>
            <div className="text-2xl font-bold text-red-300 mt-1 font-mono">{data.genuine_count}</div>
            <span className="text-[11px] text-slate-500">Comparable setups, opposing facts</span>
          </div>

          <div className="bg-slate-900/60 border border-amber-500/20 rounded-xl p-4">
            <span className="text-xs text-amber-400 uppercase font-semibold">Condition-Dependent</span>
            <div className="text-2xl font-bold text-amber-300 mt-1 font-mono">{data.condition_dependent_count}</div>
            <span className="text-[11px] text-slate-500">Caused by network/dataset shift</span>
          </div>

          <div className="bg-slate-900/60 border border-blue-500/20 rounded-xl p-4">
            <span className="text-xs text-blue-400 uppercase font-semibold">Methodological Divergences</span>
            <div className="text-2xl font-bold text-blue-300 mt-1 font-mono">
              {data.methodological_divergence_count}
            </div>
            <span className="text-[11px] text-slate-500">Different architectural paradigms</span>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-400 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Contradictions List */}
      <div className="space-y-4">
        {filteredContradictions.length === 0 ? (
          <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl space-y-3">
            <GitCompare className="w-8 h-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-300">No Contradictions Detected in Filter</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              No conflicting findings found matching the selected criteria. Click "Detect Contradictions" to scan the literature corpus.
            </p>
          </div>
        ) : (
          filteredContradictions.map((c: ContradictionItem) => {
            const isExpanded = expandedId === c.id;

            // Nature pill styles
            const isGenuine = c.nature === 'genuine_contradiction';
            const isCond = c.nature === 'condition_dependent_difference';
            const isMeth = c.nature === 'methodological_divergence';

            return (
              <div
                key={c.id}
                className={`border rounded-2xl transition-all overflow-hidden ${
                  isGenuine
                    ? 'bg-slate-900/80 border-red-500/30 hover:border-red-500/50'
                    : isCond
                    ? 'bg-slate-900/80 border-amber-500/30 hover:border-amber-500/50'
                    : 'bg-slate-900/80 border-blue-500/30 hover:border-blue-500/50'
                }`}
              >
                {/* Header */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : c.id)}
                  className="p-5 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 select-none"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Nature Badge */}
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${
                          isGenuine
                            ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                            : isCond
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                        }`}
                      >
                        {c.nature.replace(/_/g, ' ')}
                      </span>

                      {/* Category Badge */}
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {c.category.replace(/_/g, ' ')}
                      </span>

                      {/* Severity */}
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                          c.severity === 'high'
                            ? 'bg-red-950 text-red-400'
                            : c.severity === 'medium'
                            ? 'bg-amber-950 text-amber-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {c.severity.toUpperCase()} SEVERITY
                      </span>

                      <span className="text-xs text-slate-500 font-mono">
                        Confidence: {(c.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-100">{c.title}</h3>
                    <p className="text-xs text-slate-400 line-clamp-2">{c.description}</p>
                  </div>

                  {/* Actions & Chevron */}
                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={(e) => handleDelete(c.id, e)}
                      className="p-1.5 text-slate-500 hover:text-red-400 transition-colors"
                      title="Dismiss contradiction"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Collapsible Passages & Root Cause Drawer */}
                {isExpanded && (
                  <div className="p-5 pt-0 border-t border-slate-800/80 bg-slate-950/60 space-y-4 text-xs">
                    {/* Root Cause Analysis Banner */}
                    {c.root_cause_analysis && (
                      <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-amber-400">
                          <Info className="w-4 h-4" />
                          <span>Condition Analysis & Underlying Root Cause:</span>
                        </div>
                        <p className="text-slate-300 leading-relaxed">{c.root_cause_analysis}</p>
                      </div>
                    )}

                    {/* Side-by-Side Source Passages */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Paper A Box */}
                      <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <span className="font-bold text-slate-200 truncate max-w-[240px]">
                            {c.paper_a_title}
                          </span>
                          <span className="text-[11px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            Page {c.page_a || 1}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-medium">
                          Section: {c.section_a || 'Experiments / Results'}
                        </div>
                        <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-slate-300 font-mono text-[11px] leading-relaxed max-h-48 overflow-y-auto">
                          "{c.passage_a}"
                        </div>
                      </div>

                      {/* Paper B Box */}
                      <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <span className="font-bold text-slate-200 truncate max-w-[240px]">
                            {c.paper_b_title}
                          </span>
                          <span className="text-[11px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            Page {c.page_b || 1}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-medium">
                          Section: {c.section_b || 'Experiments / Results'}
                        </div>
                        <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-slate-300 font-mono text-[11px] leading-relaxed max-h-48 overflow-y-auto">
                          "{c.passage_b}"
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

