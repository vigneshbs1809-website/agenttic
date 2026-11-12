import React, { useState } from 'react';
import {
  Scale,
  Check,
  Plus,
  RefreshCw,
  Download,
  Copy,
  AlertTriangle,
  FileText,
  Info,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Quote,
  FileSpreadsheet
} from 'lucide-react';
import {
  Document,
  CrossPaperComparisonReport,
  MatrixRow,
  MatrixCell,
  ComparabilityAssessment
} from '../types';
import { api } from '../services/api';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LoadingState } from '../components/common/LoadingState';

interface ComparativeAnalysisProps {
  documents: Document[];
}

export const ComparativeAnalysis: React.FC<ComparativeAnalysisProps> = ({ documents }) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(
    documents.slice(0, 2).map((d) => d.id)
  );
  const [comparison, setComparison] = useState<CrossPaperComparisonReport | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [expandedCellEvidence, setExpandedCellEvidence] = useState<Record<string, boolean>>({});

  const toggleSelectPaper = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((pId) => pId !== id);
      }
      if (prev.length >= 5) {
        alert('You can select a maximum of 5 papers for simultaneous head-to-head comparison.');
        return prev;
      }
      return [...prev, id];
    });
  };

  const handleRunComparison = async (forceRegenerate = false) => {
    if (selectedIds.length < 2) {
      setErrorMsg('Please select between 2 and 5 research papers to compare.');
      return;
    }
    if (selectedIds.length > 5) {
      setErrorMsg('Maximum 5 research papers can be compared simultaneously.');
      return;
    }

    setIsComparing(true);
    setErrorMsg(null);
    try {
      const res = await api.comparePapers(selectedIds);
      // res returns { comparison_id, report, message } or direct report
      const rep: CrossPaperComparisonReport = res.report || res;
      setComparison(rep);
    } catch (err: any) {
      setErrorMsg(err.message || 'Cross-paper comparison failed.');
    } finally {
      setIsComparing(false);
    }
  };

  const handleCopyMarkdown = () => {
    const textToCopy =
      comparison?.comparative_summary_markdown ||
      comparison?.comparative_summary ||
      '';
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadMarkdown = () => {
    const text =
      comparison?.comparative_summary_markdown ||
      comparison?.comparative_summary ||
      '';
    if (!text) return;
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparative_analysis_${comparison?.comparison_id || 'export'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleDownloadJson = () => {
    if (!comparison) return;
    const blob = new Blob([JSON.stringify(comparison, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparative_matrix_${comparison.comparison_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // Compare criteria keys required by prompt
  const REQUIRED_CRITERIA = [
    { key: 'objectives', label: 'Research Objectives', desc: 'Target aims, research questions, and scope' },
    { key: 'algorithms', label: 'Algorithms & Models', desc: 'Core algorithmic architectures and mathematical models' },
    { key: 'methodology', label: 'Methodologies', desc: 'Study frameworks and theoretical formulations' },
    { key: 'datasets', label: 'Datasets & Benchmarks', desc: 'Datasets evaluated, sizes, and domain sources' },
    { key: 'metrics', label: 'Evaluation Metrics', desc: 'Specific quantitative metrics and error measures' },
    { key: 'results', label: 'Experimental Results', desc: 'Reported performance outcomes and benchmark scores' },
    { key: 'strengths', label: 'Strengths & Novelty', desc: 'Demonstrated superiority and novel contributions' },
    { key: 'limitations', label: 'Limitations & Bottlenecks', desc: 'Reported constraints and failure modes' },
  ];

  // Helper to resolve cell value for a paper
  const getCellValue = (row: MatrixRow | any, paperId: string): MatrixCell | null => {
    if (!row) return null;
    if (Array.isArray(row.cells)) {
      const match = row.cells.find((c: MatrixCell) => c.paper_id === paperId);
      if (match) return match;
    }
    // Fallback for flat dictionary
    if (row[paperId]) {
      const val = row[paperId];
      return typeof val === 'string'
        ? { paper_id: paperId, paper_title: '', criterion_name: row.criterion_label || '', value: val }
        : val;
    }
    return null;
  };

  const getComparedPaperTitle = (paperId: string): string => {
    const doc = documents.find((d) => d.id === paperId);
    if (doc) return doc.title || doc.filename;
    if (comparison && comparison.compared_papers) {
      const cp = comparison.compared_papers.find((p: any) => p.id === paperId);
      if (cp) return cp.title;
    }
    return paperId.slice(0, 8);
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <Scale className="w-5 h-5 text-slate-800" />
            Cross-Paper Comparative Analysis
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Head-to-head comparative analysis of 2–5 research papers. Rigor-backed comparability assessments, multi-criteria matrix, and narrative synthesis.
          </p>
        </div>

        <button
          type="button"
          onClick={() => handleRunComparison(false)}
          disabled={isComparing || selectedIds.length < 2 || selectedIds.length > 5}
          className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors disabled:opacity-50 self-start md:self-auto"
        >
          {isComparing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Synthesizing Matrix...</span>
            </>
          ) : (
            <>
              <Scale className="w-3.5 h-3.5" />
              <span>Compare Selected ({selectedIds.length} Papers)</span>
            </>
          )}
        </button>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Paper Multi-Select Workspace (2 to 5 papers) */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div>
            <span className="font-semibold text-gray-900 block">
              Select 2 to 5 Academic Papers to Compare
            </span>
            <span className="text-gray-500 text-[11px]">
              Select papers across common or divergent domains for cross-paper matrix synthesis.
            </span>
          </div>
          <span
            className={`font-mono text-xs px-2 py-0.5 rounded border ${
              selectedIds.length >= 2 && selectedIds.length <= 5
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}
          >
            {selectedIds.length} of 5 selected
          </span>
        </div>

        <div className="flex flex-wrap gap-2 pt-1 max-h-36 overflow-y-auto">
          {documents.map((doc) => {
            const isSelected = selectedIds.includes(doc.id);
            return (
              <button
                key={doc.id}
                type="button"
                onClick={() => toggleSelectPaper(doc.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium border transition-colors cursor-pointer ${
                  isSelected
                    ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                }`}
              >
                <FileText className={`w-3.5 h-3.5 ${isSelected ? 'text-white' : 'text-gray-400'}`} />
                <span className="truncate max-w-[240px]">{doc.title || doc.filename}</span>
                {isSelected && <Check className="w-3 h-3 text-white ml-0.5" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Comparison Loading */}
      {isComparing && (
        <div className="py-12 bg-white border border-gray-200 rounded-lg">
          <LoadingState message="Extracting 13-criteria matrix, computing methodological divergences, and assessing experimental comparability..." />
        </div>
      )}

      {/* Comparison Results */}
      {comparison && !isComparing && (
        <div className="space-y-6">
          {/* Action Bar for Exporting Comparison */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 bg-gray-50 border border-gray-200 rounded-lg text-xs">
            <div className="font-semibold text-gray-900 truncate">
              {comparison.comparison_title || comparison.title || 'Cross-Paper Comparative Study'}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyMarkdown}
                className="px-2.5 py-1 text-xs bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-1"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Summary'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadMarkdown}
                className="px-2.5 py-1 text-xs bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                <span>Export Markdown (.md)</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadJson}
                className="px-2.5 py-1 text-xs bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-1"
              >
                <FileSpreadsheet className="w-3 h-3" />
                <span>Export JSON</span>
              </button>
            </div>
          </div>

          {/* 1. Comparability Assessment Warning & Caveat */}
          {comparison.comparability_assessment && (
            <div className="bg-amber-50/60 border border-amber-200 rounded-lg p-4 flex items-start gap-3 text-xs">
              <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-amber-900">
                    Scientific Comparability Verdict: {comparison.comparability_assessment.verdict || 'Partially Comparable'}
                  </span>
                </div>
                <p className="text-amber-800 leading-relaxed">
                  {comparison.comparability_assessment.warning_or_caveat ||
                    'Important: Do not claim that an algorithm is superior simply because its reported accuracy is higher. Verify whether datasets, baseline parameters, and evaluation protocols are identical.'}
                </p>
                <div className="flex flex-wrap gap-4 pt-1 text-[11px] text-amber-900 font-mono">
                  <span>Datasets: {comparison.comparability_assessment.dataset_comparability || 'Divergent'}</span>
                  <span>Settings: {comparison.comparability_assessment.experimental_setting_comparability || 'Divergent'}</span>
                  <span>Metrics: {comparison.comparability_assessment.metric_comparability || 'Partially Shared'}</span>
                </div>
              </div>
            </div>
          )}

          {/* 2. Comparison Table Covering Required Criteria */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-xs overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-200 bg-gray-50/70 flex items-center justify-between">
              <div>
                <h2 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Comparative Analysis Matrix
                </h2>
                <p className="text-[11px] text-gray-500 mt-0.5">
                  Multi-criteria side-by-side comparison across all {selectedIds.length} papers. Click any cell to inspect source quotes.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-gray-700">
                    <th className="py-3 px-4 font-bold w-52 bg-gray-50/90 border-r border-gray-200">
                      Comparison Dimension
                    </th>
                    {selectedIds.map((pId, idx) => (
                      <th
                        key={pId}
                        className="py-3 px-4 font-bold border-r border-gray-200 last:border-r-0 min-w-[200px]"
                      >
                        <div className="text-slate-900 font-semibold truncate" title={getComparedPaperTitle(pId)}>
                          Paper {idx + 1}: {getComparedPaperTitle(pId)}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-gray-700">
                  {(comparison.matrix && comparison.matrix.length > 0
                    ? comparison.matrix
                    : REQUIRED_CRITERIA.map((rc) => ({
                        criterion_key: rc.key,
                        criterion_label: rc.label,
                        cells: []
                      }))
                  ).map((row: any, rIdx: number) => {
                    const rowLabel = row.criterion_label || row.criterion_name || row.criterion || `Dimension ${rIdx + 1}`;
                    return (
                      <tr key={rIdx} className="hover:bg-gray-50/50 transition-colors">
                        {/* Criterion Title */}
                        <td className="py-3.5 px-4 font-semibold text-gray-900 bg-gray-50/40 border-r border-gray-200 align-top">
                          <div className="font-semibold text-gray-900">{rowLabel}</div>
                          {row.criterion_key && (
                            <span className="text-[10px] text-gray-400 font-mono">
                              #{row.criterion_key}
                            </span>
                          )}
                        </td>

                        {/* Paper Value Cells */}
                        {selectedIds.map((pId) => {
                          const cell = getCellValue(row, pId);
                          const cellKey = `${rIdx}_${pId}`;
                          const isEvidenceExpanded = Boolean(expandedCellEvidence[cellKey]);
                          const cellVal = cell?.value || (row[pId] ? String(row[pId]) : 'Not Reported');

                          return (
                            <td
                              key={pId}
                              className="py-3.5 px-4 text-gray-800 leading-relaxed border-r border-gray-100 last:border-r-0 align-top font-sans"
                            >
                              <div className="space-y-1.5">
                                <p className="text-xs text-gray-800 leading-relaxed">
                                  {cellVal}
                                </p>

                                {/* Supporting Passage & Page Number */}
                                {cell?.evidence_quote && (
                                  <div className="pt-1">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        setExpandedCellEvidence((prev) => ({
                                          ...prev,
                                          [cellKey]: !prev[cellKey]
                                        }))
                                      }
                                      className="text-[10px] text-slate-800 hover:text-slate-950 font-medium flex items-center gap-1"
                                    >
                                      <Quote className="w-3 h-3 text-slate-600" />
                                      <span>
                                        {isEvidenceExpanded
                                          ? 'Hide Source Quote'
                                          : `Source Evidence ${cell.page_number ? `(p. ${cell.page_number})` : ''}`}
                                      </span>
                                    </button>

                                    {isEvidenceExpanded && (
                                      <div className="mt-1.5 p-2 bg-emerald-50/50 border border-emerald-200 rounded font-mono text-[11px] text-emerald-950 leading-relaxed">
                                        <div className="text-[9px] font-semibold uppercase tracking-wider text-emerald-700 mb-0.5">
                                          {cell.section_name ? `Section: ${cell.section_name}` : 'Verbatim Passage'}
                                          {cell.page_number ? ` &bull; Page ${cell.page_number}` : ''}
                                        </div>
                                        "{cell.evidence_quote}"
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. Written Comparative Explanation & Narrative */}
          <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div>
                <h2 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Comparative Written Explanation
                </h2>
                <p className="text-[11px] text-gray-500 mt-0.5">
                  Synthesized analytical explanation of architectural paradigms, convergence properties, and empirical trade-offs.
                </p>
              </div>

              <button
                type="button"
                onClick={handleCopyMarkdown}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-600 hover:text-gray-900 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Explanation'}</span>
              </button>
            </div>

            <div className="text-xs text-gray-800 font-sans leading-relaxed p-4 bg-gray-50/70 rounded border border-gray-100 max-h-96 overflow-y-auto whitespace-pre-wrap">
              {comparison.comparative_summary_markdown ||
                comparison.comparative_summary ||
                'Comparative narrative synthesis generated across selected research papers.'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default ComparativeAnalysis;
