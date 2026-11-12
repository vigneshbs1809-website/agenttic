import React, { useState, useEffect } from 'react';
import {
  Split,
  RefreshCw,
  Filter,
  Trash2,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Info,
  CheckCircle2,
  FileText
} from 'lucide-react';
import {
  Document,
  ResearchProjectItem,
  ContradictionItem,
  DetectContradictionsResponse
} from '../types';
import { api } from '../services/api';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LoadingState } from '../components/common/LoadingState';

interface ContradictionAnalysisProps {
  documents: Document[];
  projects: ResearchProjectItem[];
  selectedProjectId?: string;
}

export const ContradictionAnalysis: React.FC<ContradictionAnalysisProps> = ({
  documents,
  projects,
  selectedProjectId: initialProjectId = ''
}) => {
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedNature, setSelectedNature] = useState<string>('all');
  const [data, setData] = useState<DetectContradictionsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadContradictions(selectedProjectId);
  }, [selectedProjectId]);

  const loadContradictions = async (projId?: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      let res: DetectContradictionsResponse;
      if (projId) {
        res = await api.getProjectContradictions(projId, {
          category: selectedCategory !== 'all' ? selectedCategory : undefined,
          nature: selectedNature !== 'all' ? selectedNature : undefined,
        });
      } else {
        res = await api.detectContradictions({ force_redetect: false });
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
    if (!confirm('Dismiss this detected contradiction?')) return;
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

  const filteredContradictions = (data?.contradictions || []).filter((c) => {
    if (selectedCategory !== 'all' && c.category !== selectedCategory) return false;
    if (selectedNature !== 'all' && c.nature !== selectedNature) return false;
    return true;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-bold text-gray-900 tracking-tight">
            Cross-Paper Contradiction Analysis
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            Examines conflicting experimental outcomes, opposing conclusions, and divergent algorithmic claims between papers, rigorously distinguishing genuine contradictions from condition-dependent differences.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRunDetection}
          disabled={isDetecting || isLoading}
          className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isDetecting ? 'animate-spin' : ''}`} />
          <span>{isDetecting ? 'Analyzing Conflicts...' : 'Detect Contradictions'}</span>
        </button>
      </div>

      {/* Error Message */}
      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Controls Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Project Dropdown */}
          <div className="flex items-center gap-1.5 text-gray-700">
            <BookOpen className="w-4 h-4 text-gray-400" />
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="">All Literature Corpus</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          <div className="h-4 w-px bg-gray-200 hidden sm:block" />

          {/* Category Filter */}
          <div className="flex items-center gap-1.5 text-gray-700">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
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
          <div className="flex items-center gap-1.5 text-gray-700">
            <select
              value={selectedNature}
              onChange={(e) => setSelectedNature(e.target.value)}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="all">All Conflict Natures</option>
              <option value="genuine_contradiction">Genuine Contradictions</option>
              <option value="condition_dependent_difference">Condition-Dependent Differences</option>
              <option value="methodological_divergence">Methodological Divergences</option>
            </select>
          </div>
        </div>

        <div className="text-gray-500">
          Showing <span className="font-semibold text-gray-800">{filteredContradictions.length}</span> of{' '}
          <span className="font-semibold text-gray-800">{data?.total_contradictions || 0}</span> conflicts
        </div>
      </div>

      {/* KPI Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-3.5 space-y-1 shadow-2xs">
            <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider block">Total Conflicts</span>
            <div className="text-xl font-bold text-gray-900 font-mono">{data.total_contradictions}</div>
          </div>

          <div className="bg-white border border-rose-200 rounded-lg p-3.5 space-y-1 shadow-2xs">
            <span className="text-[10px] text-rose-700 font-semibold uppercase tracking-wider block">Genuine Contradictions</span>
            <div className="text-xl font-bold text-rose-800 font-mono">{data.genuine_count}</div>
          </div>

          <div className="bg-white border border-amber-200 rounded-lg p-3.5 space-y-1 shadow-2xs">
            <span className="text-[10px] text-amber-700 font-semibold uppercase tracking-wider block">Condition Dependent</span>
            <div className="text-xl font-bold text-amber-800 font-mono">{data.condition_dependent_count}</div>
          </div>

          <div className="bg-white border border-blue-200 rounded-lg p-3.5 space-y-1 shadow-2xs">
            <span className="text-[10px] text-blue-700 font-semibold uppercase tracking-wider block">Methodological Divergences</span>
            <div className="text-xl font-bold text-blue-800 font-mono">{data.methodological_divergence_count}</div>
          </div>
        </div>
      )}

      {/* Contradictions List */}
      {isLoading ? (
        <LoadingState message="Cross-examining papers and analyzing conflict conditions..." />
      ) : filteredContradictions.length === 0 ? (
        <div className="p-12 text-center bg-gray-50/50 border border-gray-200 rounded-lg space-y-2">
          <Split className="w-8 h-8 text-gray-400 mx-auto" />
          <h4 className="text-sm font-semibold text-gray-700">No Contradictions in Current Filter</h4>
          <p className="text-xs text-gray-500">
            Click "Detect Contradictions" to cross-examine research papers across your library.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredContradictions.map((c: ContradictionItem) => {
            const isExpanded = expandedId === c.id;
            const isGenuine = c.nature === 'genuine_contradiction';
            const isCond = c.nature === 'condition_dependent_difference';

            return (
              <div
                key={c.id}
                className="bg-white border border-gray-200 rounded-lg shadow-2xs overflow-hidden transition-all hover:border-gray-300"
              >
                {/* Card Header Row */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : c.id)}
                  className="p-5 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 select-none"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          isGenuine
                            ? 'bg-rose-50 text-rose-800 border border-rose-200'
                            : isCond
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : 'bg-blue-50 text-blue-800 border border-blue-200'
                        }`}
                      >
                        {c.nature.replace(/_/g, ' ')}
                      </span>

                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-700">
                        {c.category.replace(/_/g, ' ')}
                      </span>

                      <span className="text-[10px] font-mono text-gray-500">
                        Confidence: {(c.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-gray-900">{c.title}</h3>
                    <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">
                      {c.description}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      type="button"
                      onClick={(e) => handleDelete(c.id, e)}
                      className="p-1 text-gray-400 hover:text-rose-600 transition-colors"
                      title="Dismiss conflict"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </div>

                {/* Collapsible Passages & Root Cause Drawer */}
                {isExpanded && (
                  <div className="p-5 pt-1 border-t border-gray-100 bg-gray-50/60 space-y-4 text-xs">
                    {/* Root Cause Analysis Banner */}
                    {c.root_cause_analysis && (
                      <div className="p-3.5 bg-white border border-gray-200 rounded-md space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-gray-900 text-[11px] uppercase tracking-wider">
                          <Info className="w-3.5 h-3.5 text-gray-500" />
                          <span>Condition Analysis & Underlying Root Cause:</span>
                        </div>
                        <p className="text-gray-800 leading-relaxed font-sans">{c.root_cause_analysis}</p>
                      </div>
                    )}

                    {/* Side-by-Side Source Passages */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Paper A Box */}
                      <div className="p-4 bg-white border border-gray-200 rounded-md space-y-2">
                        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                          <span className="font-semibold text-gray-900 truncate max-w-[240px]">
                            {c.paper_a_title}
                          </span>
                          <span className="text-[10px] font-mono bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                            Page {c.page_a || 1}
                          </span>
                        </div>
                        <div className="text-[10px] text-gray-500">
                          Section: {c.section_a || 'Experiments / Results'}
                        </div>
                        <div className="p-2.5 bg-gray-50 border border-gray-200 rounded font-mono text-[11px] text-gray-700 leading-relaxed max-h-40 overflow-y-auto">
                          "{c.passage_a}"
                        </div>
                      </div>

                      {/* Paper B Box */}
                      <div className="p-4 bg-white border border-gray-200 rounded-md space-y-2">
                        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                          <span className="font-semibold text-gray-900 truncate max-w-[240px]">
                            {c.paper_b_title}
                          </span>
                          <span className="text-[10px] font-mono bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                            Page {c.page_b || 1}
                          </span>
                        </div>
                        <div className="text-[10px] text-gray-500">
                          Section: {c.section_b || 'Experiments / Results'}
                        </div>
                        <div className="p-2.5 bg-gray-50 border border-gray-200 rounded font-mono text-[11px] text-gray-700 leading-relaxed max-h-40 overflow-y-auto">
                          "{c.passage_b}"
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

