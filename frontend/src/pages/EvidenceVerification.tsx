import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Search,
  BookOpen,
  ArrowRight,
  FileText,
  Filter,
  Check,
  RefreshCw,
  SlidersHorizontal,
  ExternalLink,
  ChevronRight,
  Copy,
  Plus
} from 'lucide-react';
import { Document, VerificationResultItem } from '../types';
import { api } from '../services/api';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { SearchInput } from '../components/common/SearchInput';
import { Pagination } from '../components/common/Pagination';
import { ModalDialog } from '../components/common/ModalDialog';

interface EvidenceVerificationProps {
  documents: Document[];
  selectedProjectId?: string;
}

export const EvidenceVerification: React.FC<EvidenceVerificationProps> = ({
  documents,
  selectedProjectId,
}) => {
  const [selectedPaperId, setSelectedPaperId] = useState<string>('');
  const [claimText, setClaimText] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<VerificationResultItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Active Inspect Modal
  const [inspectingItem, setInspectingItem] = useState<VerificationResultItem | null>(null);
  const [showVerifyPanel, setShowVerifyPanel] = useState(false);
  const [copiedQuote, setCopiedQuote] = useState(false);

  // Initialize selected paper if available
  useEffect(() => {
    if (documents.length > 0 && !selectedPaperId) {
      setSelectedPaperId(documents[0].id);
    }
  }, [documents, selectedPaperId]);

  // Load verification history from backend SQLite
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const records = await api.getVerificationHistory(selectedPaperId || undefined);
      setHistory(records);
    } catch (e: any) {
      console.error('Failed to load verification history', e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [selectedPaperId]);

  const handleVerify = async (textToVerify?: string) => {
    const claim = textToVerify || claimText;
    if (!claim.trim() || !selectedPaperId || verifying) return;

    setVerifying(true);
    setError(null);
    try {
      const res = await api.verifyClaim(claim, selectedPaperId);
      setInspectingItem(res);
      await loadHistory();
      setClaimText('');
      setShowVerifyPanel(false);
    } catch (e: any) {
      setError(e.message || 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const sampleClaims = [
    {
      label: 'Accurate Metric Benchmark',
      text: 'CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench.',
    },
    {
      label: 'Fabricated Metric (Contradiction)',
      text: 'CentralQ achieves a 99.4% success rate on the Fleet-Dispatch-Bench.',
    },
    {
      label: 'Directional Inversion (Contradiction)',
      text: 'CentralQ increases latency on the Fleet-Dispatch-Bench.',
    },
    {
      label: 'Hallucinated Concept (Insufficient Evidence)',
      text: 'CentralQ utilizes superconducting quantum annealing flux qubits to optimize Josephson junction coupling.',
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Supported':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Supported
          </span>
        );
      case 'Partially Supported':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Partially Supported
          </span>
        );
      case 'Contradicted':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
            <XCircle className="w-3 h-3 text-rose-600" />
            Contradicted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-gray-100 text-gray-700 border border-gray-200">
            <HelpCircle className="w-3 h-3 text-gray-500" />
            Insufficient Evidence
          </span>
        );
    }
  };

  const handleCopyQuote = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedQuote(true);
    setTimeout(() => setCopiedQuote(false), 1800);
  };

  // Filter verification history
  const filteredHistory = history.filter((item) => {
    const matchesSearch =
      searchFilter === '' ||
      item.claim_text.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (item.explanation && item.explanation.toLowerCase().includes(searchFilter.toLowerCase())) ||
      (item.paper_title && item.paper_title.toLowerCase().includes(searchFilter.toLowerCase()));

    const matchesStatus =
      statusFilter === 'all' || item.verification_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.ceil(filteredHistory.length / pageSize);
  const pagedHistory = filteredHistory.slice((page - 1) * pageSize, page * pageSize);
  const selectedDoc = documents.find((d) => d.id === selectedPaperId);

  // Status distribution stats for header
  const supportedCount = history.filter((h) => h.verification_status === 'Supported').length;
  const partialCount = history.filter((h) => h.verification_status === 'Partially Supported').length;
  const contradictedCount = history.filter((h) => h.verification_status === 'Contradicted').length;
  const insufficientCount = history.filter((h) => h.verification_status === 'Insufficient Evidence').length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-900 text-white">
              Ground-Truth Provenance
            </span>
            <span className="text-xs text-gray-400 font-mono">
              Independent Dual-Pass Retrieval &middot; Strict Anti-Hallucination
            </span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight mt-1">
            Evidence Verification Agent
          </h1>
          <p className="text-xs text-gray-500">
            Independently validates claims against source PDF passages. Rejects unsupported assertions and highlights contradictions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowVerifyPanel(!showVerifyPanel)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-2xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Verify New Claim</span>
          </button>
          <button
            type="button"
            onClick={loadHistory}
            disabled={loadingHistory}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded text-xs font-medium transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
            <span>Reload Audit Log</span>
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

      {/* Claim Submission Panel (Collapsible or visible when requested) */}
      {showVerifyPanel && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100">
            <h2 className="text-xs font-bold text-gray-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-slate-800" />
              Submit Factual Proposition for Verification
            </h2>
            <button
              type="button"
              onClick={() => setShowVerifyPanel(false)}
              className="text-gray-400 hover:text-gray-600 text-xs"
            >
              Close Panel
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Target Source Document
              </label>
              <select
                value={selectedPaperId}
                onChange={(e) => setSelectedPaperId(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-white border border-gray-200 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900"
              >
                {documents.length === 0 ? (
                  <option value="">No documents available</option>
                ) : (
                  documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title} ({d.publication_year || 'N/A'})
                    </option>
                  ))
                )}
              </select>
              {selectedDoc && (
                <p className="text-[11px] text-gray-400 mt-1">
                  {selectedDoc.total_pages || 1} pages &middot; {selectedDoc.authors?.[0] || 'Unknown Author'} et al.
                </p>
              )}
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Claim Proposition to Validate
              </label>
              <textarea
                value={claimText}
                onChange={(e) => setClaimText(e.target.value)}
                placeholder="e.g. CentralQ achieves an 89.2% success rate and 28.4% latency reduction..."
                rows={2}
                className="w-full px-3 py-2 text-xs bg-white border border-gray-200 rounded text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-none font-sans"
              />
            </div>
          </div>

          {/* Quick Benchmark Presets */}
          <div>
            <span className="text-[11px] font-medium text-gray-500 mb-1.5 block">
              Or test with preset benchmarks:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {sampleClaims.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setClaimText(sample.text);
                    handleVerify(sample.text);
                  }}
                  disabled={verifying || !selectedPaperId}
                  className="px-2.5 py-1 text-[11px] border border-gray-200 rounded bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer text-left disabled:opacity-50"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <span className="text-[11px] text-gray-400">
              Dual-pass retrieval: BM25 lexical + semantic vectors
            </span>
            <button
              type="button"
              onClick={() => handleVerify()}
              disabled={verifying || !claimText.trim() || !selectedPaperId}
              className="px-4 py-1.5 text-xs font-semibold bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {verifying ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Verifying Passage...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Verify Claim
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Structured Claims Table Section */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-2xs overflow-hidden">
        {/* Table Controls Bar */}
        <div className="p-4 border-b border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            {/* Status Filter */}
            <div className="flex items-center gap-1.5 text-gray-700">
              <Filter className="w-3.5 h-3.5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
              >
                <option value="all">All Verification Statuses</option>
                <option value="Supported">Supported ({supportedCount})</option>
                <option value="Partially Supported">Partially Supported ({partialCount})</option>
                <option value="Contradicted">Contradicted ({contradictedCount})</option>
                <option value="Insufficient Evidence">Insufficient Evidence ({insufficientCount})</option>
              </select>
            </div>

            {/* Document Filter */}
            {documents.length > 0 && (
              <div className="flex items-center gap-1.5 text-gray-700">
                <BookOpen className="w-3.5 h-3.5 text-gray-400" />
                <select
                  value={selectedPaperId}
                  onChange={(e) => {
                    setSelectedPaperId(e.target.value);
                    setPage(1);
                  }}
                  className="bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2.5 focus:outline-none focus:ring-1 focus:ring-slate-900 max-w-[200px] truncate"
                >
                  <option value="">All Uploaded Documents</option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Search Filter */}
          <div className="w-full md:w-64">
            <SearchInput
              value={searchFilter}
              onChange={(v) => {
                setSearchFilter(v);
                setPage(1);
              }}
              placeholder="Search claims & explanations..."
            />
          </div>
        </div>

        {/* Structured Table */}
        {loadingHistory ? (
          <div className="p-12">
            <LoadingState message="Retrieving persistent verification records from SQLite..." />
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="p-16 text-center text-xs text-gray-500 space-y-2">
            <ShieldCheck className="w-8 h-8 text-gray-300 mx-auto" />
            <p className="font-semibold text-gray-700">No Verification Records Found</p>
            <p className="text-gray-400 max-w-sm mx-auto">
              No claims match the active status or search filters. Click "Verify New Claim" above to test research claims.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-gray-600 font-semibold uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Verification Status</th>
                    <th className="py-3 px-4">Claim Proposition</th>
                    <th className="py-3 px-4">Source Research Paper</th>
                    <th className="py-3 px-4 text-center">PDF Page</th>
                    <th className="py-3 px-4 text-center">Audit Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pagedHistory.map((item, idx) => (
                    <tr
                      key={item.id || idx}
                      onClick={() => setInspectingItem(item)}
                      className="hover:bg-gray-50/80 cursor-pointer transition-colors"
                    >
                      {/* Status */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getStatusBadge(item.verification_status)}
                      </td>

                      {/* Claim Proposition */}
                      <td className="py-3 px-4 max-w-sm">
                        <p className="font-medium text-gray-900 line-clamp-2 leading-snug">
                          "{item.claim_text}"
                        </p>
                        {item.explanation && (
                          <p className="text-[11px] text-gray-500 line-clamp-1 mt-0.5">
                            {item.explanation}
                          </p>
                        )}
                      </td>

                      {/* Source Paper */}
                      <td className="py-3 px-4 text-gray-600 max-w-xs truncate" title={item.paper_title || item.source_paper?.title}>
                        <span className="font-medium text-gray-800">
                          {item.paper_title || item.source_paper?.title || 'Target Research Paper'}
                        </span>
                        {item.section_title && (
                          <span className="block text-[10px] text-gray-400 truncate">
                            Section: {item.section_title}
                          </span>
                        )}
                      </td>

                      {/* Page Number */}
                      <td className="py-3 px-4 text-center font-mono text-gray-700 whitespace-nowrap">
                        {item.page_number ? (
                          <span className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">
                            p. {item.page_number}
                          </span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>

                      {/* Validated Finding */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        {item.is_verified_finding ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-medium text-[11px]">
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-700 font-medium text-[11px]">
                            <XCircle className="w-3.5 h-3.5 text-rose-500" />
                            Unverified
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setInspectingItem(item);
                          }}
                          className="px-2.5 py-1 text-xs text-slate-800 hover:text-slate-950 hover:bg-gray-100 rounded font-medium transition-colors"
                        >
                          Inspect Evidence
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="p-3 border-t border-gray-100 bg-gray-50/50">
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        )}
      </div>

      {/* Evidence Provenance Inspector Modal */}
      {inspectingItem && (
        <ModalDialog
          isOpen={Boolean(inspectingItem)}
          onClose={() => setInspectingItem(null)}
          title="Evidence Verification Provenance Inspector"
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            {/* Status and Provenance Badges */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                {getStatusBadge(inspectingItem.verification_status)}
                {inspectingItem.is_verified_finding ? (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Validated Finding
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-800 border border-rose-200">
                    Unsupported / Rejected Finding
                  </span>
                )}
              </div>

              {inspectingItem.page_number && (
                <span className="bg-gray-100 px-2 py-0.5 rounded text-gray-700 font-medium">
                  PDF Page {inspectingItem.page_number}
                  {inspectingItem.section_title ? ` &middot; ${inspectingItem.section_title}` : ''}
                </span>
              )}
            </div>

            {/* Claim Text */}
            <div className="space-y-1">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                Evaluated Claim Proposition
              </span>
              <p className="text-xs font-semibold text-gray-900 bg-gray-50 p-3 rounded border border-gray-200 leading-relaxed font-sans">
                "{inspectingItem.claim_text}"
              </p>
            </div>

            {/* Original Verbatim Passage */}
            {(inspectingItem.original_evidence || inspectingItem.supporting_evidence) && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-emerald-800 uppercase tracking-wider block">
                    Original Verbatim PDF Passage
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      handleCopyQuote(
                        inspectingItem.original_evidence || inspectingItem.supporting_evidence || ''
                      )
                    }
                    className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-800"
                  >
                    {copiedQuote ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-600">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Quote</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="p-3 bg-emerald-50/50 border border-emerald-200 rounded text-xs text-gray-900 leading-relaxed font-mono">
                  "{inspectingItem.original_evidence || inspectingItem.supporting_evidence}"
                </div>
              </div>
            )}

            {/* Counter-Evidence (if present) */}
            {inspectingItem.counter_evidence && (
              <div className="space-y-1">
                <span className="text-[10px] font-semibold text-rose-700 uppercase tracking-wider block">
                  Contradictory Passage in PDF
                </span>
                <div className="p-3 bg-rose-50/50 border border-rose-200 rounded text-xs text-rose-950 leading-relaxed font-mono">
                  "{inspectingItem.counter_evidence}"
                </div>
              </div>
            )}

            {/* Verification Explanation */}
            <div className="space-y-1">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                Objective Verification Explanation
              </span>
              <p className="text-xs text-gray-700 leading-relaxed bg-white p-3 rounded border border-gray-200">
                {inspectingItem.explanation}
              </p>
            </div>

            {/* Source Paper Info */}
            <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500">
              <span className="truncate max-w-md">
                Source Document: {inspectingItem.paper_title || inspectingItem.source_paper?.title || 'N/A'}
              </span>
              <span className="font-mono">
                Similarity Score: {inspectingItem.similarity_score ? (inspectingItem.similarity_score * 100).toFixed(0) : '100'}%
              </span>
            </div>
          </div>
        </ModalDialog>
      )}
    </div>
  );
};
export default EvidenceVerification;
