import React, { useState, useEffect } from 'react';
import {
  FolderKanban,
  FileText,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Target,
  BarChart3,
  Calendar,
  Clock,
  Plus,
  Compass,
  Upload,
  ArrowRight,
  Layers,
  Cpu,
  RefreshCw,
  Search,
  BookOpen
} from 'lucide-react';
import {
  Document,
  SystemHealth,
  ResearchProjectItem,
  AnalyticsSummary,
  RecentActivityItem
} from '../types';
import { api } from '../services/api';
import { DataTable, Column } from '../components/common/DataTable';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { SearchInput } from '../components/common/SearchInput';
import { ModalDialog } from '../components/common/ModalDialog';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorMessage } from '../components/common/ErrorMessage';

interface OverviewProps {
  documents: Document[];
  health: SystemHealth | null;
  projects: ResearchProjectItem[];
  onNavigate: (tab: string, contextId?: string) => void;
  onOpenUpload?: () => void;
}

export const Overview: React.FC<OverviewProps> = ({
  documents,
  health,
  projects,
  onNavigate,
  onOpenUpload
}) => {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Search & Pagination for Ingested Papers Table
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;

  // New Project Dialog State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getAnalytics();
      setAnalytics(data);
    } catch (e: any) {
      console.warn('Failed to load analytics summary', e);
      setErrorMsg('Could not fetch real-time analytics from SQLite.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsCreating(true);
    try {
      const created = await api.createProject({
        title: newTitle.trim(),
        domain: newDomain.trim() || undefined,
        description: newDescription.trim() || undefined
      });
      setIsCreateOpen(false);
      setNewTitle('');
      setNewDomain('');
      setNewDescription('');
      // Navigate to projects view with the new project
      onNavigate('projects', created.id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create new project');
    } finally {
      setIsCreating(false);
    }
  };

  // Filter papers
  const filteredDocs = documents.filter((d) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const titleMatch = (d.title || d.filename || '').toLowerCase().includes(q);
    const authorMatch = (d.authors || []).some((a) => a.toLowerCase().includes(q));
    return titleMatch || authorMatch;
  });

  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;
  const paginatedDocs = filteredDocs.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Computed metrics from real SQLite analytics
  const totalProjects = analytics?.total_projects ?? projects.length;
  const totalUploadedPapers = analytics?.total_uploaded_papers ?? documents.length;
  const processedPapers = analytics?.processed_papers ?? documents.filter((d) => d.processed_status === 'completed').length;
  const identifiedGaps = analytics?.identified_research_gaps ?? analytics?.total_gaps ?? 0;
  const verifiedClaims = analytics?.verified_claims ?? 0;
  const yearDistribution = analytics?.year_distribution || [];
  const maxYearPapers = Math.max(...yearDistribution.map((y) => y.papers), 1);
  const recentActivities: RecentActivityItem[] = analytics?.recent_activity || [];

  const columns: Column<Document>[] = [
    {
      key: 'title',
      header: 'Paper Title',
      render: (doc) => (
        <div className="min-w-0 pr-4">
          <div className="font-semibold text-gray-900 truncate hover:text-slate-900">
            {doc.title || doc.filename}
          </div>
          <div className="text-[11px] text-gray-500 truncate mt-0.5">
            {doc.authors && doc.authors.length > 0 ? doc.authors.join(', ') : 'Authors Not Reported'}
          </div>
        </div>
      )
    },
    {
      key: 'publication_year',
      header: 'Year',
      width: '70px',
      render: (doc) => (
        <span className="text-gray-600 font-mono text-xs">{doc.publication_year || '—'}</span>
      )
    },
    {
      key: 'total_pages',
      header: 'Pages',
      width: '70px',
      render: (doc) => (
        <span className="text-gray-600 font-mono text-xs">{doc.total_pages || 1}</span>
      )
    },
    {
      key: 'chunk_count',
      header: 'Chunks',
      width: '80px',
      render: (doc) => (
        <span className="text-gray-600 font-mono text-xs">{doc.chunk_count || 0}</span>
      )
    },
    {
      key: 'processed_status',
      header: 'Status',
      width: '110px',
      render: (doc) => (
        <StatusIndicator status={doc.processed_status} size="sm" />
      )
    },
    {
      key: 'created_at',
      header: 'Ingested',
      width: '100px',
      render: (doc) => (
        <span className="text-gray-500 text-[11px]">
          {new Date(doc.created_at).toLocaleDateString()}
        </span>
      )
    }
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header with Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-slate-800" />
            Overview Dashboard
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Real-time literature corpus telemetry, research discovery metrics, and cross-paper analytics from SQLite.
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium shadow-xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Research Project</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('discover')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded text-xs font-medium transition-colors"
          >
            <Compass className="w-3.5 h-3.5 text-gray-500" />
            <span>Discover Papers</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('library')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded text-xs font-medium transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-gray-500" />
            <span>PDF Library</span>
          </button>
        </div>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* 5 Core KPI Summary Cards (Actual Database Information) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* 1. Total Research Projects */}
        <div
          onClick={() => onNavigate('projects')}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs space-y-1 hover:border-gray-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
            <span>Research Projects</span>
            <FolderKanban className="w-4 h-4 text-gray-400" />
          </div>
          <div className="text-2xl font-bold text-gray-900 font-mono">
            {totalProjects}
          </div>
          <div className="text-[11px] text-gray-500">
            Workspaces in SQLite
          </div>
        </div>

        {/* 2. Total Uploaded Papers */}
        <div
          onClick={() => onNavigate('library')}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs space-y-1 hover:border-gray-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
            <span>Uploaded Papers</span>
            <FileText className="w-4 h-4 text-gray-400" />
          </div>
          <div className="text-2xl font-bold text-gray-900 font-mono">
            {totalUploadedPapers}
          </div>
          <div className="text-[11px] text-gray-500">
            Cataloged academic PDFs
          </div>
        </div>

        {/* 3. Processed Papers */}
        <div
          onClick={() => onNavigate('library')}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs space-y-1 hover:border-gray-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
            <span>Processed Papers</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900 font-mono">
            {processedPapers}
          </div>
          <div className="text-[11px] text-emerald-700 font-medium">
            {totalUploadedPapers > 0 ? Math.round((processedPapers / totalUploadedPapers) * 100) : 0}% fully indexed
          </div>
        </div>

        {/* 4. Identified Research Gaps */}
        <div
          onClick={() => onNavigate('gaps')}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs space-y-1 hover:border-gray-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
            <span>Research Gaps</span>
            <Target className="w-4 h-4 text-slate-700" />
          </div>
          <div className="text-2xl font-bold text-gray-900 font-mono">
            {identifiedGaps}
          </div>
          <div className="text-[11px] text-gray-500">
            Across 10 categories
          </div>
        </div>

        {/* 5. Verified Claims */}
        <div
          onClick={() => onNavigate('verification')}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs space-y-1 hover:border-gray-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
            <span>Verified Claims</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900 font-mono">
            {verifiedClaims}
          </div>
          <div className="text-[11px] text-gray-500">
            Grounded PDF assertions
          </div>
        </div>
      </div>

      {/* Mid Grid: Research Publications by Year & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Research Publications by Year (Actual SQLite Distribution) */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-800" />
              <h2 className="text-sm font-semibold text-gray-900">
                Research Publications by Year
              </h2>
            </div>
            <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              Corpus Timeline
            </span>
          </div>

          {yearDistribution.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-500">
              No publication year data available in SQLite yet.
            </div>
          ) : (
            <div className="space-y-3 pt-1">
              {yearDistribution.map((item) => {
                const percent = Math.round((item.papers / maxYearPapers) * 100);
                return (
                  <div key={item.year} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-medium text-gray-800">
                        {item.year}
                      </span>
                      <span className="text-gray-500 font-mono">
                        {item.papers} {item.papers === 1 ? 'paper' : 'papers'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-slate-900 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500">
            <span>Aggregated from SQLite publication_year fields</span>
            <button
              onClick={() => onNavigate('trends')}
              className="text-slate-800 hover:text-slate-950 font-medium underline flex items-center gap-1"
            >
              View detailed trends
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Recent Activity Feed (Actual SQLite Records) */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-800" />
              <h2 className="text-sm font-semibold text-gray-900">
                Recent Platform Activity
              </h2>
            </div>
            <button
              onClick={loadAnalytics}
              className="text-xs text-gray-500 hover:text-gray-800 flex items-center gap-1"
              title="Refresh Activity"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Refresh</span>
            </button>
          </div>

          {recentActivities.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-500">
              No recent activity recorded yet. Ingest a paper or run verification to see events.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
              {recentActivities.map((act) => (
                <div
                  key={act.id}
                  className="p-2.5 bg-gray-50/70 border border-gray-200/70 rounded flex items-start justify-between gap-3 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="font-semibold text-gray-900 truncate">
                        {act.action}
                      </span>
                      <span className="px-1.5 py-0.2 bg-white border border-gray-200 rounded text-[10px] text-gray-600 font-mono">
                        {act.badge || 'Activity'}
                      </span>
                    </div>
                    <p className="text-gray-600 truncate text-[11px]">
                      {act.title}
                    </p>
                  </div>

                  <div className="text-[10px] text-gray-400 whitespace-nowrap shrink-0 mt-0.5 font-mono">
                    {act.timestamp ? new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pt-2 border-t border-gray-100 text-[11px] text-gray-500 flex items-center justify-between">
            <span>Audit trail of papers, gaps, and claim verifications</span>
            <span className="font-mono text-gray-400">SQLite Logged</span>
          </div>
        </div>
      </div>

      {/* Ingested Literature Papers Section */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">
              Ingested Academic Papers ({documents.length})
            </h2>
            <p className="text-xs text-gray-500">
              Scientific papers cataloged in SQLite. Select any paper to view its 14-dimension structured analysis.
            </p>
          </div>

          <div className="w-full sm:w-64">
            <SearchInput
              value={searchQuery}
              onChange={(q) => {
                setSearchQuery(q);
                setCurrentPage(1);
              }}
              placeholder="Search by title or author..."
            />
          </div>
        </div>

        <DataTable
          columns={columns}
          data={paginatedDocs}
          rowKey={(doc) => doc.id}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          totalItems={filteredDocs.length}
          pageSize={pageSize}
          emptyMessage={
            searchQuery ? 'No papers matching search query.' : 'No papers uploaded yet. Upload a PDF to begin.'
          }
          onRowClick={(doc) => onNavigate('analysis', doc.id)}
        />
      </div>

      {/* Quick Action: Create New Project Modal */}
      <ModalDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Research Project"
      >
        <form onSubmit={handleCreateProject} className="space-y-4">
          <p className="text-xs text-gray-600 leading-relaxed">
            Create an isolated project workspace to organize academic literature, cross-paper comparison matrices, and discovered research gaps.
          </p>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Project Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Graph Neural Networks for Algorithmic Reasoning"
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Research Topic / Domain
            </label>
            <input
              type="text"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder="e.g. Multi-Agent Reinforcement Learning, Graph Attention"
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Scope & Description
            </label>
            <textarea
              rows={3}
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              placeholder="Objectives and scope of this research project..."
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating || !newTitle.trim()}
              className="px-4 py-1.5 text-xs font-medium bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {isCreating ? (
                <>
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-3 h-3" />
                  Create Project
                </>
              )}
            </button>
          </div>
        </form>
      </ModalDialog>
    </div>
  );
};
export default Overview;
