import React, { useState, useEffect } from 'react';
import {
  Target,
  RefreshCw,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronRight,
  BookOpen,
  Info,
  ShieldCheck,
  Sparkles,
  Edit3,
  Check,
  X,
  Trash2,
  FileText,
  Search,
  ExternalLink
} from 'lucide-react';
import { ResearchGapItem, ResearchProjectItem } from '../types';
import { api } from '../services/api';
import { SearchInput } from '../components/common/SearchInput';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LoadingState } from '../components/common/LoadingState';
import { ModalDialog } from '../components/common/ModalDialog';

interface ResearchGapsProps {
  projects?: ResearchProjectItem[];
  selectedProjectId?: string;
}

export const ResearchGaps: React.FC<ResearchGapsProps> = ({
  projects = [],
  selectedProjectId: initialProjectId = '',
}) => {
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedMethod, setSelectedMethod] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [gaps, setGaps] = useState<ResearchGapItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Inspector and Edit modals
  const [inspectingGap, setInspectingGap] = useState<ResearchGapItem | null>(null);
  const [editingGap, setEditingGap] = useState<ResearchGapItem | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editDirection, setEditDirection] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadGaps(selectedProjectId);
    } else if (projects.length > 0) {
      setSelectedProjectId(projects[0].id);
      loadGaps(projects[0].id);
    } else {
      loadAllGaps();
    }
  }, [selectedProjectId, projects]);

  const loadCategories = async () => {
    try {
      const cats = await api.getGapCategories();
      setCategories(cats);
    } catch (e) {
      console.warn('Could not load categories', e);
    }
  };

  const loadGaps = async (pId: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getAllGaps({
        projectId: pId && pId !== 'all' ? pId : undefined,
        gapType: selectedCategory !== 'all' ? selectedCategory : undefined,
        method: selectedMethod !== 'all' ? selectedMethod : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
      });
      setGaps(res.gaps || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load research gaps');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAllGaps = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getAllGaps({
        gapType: selectedCategory !== 'all' ? selectedCategory : undefined,
        method: selectedMethod !== 'all' ? selectedMethod : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
      });
      setGaps(res.gaps || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load research gaps');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDiscoverGaps = async () => {
    if (!selectedProjectId || selectedProjectId === 'all') {
      setErrorMsg('Please select a specific project first to run the Gap Discovery Agent.');
      return;
    }
    setIsDiscovering(true);
    setErrorMsg(null);
    try {
      const res = await api.discoverProjectGaps(selectedProjectId, {
        force_rediscover: true,
      });
      setGaps(res.gaps || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Gap discovery failed');
    } finally {
      setIsDiscovering(false);
    }
  };

  // Status updates (Approve / Reject)
  const handleUpdateStatus = async (gapId: string, newStatus: 'approved' | 'rejected' | 'open') => {
    try {
      await api.updateGap(gapId, { status: newStatus });
      setGaps((prev) =>
        prev.map((g) => (g.id === gapId ? { ...g, status: newStatus } : g))
      );
      if (inspectingGap && inspectingGap.id === gapId) {
        setInspectingGap({ ...inspectingGap, status: newStatus });
      }
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to update gap status to ${newStatus}`);
    }
  };

  // Edit Gap
  const handleStartEdit = (gap: ResearchGapItem) => {
    setEditingGap(gap);
    setEditTitle(gap.title);
    setEditDesc(gap.description);
    setEditDirection(gap.suggested_direction || '');
  };

  const handleSaveEdit = async () => {
    if (!editingGap) return;
    setIsSavingEdit(true);
    try {
      const updated = await api.updateGap(editingGap.id, {
        title: editTitle,
        description: editDesc,
        suggested_direction: editDirection,
      });
      setGaps((prev) =>
        prev.map((g) =>
          g.id === editingGap.id
            ? {
                ...g,
                title: editTitle,
                description: editDesc,
                suggested_direction: editDirection,
              }
            : g
        )
      );
      if (inspectingGap && inspectingGap.id === editingGap.id) {
        setInspectingGap({
          ...inspectingGap,
          title: editTitle,
          description: editDesc,
          suggested_direction: editDirection,
        });
      }
      setEditingGap(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save gap edits');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDeleteGap = async (gapId: string) => {
    if (!confirm('Are you sure you want to delete this research gap record?')) return;
    try {
      await api.deleteGap(gapId);
      setGaps((prev) => prev.filter((g) => g.id !== gapId));
      if (inspectingGap && inspectingGap.id === gapId) {
        setInspectingGap(null);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete gap');
    }
  };

  const filteredGaps = gaps.filter((g) => {
    if (selectedCategory !== 'all' && (g.category || (g as any).gap_type) !== selectedCategory) return false;
    if (selectedMethod !== 'all' && g.identification_method !== selectedMethod) return false;
    if (selectedStatus !== 'all' && (g.status || 'open').toLowerCase() !== selectedStatus.toLowerCase()) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = g.title.toLowerCase().includes(q);
      const matchDesc = g.description.toLowerCase().includes(q);
      return matchTitle || matchDesc;
    }
    return true;
  });

  const getStatusBadge = (statusStr: string) => {
    const s = (statusStr || 'open').toLowerCase();
    switch (s) {
      case 'approved':
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-800 border border-rose-200">
            <XCircle className="w-3 h-3 text-rose-600" />
            Rejected
          </span>
        );
      case 'addressed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-800 border border-blue-200">
            <ShieldCheck className="w-3 h-3 text-blue-600" />
            Addressed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-700 border border-gray-200">
            Open
          </span>
        );
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-purple-50 text-purple-800 border border-purple-200">
              Central Platform Contribution
            </span>
            <span className="text-xs text-gray-400 font-mono">
              Explicit Author Stated &middot; Implicit Cross-Paper Inferred
            </span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight mt-1">
            Research Gap Discovery
          </h1>
          <p className="text-xs text-gray-500">
            Systematic identification of unaddressed research opportunities backed by verbatim academic citations and confidence justifications.
          </p>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDiscoverGaps}
            disabled={isDiscovering || isLoading || !selectedProjectId || selectedProjectId === 'all'}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-2xs transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin' : ''}`} />
            <span>{isDiscovering ? 'Discovering Gaps...' : 'Discover Research Gaps'}</span>
          </button>
        </div>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Controls Bar: Multi-Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Project Selector */}
          {projects.length > 0 && (
            <div className="flex items-center gap-1.5 text-gray-700">
              <BookOpen className="w-3.5 h-3.5 text-gray-400" />
              <select
                value={selectedProjectId}
                onChange={(e) => {
                  setSelectedProjectId(e.target.value);
                  loadGaps(e.target.value);
                }}
                className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900 max-w-[200px] truncate"
              >
                <option value="all">All Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="h-4 w-px bg-gray-200 hidden sm:block" />

          {/* Category Filter */}
          <div className="flex items-center gap-1.5 text-gray-700">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
              }}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="all">All 10 Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Identification Method */}
          <div className="flex items-center gap-1.5 text-gray-700">
            <select
              value={selectedMethod}
              onChange={(e) => setSelectedMethod(e.target.value)}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="all">All Methods</option>
              <option value="explicit_author_stated">Explicit (Author-Stated)</option>
              <option value="implicit_system_inferred">Implicit (System-Inferred)</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-gray-700">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="addressed">Addressed</option>
            </select>
          </div>
        </div>

        {/* Search Input */}
        <div className="w-full sm:w-64">
          <SearchInput
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search gaps by title or text..."
          />
        </div>
      </div>

      {/* Main Research Gaps Table */}
      {isLoading ? (
        <LoadingState message="Querying persistent research gaps and evidence passages from SQLite..." />
      ) : filteredGaps.length === 0 ? (
        <div className="p-16 text-center bg-white border border-gray-200 rounded-lg space-y-3">
          <Target className="w-10 h-10 text-gray-300 mx-auto" />
          <h3 className="text-sm font-semibold text-gray-800">No Research Gaps Found</h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            No research gaps match the active filters. Select a project and click "Discover Research Gaps" to analyze literature and surface gaps.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-gray-600 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Gap Title & ID</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Supporting Papers</th>
                  <th className="py-3 px-4 text-center">Confidence Score</th>
                  <th className="py-3 px-4 text-center">Evidence Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredGaps.map((gap) => {
                  const cat = gap.category || (gap as any).gap_type || 'Methodological';
                  const isExplicit = gap.identification_method === 'explicit_author_stated';
                  const confPct = Math.round((gap.confidence_score || 0.8) * 100);
                  const paperCount = gap.supporting_paper_count || gap.evidence?.length || 1;

                  return (
                    <tr
                      key={gap.id}
                      onClick={() => setInspectingGap(gap)}
                      className="hover:bg-gray-50/80 cursor-pointer transition-colors"
                    >
                      {/* Gap Title */}
                      <td className="py-3 px-4 max-w-md">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                isExplicit
                                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                  : 'bg-purple-50 text-purple-700 border border-purple-200'
                              }`}
                            >
                              {isExplicit ? 'Explicit' : 'Implicit'}
                            </span>
                            <span className="font-mono text-[10px] text-gray-400 truncate max-w-[120px]">
                              {gap.id}
                            </span>
                          </div>
                          <p className="font-semibold text-gray-900 leading-snug line-clamp-1 hover:text-slate-800">
                            {gap.title}
                          </p>
                          <p className="text-[11px] text-gray-500 line-clamp-1">
                            {gap.description}
                          </p>
                        </div>
                      </td>

                      {/* Category */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-800 border border-gray-200 uppercase tracking-tight">
                          {cat}
                        </span>
                      </td>

                      {/* Supporting Papers */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="text-gray-700">
                          <span className="font-medium text-gray-900">{paperCount}</span>
                          <span className="text-gray-500 text-[11px]"> paper{paperCount !== 1 ? 's' : ''}</span>
                        </div>
                        {gap.evidence && gap.evidence[0] && (
                          <p className="text-[10px] text-gray-400 truncate max-w-[180px]">
                            {gap.evidence[0].paper_title}
                          </p>
                        )}
                      </td>

                      {/* Confidence Score */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <div className="inline-flex items-center gap-1.5">
                          <div className="w-12 bg-gray-200 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-slate-900 h-1.5 rounded-full"
                              style={{ width: `${confPct}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs font-semibold text-gray-800">
                            {confPct}%
                          </span>
                        </div>
                      </td>

                      {/* Evidence Status */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        {getStatusBadge(gap.status)}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div
                          className="inline-flex items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            onClick={() => handleUpdateStatus(gap.id, 'approved')}
                            title="Approve Research Gap"
                            className="p-1 text-gray-400 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleUpdateStatus(gap.id, 'rejected')}
                            title="Reject Research Gap"
                            className="p-1 text-gray-400 hover:text-rose-700 hover:bg-rose-50 rounded transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleStartEdit(gap)}
                            title="Edit Research Gap"
                            className="p-1 text-gray-400 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-3 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between text-[11px] text-gray-500">
            <span>Showing {filteredGaps.length} research gaps</span>
            <span>Click any row to inspect passages, counter-evidence, and suggested directions</span>
          </div>
        </div>
      )}

      {/* Gap Detail Inspector Modal */}
      {inspectingGap && (
        <ModalDialog
          isOpen={Boolean(inspectingGap)}
          onClose={() => setInspectingGap(null)}
          title="Research Gap Detail & Ground-Truth Provenance"
          maxWidth="2xl"
        >
          <div className="space-y-5 text-xs">
            {/* Header Metadata */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-800 border border-gray-200 uppercase">
                  {inspectingGap.category || (inspectingGap as any).gap_type}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    inspectingGap.identification_method === 'explicit_author_stated'
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : 'bg-purple-50 text-purple-700 border border-purple-200'
                  }`}
                >
                  {inspectingGap.identification_method === 'explicit_author_stated'
                    ? 'Explicit (Author-Stated)'
                    : 'Implicit (System-Inferred)'}
                </span>
                {getStatusBadge(inspectingGap.status)}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleUpdateStatus(inspectingGap.id, 'approved')}
                  className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded font-medium text-[11px] flex items-center gap-1 transition-colors"
                >
                  <Check className="w-3 h-3 text-emerald-600" />
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => handleUpdateStatus(inspectingGap.id, 'rejected')}
                  className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-200 rounded font-medium text-[11px] flex items-center gap-1 transition-colors"
                >
                  <X className="w-3 h-3 text-rose-600" />
                  Reject
                </button>
                <button
                  type="button"
                  onClick={() => handleStartEdit(inspectingGap)}
                  className="px-2.5 py-1 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 rounded font-medium text-[11px] flex items-center gap-1 transition-colors"
                >
                  <Edit3 className="w-3 h-3" />
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteGap(inspectingGap.id)}
                  className="p-1 text-gray-400 hover:text-rose-600 rounded transition-colors"
                  title="Delete Gap"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Gap Title & Explanation */}
            <div className="space-y-2">
              <h2 className="text-base font-bold text-gray-900 leading-snug">
                {inspectingGap.title}
              </h2>
              <div>
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
                  Detailed Explanation
                </span>
                <p className="text-xs text-gray-800 leading-relaxed bg-gray-50 p-3 rounded border border-gray-200">
                  {inspectingGap.description}
                </p>
              </div>
            </div>

            {/* Suggested Actionable Direction */}
            {inspectingGap.suggested_direction && (
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded space-y-1">
                <span className="font-semibold text-slate-900 block text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-slate-700" />
                  Suggested Actionable Research Direction:
                </span>
                <p className="text-gray-800 leading-relaxed font-sans">
                  {inspectingGap.suggested_direction}
                </p>
              </div>
            )}

            {/* Confidence Score & Justification */}
            <div className="p-3 bg-white border border-gray-200 rounded space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-700 uppercase tracking-wider text-[10px]">
                  Confidence Score: {Math.round((inspectingGap.confidence_score || 0.8) * 100)}%
                </span>
                <span className="text-[10px] text-gray-400">
                  Transparency Notice: Not a statistically validated probability
                </span>
              </div>
              {inspectingGap.confidence_justification && (
                <p className="text-[11px] text-gray-600 leading-relaxed">
                  {inspectingGap.confidence_justification}
                </p>
              )}
            </div>

            {/* Original Supporting Literature Passages with Page Numbers */}
            <div className="space-y-2 pt-1">
              <span className="font-semibold text-gray-800 block text-[11px] uppercase tracking-wider">
                Original Supporting Literature Passages ({inspectingGap.evidence?.length || 0}):
              </span>
              {inspectingGap.evidence && inspectingGap.evidence.length > 0 ? (
                <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                  {inspectingGap.evidence
                    .filter((ev) => !ev.is_counter_evidence)
                    .map((ev, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-3 bg-gray-50 border border-gray-200 rounded space-y-1 font-mono text-[11px]"
                      >
                        <div className="flex items-center justify-between font-sans text-gray-800 font-medium">
                          <span className="truncate max-w-sm">{ev.paper_title}</span>
                          {ev.page_number && (
                            <span className="bg-white px-2 py-0.5 rounded text-[10px] text-gray-700 border border-gray-200">
                              Page {ev.page_number}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-800 leading-relaxed">"{ev.quote_or_excerpt || ev.original_text}"</p>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-[11px] text-gray-400 italic">No direct excerpts attached.</p>
              )}
            </div>

            {/* Counter-Evidence (if present) */}
            {inspectingGap.evidence && inspectingGap.evidence.some((ev) => ev.is_counter_evidence) && (
              <div className="space-y-2 pt-1">
                <span className="font-semibold text-rose-700 block text-[11px] uppercase tracking-wider">
                  Counter-Evidence / Conflicting Passages:
                </span>
                <div className="space-y-2">
                  {inspectingGap.evidence
                    .filter((ev) => ev.is_counter_evidence)
                    .map((ev, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-3 bg-rose-50/50 border border-rose-200 rounded space-y-1 font-mono text-[11px]"
                      >
                        <div className="flex items-center justify-between font-sans text-rose-900 font-medium">
                          <span className="truncate max-w-sm">{ev.paper_title}</span>
                          {ev.page_number && (
                            <span className="bg-white px-2 py-0.5 rounded text-[10px] text-rose-800 border border-rose-200">
                              Page {ev.page_number}
                            </span>
                          )}
                        </div>
                        <p className="text-rose-900 leading-relaxed">"{ev.quote_or_excerpt || ev.original_text}"</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </ModalDialog>
      )}

      {/* Edit Gap Modal */}
      {editingGap && (
        <ModalDialog
          isOpen={Boolean(editingGap)}
          onClose={() => setEditingGap(null)}
          title="Edit Research Gap Record"
          maxWidth="xl"
        >
          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Gap Title
              </label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Detailed Explanation / Description
              </label>
              <textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-none font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Suggested Research Direction
              </label>
              <textarea
                value={editDirection}
                onChange={(e) => setEditDirection(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-none font-sans"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setEditingGap(null)}
                className="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded text-xs font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={isSavingEdit || !editTitle.trim()}
                className="px-4 py-1.5 bg-slate-900 text-white rounded text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
              >
                {isSavingEdit ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </button>
            </div>
          </div>
        </ModalDialog>
      )}
    </div>
  );
};
export default ResearchGaps;
