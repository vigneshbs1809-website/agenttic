import React, { useState, useEffect, useMemo } from 'react';
import {
  FileText,
  Download,
  Copy,
  Check,
  RefreshCw,
  BookOpen,
  Layers,
  ChevronRight,
  Sparkles,
  Trash2,
  Eye,
  FileCheck2,
  Calendar,
  Compass,
  ArrowRight,
  Filter,
  CheckCircle2,
  AlertCircle,
  Hash,
  Share2,
  Search,
  ExternalLink
} from 'lucide-react';
import {
  Document,
  ResearchProjectItem,
  AcademicReportType,
  CitationStyle,
  ReportSummaryItem,
  ReportDetailResponse,
  ReportGenerateRequest
} from '../types';
import { api } from '../services/api';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { ModalDialog } from '../components/common/ModalDialog';

interface ResearchReportsProps {
  documents: Document[];
  selectedProjectId?: string;
}

interface ReportTypeMeta {
  key: AcademicReportType;
  title: string;
  badge: string;
  description: string;
  sectionCount: string;
}

const REPORT_TYPES: ReportTypeMeta[] = [
  {
    key: 'literature_review',
    title: 'Complete Literature Review',
    badge: 'Comprehensive',
    description: 'All 15 standard sections: Background, Thematic Analysis, Methodology Matrix, Trends, Contradictions, Gaps, Evidence Audit, and Proposed Framework.',
    sectionCount: '15 Academic Sections',
  },
  {
    key: 'individual_paper',
    title: 'Individual Paper Analysis',
    badge: 'Monograph',
    description: 'Deep architectural inspection, problem formulation, datasets, reported empirical results, stated limitations, and verified PDF page citations.',
    sectionCount: '6 Granular Sections',
  },
  {
    key: 'comparative_analysis',
    title: 'Comparative Analysis',
    badge: 'Cross-Paper',
    description: 'Multi-paper evaluation matrix comparing objectives, methodologies, algorithms, metrics, comparability assessment, and trade-offs.',
    sectionCount: '5 Comparative Dimensions',
  },
  {
    key: 'gap_analysis',
    title: 'Research Gap Analysis',
    badge: 'Frontier',
    description: 'Synthesis of explicit author limitations and system-inferred gaps across 10 categories with verbatim evidence and confidence scoring.',
    sectionCount: 'Categorized Gap Taxonomy',
  },
  {
    key: 'contradiction_analysis',
    title: 'Contradiction Analysis',
    badge: 'Discrepancy',
    description: 'Side-by-side conflicting passages, experimental condition divergences, root-cause dissections, and reproducibility implications.',
    sectionCount: 'Evidence Pairs & Root Cause',
  },
  {
    key: 'proposed_methodology',
    title: 'Proposed Research Methodology',
    badge: 'Methodology',
    description: 'Grounded research questions (RQ1–RQ3), novel system architecture, benchmark protocol, and gap mitigations designed for 8 GB RAM systems.',
    sectionCount: 'Actionable Research Roadmap',
  },
];

