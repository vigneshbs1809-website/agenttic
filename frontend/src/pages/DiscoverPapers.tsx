import React, { useState } from 'react';
import {
  Compass,
  Search,
  Filter,
  ExternalLink,
  Plus,
  CheckCircle2,
  Download,
  BookOpen,
  Globe,
  Loader2,
  Check,
  ChevronDown,
  ChevronUp,
  FileText,
  Layers,
  ArrowUpDown
} from 'lucide-react';
import {
  DiscoveredPaperItem,
  DiscoverySearchResponse,
  ResearchProjectItem
} from '../types';
import { api } from '../services/api';
import { SearchInput } from '../components/common/SearchInput';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { LoadingState } from '../components/common/LoadingState';

interface DiscoverPapersProps {
  projects: ResearchProjectItem[];
  selectedProjectId?: string;
  onPaperAdded?: () => void;
}

export const DiscoverPapers: React.FC<DiscoverPapersProps> = ({
  projects,
  selectedProjectId,
  onPaperAdded
}) => {
  // Query parameters
  const [topic, setTopic] = useState('Multi-Agent Reinforcement Learning Urban Traffic');
  const [author, setAuthor] = useState('');
  const [startYear, setStartYear] = useState<number | undefined>(undefined);
  const [endYear, setEndYear] = useState<number | undefined>(undefined);
  const [openAccessOnly, setOpenAccessOnly] = useState(false);
  const [sortBy, setSortBy] = useState<string>('relevance');

  // Source filters
  const [sources, setSources] = useState<Record<string, boolean>>({
    openalex: true,
    arxiv: true,
    semanticscholar: true,
  });

  // Target project selection
  const [targetProjectId, setTargetProjectId] = useState<string>(selectedProjectId || '');

  // UI state
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DiscoverySearchResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Paper selection & batch add state
  const [selectedPapers, setSelectedPapers] = useState<Record<string, DiscoveredPaperItem>>({});
  const [addingKeys, setAddingKeys] = useState<Record<string, boolean>>({});
  const [addedSuccessMap, setAddedSuccessMap] = useState<Record<string, string>>({});
  const [isBatchAdding, setIsBatchAdding] = useState(false);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<string, boolean>>({});

  const toggleSource = (sourceKey: string) => {
    setSources((prev) => {
      const next = { ...prev, [sourceKey]: !prev[sourceKey] };
      // Keep at least one source checked
      if (!Object.values(next).some(Boolean)) {
        return prev;
      }
      return next;
    });
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim()) return;

    setIsSearching(true);
    setErrorMsg(null);
    setSelectedPapers({});

    const selectedSourcesList = Object.keys(sources).filter((k) => sources[k]);

    try {
      const res = await api.discoverPapers({
        topic: topic.trim(),
        author: author.trim() || undefined,
        year_start: startYear,
        year_end: endYear,
        open_access_only: openAccessOnly,
        sources: selectedSourcesList,
        limit_per_source: 12,
        sort_by: sortBy
      });
      setSearchResults(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Academic search failed across external sources.');
    } finally {
      setIsSearching(false);
    }
  };

  const getPaperKey = (paper: DiscoveredPaperItem, idx: number): string => {
    return paper.doi || paper.id || `${paper.title.substring(0, 30)}_${paper.year || idx}`;
  };

  // Toggle selection for a single paper
  const toggleSelectPaper = (paper: DiscoveredPaperItem, key: string) => {
    setSelectedPapers((prev) => {
      const next = { ...prev };
      if (next[key]) {
        delete next[key];
      } else {
        next[key] = paper;
      }
      return next;
    });
  };

  // Select all or deselect all
  const toggleSelectAll = () => {
    if (!searchResults || !searchResults.papers) return;
    const allSelected = searchResults.papers.every((p, idx) => selectedPapers[getPaperKey(p, idx)]);
    if (allSelected) {
      setSelectedPapers({});
    } else {
      const all: Record<string, DiscoveredPaperItem> = {};
      searchResults.papers.forEach((p, idx) => {
        all[getPaperKey(p, idx)] = p;
      });
      setSelectedPapers(all);
    }
  };

  // Add a single paper to project
  const handleAddSinglePaper = async (paper: DiscoveredPaperItem, key: string) => {
    const projId = targetProjectId || (projects.length > 0 ? projects[0].id : '');
    if (!projId) {
      setErrorMsg('Please select a target research project first.');
      return;
    }

    setAddingKeys((prev) => ({ ...prev, [key]: true }));
    setErrorMsg(null);
    try {
      const res = await api.addDiscoveredPaper({
        project_id: projId,
        paper: paper,
        download_pdf: true,
        process_document: true,
      });
      setAddedSuccessMap((prev) => ({
        ...prev,
        [key]: res.pdf_downloaded ? 'PDF Downloaded & Processed' : 'Metadata Indexed'
      }));
      if (onPaperAdded) onPaperAdded();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to add paper to project');
    } finally {
      setAddingKeys((prev) => ({ ...prev, [key]: false }));
    }
  };

  // Batch add all selected papers
  const handleBatchAddSelected = async () => {
    const papersToAdd = Object.values(selectedPapers);
    if (papersToAdd.length === 0) return;

    const projId = targetProjectId || (projects.length > 0 ? projects[0].id : '');
    if (!projId) {
      setErrorMsg('Please select a target research project first.');
      return;
    }

    setIsBatchAdding(true);
    setErrorMsg(null);

    let successCount = 0;
    for (const paper of papersToAdd) {
      const key = getPaperKey(paper, 0);
      try {
        const res = await api.addDiscoveredPaper({
          project_id: projId,
          paper: paper,
          download_pdf: true,
          process_document: true,
        });
        setAddedSuccessMap((prev) => ({
          ...prev,
          [key]: res.pdf_downloaded ? 'PDF Downloaded & Processed' : 'Metadata Indexed'
        }));
        successCount++;
      } catch (err: any) {
        console.warn(`Failed to add paper: ${paper.title}`, err);
      }
    }

    setIsBatchAdding(false);
    setSelectedPapers({});
    if (onPaperAdded) onPaperAdded();
  };

  const selectedCount = Object.keys(selectedPapers).length;
  const allPapers = searchResults?.papers || [];
  const allSelected = allPapers.length > 0 && allPapers.every((p, idx) => selectedPapers[getPaperKey(p, idx)]);

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <Compass className="w-5 h-5 text-slate-800" />
            Academic Paper Discovery Workspace
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Query arXiv, OpenAlex, and Semantic Scholar concurrently. Factual paper metadata ground-truthing with open-access PDF download.
          </p>
        </div>

        {/* Target Project Dropdown */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <label className="text-xs font-medium text-gray-600 whitespace-nowrap">
            Target Project:
          </label>
          <select
            value={targetProjectId}
            onChange={(e) => setTargetProjectId(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900 max-w-xs truncate"
          >
            {projects.length === 0 ? (
              <option value="">No projects created yet</option>
            ) : (
              projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Discovery Query & Multi-Filter Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-xs space-y-4">
        <form onSubmit={handleSearch} className="space-y-3.5">
          {/* Main Topic Input & Search Button */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Enter research topic, problem statement, or keywords..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={isSearching || !topic.trim()}
              className="px-4 py-2 text-xs font-semibold bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shrink-0"
            >
              {isSearching ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Discovering Literature...
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  Search Academic Sources
                </>
              )}
            </button>
          </div>

          {/* Filter Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-1 text-xs">
            {/* Author Filter */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                Author Filter
              </label>
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="e.g. Bengio, Vaswani..."
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>

            {/* Publication Year Range */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                Publication Year Range
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={1990}
                  max={2030}
                  value={startYear || ''}
                  onChange={(e) => setStartYear(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="From"
                  className="w-full px-2 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900 font-mono"
                />
                <span className="text-gray-400">&ndash;</span>
                <input
                  type="number"
                  min={1990}
                  max={2030}
                  value={endYear || ''}
                  onChange={(e) => setEndYear(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="To"
                  className="w-full px-2 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900 font-mono"
                />
              </div>
            </div>

            {/* Relevance & Ordering Sorting */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                Relevance Sorting
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900"
              >
                <option value="relevance">Relevance Score</option>
                <option value="year_desc">Newest First (Year &darr;)</option>
                <option value="year_asc">Oldest First (Year &uarr;)</option>
                <option value="citations_desc">Most Cited First</option>
              </select>
            </div>

            {/* Open Access Only Filter */}
            <div className="flex flex-col justify-end">
              <label className="inline-flex items-center gap-2 cursor-pointer pb-2">
                <input
                  type="checkbox"
                  checked={openAccessOnly}
                  onChange={(e) => setOpenAccessOnly(e.target.checked)}
                  className="rounded border-gray-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="text-xs text-gray-700 font-medium">
                  Open-Access PDFs Only
                </span>
              </label>
            </div>
          </div>

          {/* Academic Source Filter Checkboxes */}
          <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-gray-100 text-xs">
            <span className="text-gray-500 font-semibold text-[11px] uppercase tracking-wider">
              Sources:
            </span>
            <label className="inline-flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={sources.arxiv}
                onChange={() => toggleSource('arxiv')}
                className="rounded border-gray-300 text-slate-900"
              />
              <span className="text-gray-700 font-mono text-[11px]">arXiv API</span>
            </label>
            <label className="inline-flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={sources.openalex}
                onChange={() => toggleSource('openalex')}
                className="rounded border-gray-300 text-slate-900"
              />
              <span className="text-gray-700 font-mono text-[11px]">OpenAlex</span>
            </label>
            <label className="inline-flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={sources.semanticscholar}
                onChange={() => toggleSource('semanticscholar')}
                className="rounded border-gray-300 text-slate-900"
              />
              <span className="text-gray-700 font-mono text-[11px]">Semantic Scholar</span>
            </label>
          </div>
        </form>
      </div>

      {/* Search Status & Batch Action Bar */}
      {searchResults && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-900">
              Found {searchResults.total_found} verified academic papers
            </span>
            <span className="text-gray-400">&bull;</span>
            <span className="text-gray-500">
              Sources queried: {searchResults.sources_queried.join(', ')}
            </span>
          </div>

          {selectedCount > 0 && (
            <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
              <span className="font-medium text-slate-900">
                {selectedCount} selected
              </span>
              <button
                type="button"
                onClick={handleBatchAddSelected}
                disabled={isBatchAdding}
                className="px-3 py-1.5 bg-slate-900 text-white rounded text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
              >
                {isBatchAdding ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Adding {selectedCount} Papers...
                  </>
                ) : (
                  <>
                    <Plus className="w-3.5 h-3.5" />
                    Add Selected to Project
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Results List: Clean Academic Rows */}
      {isSearching ? (
        <div className="p-12 bg-white border border-gray-200 rounded-lg">
          <LoadingState message="Querying academic repositories and computing relevance ranking..." />
        </div>
      ) : !searchResults ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center text-xs text-gray-500">
          Search for a research topic or methodology above to discover academic papers with verified metadata.
        </div>
      ) : searchResults.papers.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center text-xs text-gray-500">
          No papers found matching the specified topic and filter criteria. Try broadening your keywords.
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-xs overflow-hidden">
          {/* Header Row with Select All */}
          <div className="p-3.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between text-xs text-gray-600 font-medium">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleSelectAll}
                className="rounded border-gray-300 text-slate-900 cursor-pointer"
                title="Select all papers"
              />
              <span>Paper Title & Academic Details</span>
            </div>
            <div className="flex items-center gap-6">
              <span className="hidden sm:inline">Year & Sources</span>
              <span>Actions</span>
            </div>
          </div>

          {/* Paper Rows */}
          <div className="divide-y divide-gray-100">
            {searchResults.papers.map((paper, idx) => {
              const key = getPaperKey(paper, idx);
              const isSelected = Boolean(selectedPapers[key]);
              const isAdding = Boolean(addingKeys[key]);
              const successStatus = addedSuccessMap[key];
              const isAbstractExpanded = Boolean(expandedAbstracts[key]);

              return (
                <div
                  key={key}
                  className={`p-4 transition-colors hover:bg-gray-50/60 ${
                    isSelected ? 'bg-slate-50/50' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox */}
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectPaper(paper, key)}
                      className="mt-1 rounded border-gray-300 text-slate-900 cursor-pointer"
                    />

                    {/* Paper Content */}
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h2 className="text-sm font-semibold text-gray-900 hover:text-slate-900 leading-snug">
                            {paper.primary_url || paper.url ? (
                              <a
                                href={paper.primary_url || paper.url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:underline flex items-center gap-1.5"
                              >
                                {paper.title}
                                <ExternalLink className="w-3 h-3 text-gray-400 shrink-0 inline" />
                              </a>
                            ) : (
                              paper.title
                            )}
                          </h2>

                          {/* Authors & Venue */}
                          <p className="text-xs text-gray-500 mt-0.5">
                            {paper.authors && paper.authors.length > 0
                              ? paper.authors.join(', ')
                              : 'Authors Not Reported'}
                            {paper.venue ? ` &bull; ${paper.venue}` : ''}
                          </p>
                        </div>

                        {/* Year & Relevance */}
                        <div className="text-right shrink-0 text-xs">
                          <span className="font-mono font-semibold text-gray-900">
                            {paper.year || '—'}
                          </span>
                          {paper.relevance_score !== undefined && paper.relevance_score > 0 && (
                            <div className="text-[10px] text-gray-400 font-mono">
                              Rel: {(paper.relevance_score * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Badges: Sources, Open Access, Citations */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        {paper.is_open_access ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Open Access PDF
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">
                            Metadata Only
                          </span>
                        )}

                        {paper.citation_count !== undefined && paper.citation_count !== null && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-gray-50 border border-gray-200 text-gray-600">
                            {paper.citation_count} citations
                          </span>
                        )}

                        {paper.sources &&
                          paper.sources.map((src) => (
                            <span
                              key={src}
                              className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-50 border border-slate-200 text-slate-700 uppercase"
                            >
                              {src}
                            </span>
                          ))}

                        {paper.doi && (
                          <span className="text-[10px] font-mono text-gray-400 truncate max-w-xs">
                            DOI: {paper.doi}
                          </span>
                        )}
                      </div>

                      {/* Expandable Abstract */}
                      {paper.abstract && (
                        <div className="pt-1.5 text-xs">
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedAbstracts((prev) => ({
                                ...prev,
                                [key]: !prev[key]
                              }))
                            }
                            className="text-[11px] text-slate-800 hover:text-slate-950 font-medium flex items-center gap-1"
                          >
                            {isAbstractExpanded ? (
                              <>
                                <ChevronUp className="w-3 h-3" /> Hide Abstract
                              </>
                            ) : (
                              <>
                                <ChevronDown className="w-3 h-3" /> View Abstract
                              </>
                            )}
                          </button>

                          {isAbstractExpanded && (
                            <p className="mt-1.5 p-2.5 bg-gray-50 border border-gray-200 rounded text-xs text-gray-700 leading-relaxed font-sans">
                              {paper.abstract}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action: Add to Project */}
                    <div className="shrink-0 pl-2">
                      {successStatus ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <Check className="w-3 h-3 text-emerald-600" />
                          {successStatus}
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleAddSinglePaper(paper, key)}
                          disabled={isAdding}
                          className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors flex items-center gap-1"
                        >
                          {isAdding ? (
                            <>
                              <span className="w-3 h-3 border-2 border-slate-800/30 border-t-slate-800 rounded-full animate-spin" />
                              Adding...
                            </>
                          ) : (
                            <>
                              <Plus className="w-3 h-3" />
                              Add to Project
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
export default DiscoverPapers;
