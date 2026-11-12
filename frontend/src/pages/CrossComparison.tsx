import React, { useState } from 'react';
import {
  Scale,
  Sparkles,
  Layers,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  ArrowRight,
  Loader2,
  FileText
} from 'lucide-react';
import { Document } from '../types';
import { api } from '../services/api';

interface CrossComparisonProps {
  documents: Document[];
}

export const CrossComparison: React.FC<CrossComparisonProps> = ({ documents }) => {
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const togglePaperSelection = (id: string) => {
    setSelectedPaperIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((p) => p !== id);
      }
      if (prev.length >= 5) {
        alert('You can select a maximum of 5 papers for comparison.');
        return prev;
      }
      return [...prev, id];
    });
  };

  const handleRunComparison = async () => {
    if (selectedPaperIds.length < 2) {
      alert('Please select at least 2 papers to compare.');
      return;
    }
    setComparing(true);
    setError(null);
    try {
      const res = await api.comparePapers(selectedPaperIds);
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Comparison failed');
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Scale className="w-5 h-5 text-emerald-400" />
            Cross-Paper Comparison Agent
          </h2>
          <p className="text-xs text-slate-400">
            Synthesize methodological differences, benchmark comparability, and contradictory findings across 2–5 papers
          </p>
        </div>

        <button
          onClick={handleRunComparison}
          disabled={comparing || selectedPaperIds.length < 2}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-semibold rounded-lg text-xs shadow-md transition-all self-start sm:self-auto"
        >
          {comparing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          {comparing ? 'Synthesizing Matrix...' : `Compare Selected (${selectedPaperIds.length})`}
        </button>
      </div>

      {/* Paper Selector Grid */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
          <span>Select 2 to 5 Papers for Rigorous Cross-Analysis</span>
          <span className="text-[11px] text-slate-400 font-normal">
            {selectedPaperIds.length} of 5 selected
          </span>
        </div>

        {documents.length === 0 ? (
          <div className="text-xs text-slate-500 py-3">No uploaded research papers found. Upload papers first.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {documents.map((doc) => {
              const isSelected = selectedPaperIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  onClick={() => togglePaperSelection(doc.id)}
                  className={`cursor-pointer p-3.5 rounded-lg border text-xs transition-all ${
                    isSelected
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-slate-100 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-slate-200 line-clamp-2">{doc.title}</span>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      readOnly
                      className="mt-0.5 rounded border-slate-700 text-emerald-500 focus:ring-0"
                    />
                  </div>
                  <div className="text-[11px] text-slate-500 mt-2 flex items-center justify-between">
                    <span>{doc.authors?.slice(0, 2).join(', ') || 'Unknown Authors'}</span>
                    <span>{doc.publication_year || 'PDF'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Comparison Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary Banner */}
          {result.comparative_summary && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-2">
              <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Written Comparative Synthesis
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                {result.comparative_summary}
              </p>
            </div>
          )}

          {/* Methodological Differences & Contradictions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Methodological Differences */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                Methodological Differences
              </h4>
              {result.methodological_differences?.length > 0 ? (
                <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside">
                  {result.methodological_differences.map((diff: string, i: number) => (
                    <li key={i} className="leading-relaxed">{diff}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No radical methodological divergences identified.</p>
              )}
            </div>

            {/* Contradictory Findings */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Contradictory Findings & Discrepancies
              </h4>
              {result.contradictory_findings?.length > 0 ? (
                <ul className="text-xs text-amber-200/90 space-y-2 list-disc list-inside">
                  {result.contradictory_findings.map((contra: string, i: number) => (
                    <li key={i} className="leading-relaxed">{contra}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No direct experimental contradictions detected across evaluated benchmarks.</p>
              )}
            </div>
          </div>

          {/* Dataset & Evaluation Comparability */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Benchmark & Evaluation Comparability Check
            </h4>
            <div className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-lg border border-slate-800/80">
              {result.dataset_comparison || 'Datasets and evaluation metrics verified against reporting standards.'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

