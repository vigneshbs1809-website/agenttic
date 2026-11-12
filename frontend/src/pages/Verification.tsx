import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  HelpCircle,
  Search,
  Sparkles,
  BookOpen,
  History,
  Loader2,
  ArrowRight,
  FileText
} from 'lucide-react';
import { Document, VerificationResultItem } from '../types';
import { api } from '../services/api';

interface VerificationProps {
  documents: Document[];
}

export const Verification: React.FC<VerificationProps> = ({ documents }) => {
  const [selectedPaperId, setSelectedPaperId] = useState<string>('');
  const [claimText, setClaimText] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [currentResult, setCurrentResult] = useState<VerificationResultItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<VerificationResultItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Set default paper when documents load
  useEffect(() => {
    if (documents.length > 0 && !selectedPaperId) {
      setSelectedPaperId(documents[0].id);
    }
  }, [documents]);

  // Load verification history
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const records = await api.getVerificationHistory(selectedPaperId || undefined);
      setHistory(records);
    } catch (e) {
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
      setCurrentResult(res);
      // Refresh history list
      loadHistory();
    } catch (e: any) {
      setError(e.message || 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const sampleClaims = [
    {
      label: 'Accurate Metric Claim',
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
      label: 'Hallucinated Technical Concept (Insufficient Evidence)',
      text: 'CentralQ utilizes superconducting quantum annealing flux qubits to optimize Josephson junction coupling.',
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Supported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Supported
          </span>
        );
      case 'Partially Supported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <AlertCircle className="w-3.5 h-3.5 text-blue-400" />
            Partially Supported
          </span>
        );
      case 'Contradicted':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            Contradicted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700/50 text-slate-300 border border-slate-600/50">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            Insufficient Evidence
          </span>
        );
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          Evidence Verification Agent
        </h2>
        <p className="text-xs text-slate-400">
          Independently verifies academic assertions against original PDF source passages without LLM self-confirmation
        </p>
      </div>

      {/* Input Form Card */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6 space-y-5 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-1 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Target Research Paper</label>
            <select
              value={selectedPaperId}
              onChange={(e) => setSelectedPaperId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2.5 outline-none focus:border-emerald-500"
            >
              {documents.length === 0 ? (
                <option value="">No papers available</option>
              ) : (
                documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} ({d.publication_year || 'PDF'})
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="md:col-span-2 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Research Claim to Validate</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={claimText}
                onChange={(e) => setClaimText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
                placeholder="e.g. CentralQ achieves an 89.2% success rate on the Fleet-Dispatch-Bench..."
                className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3.5 py-2.5 outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => handleVerify()}
                disabled={verifying || !claimText.trim() || !selectedPaperId}
                className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-semibold rounded-lg text-xs shadow-md transition-all shrink-0"
              >
                {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                {verifying ? 'Verifying...' : 'Verify Claim'}
              </button>
            </div>
          </div>
        </div>

        {/* Example Claims Pills */}
        <div className="pt-2 border-t border-slate-800/80 space-y-2">
          <div className="text-[11px] font-medium text-slate-400">Quick-test Benchmark Claims:</div>
          <div className="flex flex-wrap gap-2">
            {sampleClaims.map((sample, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setClaimText(sample.text);
                  handleVerify(sample.text);
                }}
                className="px-2.5 py-1 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-md text-[11px] text-slate-300 hover:text-emerald-400 text-left transition-all"
              >
                <span className="font-semibold text-slate-400 mr-1.5">[{sample.label}]</span>
                {sample.text.length > 55 ? `${sample.text.substring(0, 55)}...` : sample.text}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Verification Result Showcase */}
      {currentResult && (
        <div
          className={`border rounded-xl p-6 space-y-4 transition-all shadow-md ${
            currentResult.verification_status === 'Supported'
              ? 'bg-emerald-950/20 border-emerald-500/40'
              : currentResult.verification_status === 'Contradicted'
              ? 'bg-rose-950/20 border-rose-500/40'
              : 'bg-slate-900/80 border-slate-700'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {getStatusBadge(currentResult.verification_status)}
                {currentResult.is_verified_finding ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    Verified Literature Finding
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/20">
                    Unverified / Rejected Finding
                  </span>
                )}
              </div>
              <h3 className="text-base font-semibold text-slate-100 pt-1">
                "{currentResult.claim_text}"
              </h3>
            </div>

            <div className="text-right text-xs text-slate-400">
              <div>Source: {currentResult.paper_title}</div>
              {currentResult.page_number && (
                <div className="text-emerald-400 font-medium">Page {currentResult.page_number}</div>
              )}
            </div>
          </div>

          {/* Explanation */}
          <div className="text-xs text-slate-200 leading-relaxed space-y-1">
            <div className="font-semibold text-slate-300">Verification Agent Analysis:</div>
            <p className="text-slate-300 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              {currentResult.explanation}
            </p>
          </div>

          {/* Supporting Evidence Passage */}
          {currentResult.supporting_evidence && (
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                Original Source Passage (Page {currentResult.page_number || 'N/A'})
              </div>
              <blockquote className="text-xs text-slate-300 italic border-l-2 border-emerald-500 pl-3 py-0.5">
                "{currentResult.supporting_evidence}"
              </blockquote>
            </div>
          )}
        </div>
      )}

      {/* Verification History Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <History className="w-4 h-4 text-emerald-400" />
            Persistent Verification Records in SQLite
          </h3>
          <span className="text-xs text-slate-500">{history.length} records</span>
        </div>

        {loadingHistory ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading history...</div>
        ) : history.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 italic">
            No claims verified yet for this paper. Submit a claim above to validate it against the source text.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Claim</th>
                  <th className="py-2.5 px-3">Page</th>
                  <th className="py-2.5 px-3">Finding Verified</th>
                  <th className="py-2.5 px-3">Explanation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {history.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-3 whitespace-nowrap">{getStatusBadge(row.verification_status)}</td>
                    <td className="py-2.5 px-3 font-medium max-w-xs truncate" title={row.claim_text}>
                      {row.claim_text}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap text-slate-400">
                      {row.page_number ? `P. ${row.page_number}` : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {row.is_verified_finding ? (
                        <span className="text-emerald-400 font-semibold">Yes</span>
                      ) : (
                        <span className="text-rose-400 font-semibold">No</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 max-w-sm truncate" title={row.explanation}>
                      {row.explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