export const ResearchReports: React.FC<ResearchReportsProps> = ({
  documents,
  selectedProjectId: initialProjectId
}) => {
  // Navigation / View state
  const [activeTab, setActiveTab] = useState<'reader' | 'history'>('reader');
  
  // Data state
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [history, setHistory] = useState<ReportSummaryItem[]>([]);
  const [selectedReport, setSelectedReport] = useState<ReportDetailResponse | null>(null);
  
  // Generator configuration form state
  const [targetProjectId, setTargetProjectId] = useState<string>(initialProjectId || '');
  const [reportType, setReportType] = useState<AcademicReportType>('literature_review');
  const [citationStyle, setCitationStyle] = useState<CitationStyle>('IEEE');
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [customTitle, setCustomTitle] = useState<string>('');
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(true);

  // Operation state
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [historyFilter, setHistoryFilter] = useState<string>('');

  // Delete confirmation modal state
  const [reportToDelete, setReportToDelete] = useState<ReportSummaryItem | null>(null);

  // Sync project selection
  useEffect(() => {
    if (initialProjectId) {
      setTargetProjectId(initialProjectId);
    }
  }, [initialProjectId]);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, [targetProjectId]);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [projList, histList] = await Promise.all([
        api.getProjects(),
        api.getReportsHistory(targetProjectId || undefined),
      ]);
      setProjects(projList);
      setHistory(histList);

      if (!targetProjectId && projList.length > 0) {
        setTargetProjectId(projList[0].id);
      }

      // If no active report loaded, load the most recent report if available
      if (!selectedReport && histList.length > 0) {
        const topReport = await api.getReportDetail(histList[0].id);
        setSelectedReport(topReport);
      }
    } catch (err: any) {
      console.error('Failed to load reports initial data', err);
      setError(err.message || 'Failed to initialize academic reports');
    } finally {
      setLoading(false);
    }
  };

  // Papers filtered by target project
  const projectPapers = useMemo(() => {
    if (!targetProjectId) return documents;
    return documents.filter((d) => d.project_id === targetProjectId);
  }, [documents, targetProjectId]);

  // Selected project object
  const activeProject = useMemo(() => {
    return projects.find((p) => p.id === targetProjectId) || null;
  }, [projects, targetProjectId]);

  // Handle report generation
  const handleGenerateReport = async () => {
    if (!targetProjectId) {
      setError('Please select a research project scope to ground this report.');
      return;
    }
    setGenerating(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const payload: ReportGenerateRequest = {
        project_id: targetProjectId,
        report_type: reportType,
        citation_style: citationStyle,
        paper_ids: selectedPaperIds.length > 0 ? selectedPaperIds : undefined,
        custom_title: customTitle.trim() || undefined,
      };

      const generated = await api.generateAcademicReport(payload);
      setSelectedReport(generated);
      setActiveTab('reader');
      setIsConfigOpen(false);
      setSuccessMessage(`Academic report "${generated.report_title}" generated successfully.`);
      
      // Refresh history list
      const updatedHistory = await api.getReportsHistory(targetProjectId || undefined);
      setHistory(updatedHistory);
    } catch (err: any) {
      setError(err.message || 'Failed to generate academic research report');
    } finally {
      setGenerating(false);
    }
  };

  // Handle previewing a report from history
  const handleSelectReportFromHistory = async (reportId: string) => {
    setLoading(true);
    try {
      const detail = await api.getReportDetail(reportId);
      setSelectedReport(detail);
      setActiveTab('reader');
    } catch (err: any) {
      setError(err.message || 'Failed to load report detail');
    } finally {
      setLoading(false);
    }
  };

  // Handle Export File
  const handleExport = async (format: 'pdf' | 'docx' | 'markdown') => {
    if (!selectedReport) return;
    setDownloadingFormat(format);
    try {
      const cleanTitle = selectedReport.report_title.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
      await api.exportReportFile(selectedReport.id, format, cleanTitle);
    } catch (err: any) {
      setError(err.message || `Failed to export as ${format.toUpperCase()}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Handle Copy Markdown
  const handleCopyMarkdown = () => {
    if (!selectedReport) return;
    navigator.clipboard.writeText(selectedReport.content_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Handle Delete Report
  const confirmDeleteReport = async () => {
    if (!reportToDelete) return;
    setDeletingId(reportToDelete.id);
    try {
      await api.deleteReport(reportToDelete.id);
      setHistory((prev) => prev.filter((r) => r.id !== reportToDelete.id));
      if (selectedReport?.id === reportToDelete.id) {
        setSelectedReport(null);
      }
      setReportToDelete(null);
    } catch (err: any) {
      setError(err.message || 'Failed to delete report');
    } finally {
      setDeletingId(null);
    }
  };

  // Filtered history list
  const filteredHistory = useMemo(() => {
    if (!historyFilter.trim()) return history;
    const term = historyFilter.toLowerCase();
    return history.filter(
      (h) =>
        h.report_title.toLowerCase().includes(term) ||
        h.project_title.toLowerCase().includes(term) ||
        h.report_type.toLowerCase().includes(term)
    );
  }, [history, historyFilter]);

  // Extract table of contents headings from markdown
  const tableOfContents = useMemo(() => {
    if (!selectedReport) return [];
    const lines = selectedReport.content_markdown.split('\n');
    const headings: { level: number; title: string; id: string }[] = [];
    lines.forEach((l) => {
      const trimmed = l.trim();
      if (trimmed.startsWith('## ')) {
        const title = trimmed.replace('## ', '').trim();
        const id = title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        headings.push({ level: 2, title, id });
      } else if (trimmed.startsWith('### ')) {
        const title = trimmed.replace('### ', '').trim();
        const id = title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        headings.push({ level: 3, title, id });
      }
    });
    return headings;
  }, [selectedReport]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 pb-16">
      {/* 1. Header & Quick Statistics */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-700" />
                <h1 className="text-xl font-semibold text-slate-900 tracking-tight">
                  Academic Report Generator
                </h1>
                <span className="text-xs bg-slate-100 text-slate-700 border border-slate-300 px-2 py-0.5 rounded font-mono">
                  Multi-Format Engine
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Ground literature reviews, comparative matrices, and gap syntheses strictly in peer-reviewed evidence.
              </p>
            </div>

            {/* Top Toolbar Actions */}
            <div className="flex items-center gap-3">
              <div className="inline-flex rounded-md border border-slate-300 p-0.5 bg-slate-100">
                <button
                  type="button"
                  onClick={() => setActiveTab('reader')}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${
                    activeTab === 'reader'
                      ? 'bg-white text-slate-900 shadow-sm border border-slate-200'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" />
                    Document Reader
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('history')}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${
                    activeTab === 'history'
                      ? 'bg-white text-slate-900 shadow-sm border border-slate-200'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5" />
                    Report History ({history.length})
                  </span>
                </button>
              </div>

              <button
                type="button"
                onClick={() => setIsConfigOpen(!isConfigOpen)}
                className={`px-3 py-1.5 text-xs font-medium rounded border transition-colors flex items-center gap-1.5 ${
                  isConfigOpen
                    ? 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                {isConfigOpen ? 'Close Generator' : 'Generate New Report'}
              </button>
            </div>
          </div>

          {/* Quick Metrics Strip */}
          <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-slate-600">
            <div>
              <span className="text-slate-400">Target Project: </span>
              <span className="font-medium text-slate-800">
                {activeProject ? activeProject.title : 'None Selected'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Available Corpus: </span>
              <span className="font-medium text-slate-800">
                {projectPapers.length} Papers
              </span>
            </div>
            <div>
              <span className="text-slate-400">Citation Style: </span>
              <span className="font-mono font-medium text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                {selectedReport ? selectedReport.citation_style : citationStyle}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Total Generated: </span>
              <span className="font-medium text-slate-800">
                {history.length} Dossiers
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error and Success Notifications */}
        {error && (
          <ErrorMessage
            message={error}
            onDismiss={() => setError(null)}
          />
        )}

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

        {/* 2. Generator Configuration Panel */}
        {isConfigOpen && (
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden transition-all">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-slate-700" />
                <h2 className="text-sm font-semibold text-slate-900">
                  Configure Academic Report Synthesis
                </h2>
              </div>
              <span className="text-xs text-slate-500">
                Step-by-step evidence grounded compilation
              </span>
            </div>

            <div className="p-5 space-y-5">
              {/* Scope & Citation Standard Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Project Selection */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Target Research Project <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={targetProjectId}
                    onChange={(e) => {
                      setTargetProjectId(e.target.value);
                      setSelectedPaperIds([]);
                    }}
                    className="w-full text-xs bg-white border border-slate-300 rounded px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-500"
                  >
                    <option value="" disabled>Select project scope...</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title} ({p.paper_count || 0} papers)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Citation Style Toggle */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Citation Standard <span className="text-rose-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setCitationStyle('IEEE')}
                      className={`text-xs px-3 py-2 rounded border font-medium flex items-center justify-between ${
                        citationStyle === 'IEEE'
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <span>IEEE</span>
                      <span className="font-mono opacity-75 text-[10px]">[1], [2]</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setCitationStyle('APA')}
                      className={`text-xs px-3 py-2 rounded border font-medium flex items-center justify-between ${
                        citationStyle === 'APA'
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <span>APA 7th</span>
                      <span className="font-mono opacity-75 text-[10px]">(Author, 2024)</span>
                    </button>
                  </div>
                </div>

                {/* Custom Title Input */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Custom Title (Optional)
                  </label>
                  <input
                    type="text"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                    placeholder="e.g., Systematic Review: Local LLM Viability"
                    className="w-full text-xs bg-white border border-slate-300 rounded px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-500"
                  />
                </div>
              </div>

              {/* Report Type Selector (6 Standard Academic Types) */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-2">
                  Academic Report Type <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {REPORT_TYPES.map((t) => {
                    const isSelected = reportType === t.key;
                    return (
                      <div
                        key={t.key}
                        onClick={() => setReportType(t.key)}
                        className={`cursor-pointer p-3.5 rounded border text-left transition-all ${
                          isSelected
                            ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                            : 'bg-white text-slate-800 border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-semibold tracking-tight">
                            {t.title}
                          </span>
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider ${
                              isSelected
                                ? 'bg-slate-800 text-slate-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                            }`}
                          >
                            {t.badge}
                          </span>
                        </div>
                        <p
                          className={`text-xs line-clamp-2 mb-2 leading-relaxed ${
                            isSelected ? 'text-slate-300' : 'text-slate-500'
                          }`}
                        >
                          {t.description}
                        </p>
                        <div
                          className={`text-[11px] font-medium flex items-center gap-1 ${
                            isSelected ? 'text-blue-300' : 'text-slate-600'
                          }`}
                        >
                          <CheckCircle2 className="w-3 h-3" />
                          {t.sectionCount}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Synthesized directly against local SQLite data with zero external API calls.
                </span>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsConfigOpen(false)}
                    className="px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={generating || !targetProjectId}
                    onClick={handleGenerateReport}
                    className="px-4 py-2 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                  >
                    {generating ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        Synthesizing Grounded Dossier...
                      </>
                    ) : (
                      <>
                        <FileCheck2 className="w-3.5 h-3.5" />
                        Generate Academic Report
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. Main Content: Reader vs History */}
        {activeTab === 'reader' ? (
          <div>
            {selectedReport ? (
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                {/* Left: Table of Contents & Metadata Panel */}
                <div className="lg:col-span-1 space-y-4">
                  <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
                    <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
                      Report Metadata
                    </h3>
                    <div className="space-y-2.5 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[11px]">Type:</span>
                        <span className="font-medium text-slate-800 capitalize">
                          {selectedReport.report_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Citation Standard:</span>
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">
                          {selectedReport.citation_style}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Corpus Project:</span>
                        <span className="font-medium text-slate-800 truncate block">
                          {selectedReport.project_title}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Total Volume:</span>
                        <span className="font-mono text-slate-800">
                          {selectedReport.word_count.toLocaleString()} Words
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Engine:</span>
                        <span className="text-slate-600 text-[11px] block truncate">
                          {selectedReport.generation_model}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Table of Contents */}
                  {tableOfContents.length > 0 && (
                    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm sticky top-24 max-h-[calc(100vh-140px)] overflow-y-auto">
                      <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2.5">
                        Table of Contents
                      </h3>
                      <nav className="space-y-1">
                        {tableOfContents.map((h, i) => (
                          <a
                            key={i}
                            href={`#section-${i}`}
                            className={`block text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-50 px-2 py-1 rounded truncate transition-colors ${
                              h.level === 3 ? 'pl-5 text-slate-500' : 'font-medium'
                            }`}
                          >
                            {h.title}
                          </a>
                        ))}
                      </nav>
                    </div>
                  )}
                </div>

                {/* Right: Academic Document Content */}
                <div className="lg:col-span-3 space-y-4">
                  {/* Export & Action Bar */}
                  <div className="bg-white border border-slate-200 rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 font-medium">Export Formats:</span>
                      <button
                        type="button"
                        onClick={() => handleExport('pdf')}
                        disabled={downloadingFormat === 'pdf'}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        {downloadingFormat === 'pdf' ? 'Generating PDF...' : 'PDF Dossier'}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleExport('docx')}
                        disabled={downloadingFormat === 'docx'}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        {downloadingFormat === 'docx' ? 'Compiling DOCX...' : 'Word (.docx)'}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleExport('markdown')}
                        disabled={downloadingFormat === 'markdown'}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Markdown
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopyMarkdown}
                        className="px-3 py-1.5 text-xs font-medium rounded border border-slate-300 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 transition-colors"
                      >
                        {copied ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            Copy Markdown
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Academic Reading Sheet */}
                  <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-8 sm:p-12 font-serif text-slate-800 leading-relaxed space-y-6">
                    {/* Render Formatted Markdown */}
                    <div className="prose prose-slate max-w-none text-sm font-sans space-y-4">
                      {selectedReport.content_markdown.split('\n\n').map((paragraph, pIdx) => {
                        const trimmed = paragraph.trim();

                        // Title H1
                        if (trimmed.startsWith('# ')) {
                          return (
                            <div key={pIdx} className="border-b border-slate-200 pb-4 mb-6">
                              <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-serif">
                                {trimmed.replace('# ', '')}
                              </h1>
                            </div>
                          );
                        }

                        // Section Heading H2
                        if (trimmed.startsWith('## ')) {
                          return (
                            <h2
                              key={pIdx}
                              id={`section-${pIdx}`}
                              className="text-base font-bold text-slate-900 border-b border-slate-200 pb-1.5 pt-4 font-sans tracking-tight"
                            >
                              {trimmed.replace('## ', '')}
                            </h2>
                          );
                        }

                        // Sub-heading H3
                        if (trimmed.startsWith('### ')) {
                          return (
                            <h3
                              key={pIdx}
                              id={`section-${pIdx}`}
                              className="text-sm font-semibold text-slate-800 pt-2 font-sans"
                            >
                              {trimmed.replace('### ', '')}
                            </h3>
                          );
                        }

                        // Divider
                        if (trimmed === '---') {
                          return <hr key={pIdx} className="border-slate-200 my-4" />;
                        }

                        // Blockquote Evidence Callout
                        if (trimmed.startsWith('>')) {
                          return (
                            <blockquote
                              key={pIdx}
                              className="bg-slate-50 border-l-4 border-slate-800 px-4 py-2.5 rounded-r text-xs text-slate-700 italic my-3"
                            >
                              {trimmed.replace(/^>\s*/gm, '')}
                            </blockquote>
                          );
                        }

                        // Table block
                        if (trimmed.startsWith('|')) {
                          const rows = trimmed.split('\n').filter((r) => !r.includes('---'));
                          if (rows.length === 0) return null;
                          const headerCols = rows[0].split('|').filter(Boolean);
                          const bodyRows = rows.slice(1);

                          return (
                            <div key={pIdx} className="overflow-x-auto my-4 border border-slate-200 rounded">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                                  <tr>
                                    {headerCols.map((c, ci) => (
                                      <th key={ci} className="px-3 py-2 border-r last:border-r-0 border-slate-200">
                                        {c.trim()}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {bodyRows.map((r, ri) => {
                                    const cells = r.split('|').filter(Boolean);
                                    return (
                                      <tr key={ri} className="hover:bg-slate-50/50">
                                        {cells.map((cell, cii) => (
                                          <td
                                            key={cii}
                                            className="px-3 py-2 border-r last:border-r-0 border-slate-100 text-slate-700"
                                          >
                                            {cell.trim().replace(/\*\*/g, '')}
                                          </td>
                                        ))}
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          );
                        }

                        // Bullet list
                        if (trimmed.startsWith('- ')) {
                          const items = trimmed.split('\n').filter((i) => i.trim().startsWith('- '));
                          return (
                            <ul key={pIdx} className="list-disc pl-5 space-y-1.5 text-xs text-slate-700">
                              {items.map((it, iti) => (
                                <li key={iti} className="leading-relaxed">
                                  {it.replace(/^- /, '')}
                                </li>
                              ))}
                            </ul>
                          );
                        }

                        // Standard paragraph
                        return (
                          <p key={pIdx} className="text-xs text-slate-700 leading-relaxed font-sans">
                            {trimmed}
                          </p>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-slate-200 p-12 text-center max-w-xl mx-auto shadow-sm">
                <FileText className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <h3 className="text-sm font-semibold text-slate-900 mb-1">
                  No Active Research Report
                </h3>
                <p className="text-xs text-slate-500 mb-4">
                  Select a past report from history or configure the generator above to produce a comprehensive academic dossier.
                </p>
                <button
                  type="button"
                  onClick={() => setIsConfigOpen(true)}
                  className="px-4 py-2 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800"
                >
                  Configure New Report
                </button>
              </div>
            )}
          </div>
        ) : (
          /* 4. Report History Audit Log Table */
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            {/* Filter Bar */}
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="relative flex-1 max-w-sm">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={historyFilter}
                  onChange={(e) => setHistoryFilter(e.target.value)}
                  placeholder="Filter reports by title or project..."
                  className="w-full text-xs pl-8 pr-3 py-1.5 bg-white border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  Showing {filteredHistory.length} of {history.length} reports
                </span>
                <button
                  type="button"
                  onClick={loadInitialData}
                  className="p-1.5 text-slate-500 hover:text-slate-800 rounded border border-slate-300 bg-white"
                  title="Refresh History"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Table */}
            {filteredHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Report Title & Type</th>
                      <th className="py-2.5 px-4">Research Project</th>
                      <th className="py-2.5 px-4">Citation Style</th>
                      <th className="py-2.5 px-4">Length</th>
                      <th className="py-2.5 px-4">Generated Date</th>
                      <th className="py-2.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredHistory.map((rep) => (
                      <tr key={rep.id} className="hover:bg-slate-50/75 transition-colors">
                        <td className="py-3 px-4 max-w-xs">
                          <div className="font-semibold text-slate-900 truncate">
                            {rep.report_title}
                          </div>
                          <div className="text-[11px] text-slate-500 capitalize flex items-center gap-1.5 mt-0.5">
                            <span className="font-mono bg-slate-100 px-1 py-0.2 rounded border border-slate-200">
                              {rep.report_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-700 truncate max-w-[180px]">
                          {rep.project_title}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">
                            {rep.citation_style}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-600 font-mono">
                          {rep.word_count.toLocaleString()} words
                        </td>
                        <td className="py-3 px-4 text-slate-500 text-[11px]">
                          {rep.created_at ? new Date(rep.created_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-right space-x-1">
                          <button
                            type="button"
                            onClick={() => handleSelectReportFromHistory(rep.id)}
                            className="px-2 py-1 text-xs font-medium rounded border border-slate-300 text-slate-700 hover:bg-slate-100 inline-flex items-center gap-1"
                            title="Preview Dossier"
                          >
                            <Eye className="w-3 h-3" />
                            View
                          </button>
                          <button
                            type="button"
                            onClick={async () => {
                              const clean = rep.report_title.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
                              await api.exportReportFile(rep.id, 'pdf', clean);
                            }}
                            className="px-2 py-1 text-xs font-medium rounded border border-rose-200 text-rose-700 hover:bg-rose-50 inline-flex items-center gap-1"
                            title="Export PDF"
                          >
                            <Download className="w-3 h-3" />
                            PDF
                          </button>
                          <button
                            type="button"
                            onClick={async () => {
                              const clean = rep.report_title.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
                              await api.exportReportFile(rep.id, 'docx', clean);
                            }}
                            className="px-2 py-1 text-xs font-medium rounded border border-blue-200 text-blue-700 hover:bg-blue-50 inline-flex items-center gap-1"
                            title="Export DOCX"
                          >
                            <Download className="w-3 h-3" />
                            DOCX
                          </button>
                          <button
                            type="button"
                            onClick={() => setReportToDelete(rep)}
                            className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors inline-flex items-center"
                            title="Delete Report"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">
                No generated reports match your criteria.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {reportToDelete && (
        <ModalDialog
          isOpen={true}
          onClose={() => setReportToDelete(null)}
          title="Delete Research Report"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs text-slate-700">
            <p>
              Are you sure you want to permanently delete the report{' '}
              <span className="font-semibold text-slate-900">"{reportToDelete.report_title}"</span>?
            </p>
            <p className="text-slate-500">
              This action removes the compiled markdown dossier and citation indices from SQLite.
            </p>
            <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReportToDelete(null)}
                className="px-3 py-1.5 text-xs font-medium rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={Boolean(deletingId)}
                onClick={confirmDeleteReport}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {deletingId ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </ModalDialog>
      )}
    </div>
  );
};
export default ResearchReports;
