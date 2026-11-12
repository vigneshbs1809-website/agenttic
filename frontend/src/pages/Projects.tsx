import React, { useState, useEffect } from 'react';
import {
  FolderKanban,
  Plus,
  Trash2,
  Edit2,
  ExternalLink,
  BookOpen,
  CheckCircle2,
  Calendar,
  Layers,
  Search,
  Filter,
  ArrowRight,
  FolderOpen,
  FileText
} from 'lucide-react';
import { ResearchProjectItem, Document } from '../types';
import { api } from '../services/api';
import { DataTable, Column } from '../components/common/DataTable';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { SearchInput } from '../components/common/SearchInput';
import { ModalDialog } from '../components/common/ModalDialog';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LoadingState } from '../components/common/LoadingState';

interface ProjectsProps {
  projects?: ResearchProjectItem[];
  onSelectActiveProject?: (id: string) => void;
  selectedProjectId?: string;
  onNavigate: (tab: string, contextId?: string) => void;
}

export const Projects: React.FC<ProjectsProps> = ({
  projects: initialProjects = [],
  onSelectActiveProject,
  selectedProjectId,
  onNavigate
}) => {
  const [projects, setProjects] = useState<ResearchProjectItem[]>(initialProjects);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  // Create Project Dialog State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit Project Dialog State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<ResearchProjectItem | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDomain, setEditDomain] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editStatus, setEditStatus] = useState('active');
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load research projects from SQLite');
    } finally {
      setIsLoading(false);
    }
  };

  // 1. Create Project
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await api.createProject({
        title: newTitle.trim(),
        domain: newDomain.trim() || undefined,
        description: newDescription.trim() || undefined
      });
      setProjects((prev) => [created, ...prev]);
      if (onSelectActiveProject) {
        onSelectActiveProject(created.id);
      }
      setIsCreateOpen(false);
      setNewTitle('');
      setNewDomain('');
      setNewDescription('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 2. Open Edit Project Modal
  const openEditModal = (proj: ResearchProjectItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingProject(proj);
    setEditTitle(proj.title);
    setEditDomain(proj.domain || '');
    setEditDescription(proj.description || '');
    setEditStatus(proj.status || 'active');
    setIsEditOpen(true);
  };

  // 3. Save Edited Project
  const handleUpdateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject || !editTitle.trim()) return;

    setIsUpdating(true);
    setErrorMsg(null);
    try {
      const updated = await api.updateProject(editingProject.id, {
        title: editTitle.trim(),
        domain: editDomain.trim() || undefined,
        description: editDescription.trim() || undefined,
        status: editStatus
      });
      setProjects((prev) =>
        prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
      );
      setIsEditOpen(false);
      setEditingProject(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update project');
    } finally {
      setIsUpdating(false);
    }
  };

  // 4. Delete Project
  const handleDeleteProject = async (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (
      !window.confirm(
        `Are you sure you want to delete project "${title}"?\nThis will cascade delete its papers, gaps, and analyses from SQLite.`
      )
    ) {
      return;
    }
    try {
      await api.deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      if (selectedProjectId === id && onSelectActiveProject) {
        onSelectActiveProject('');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete project');
    }
  };

  // 5. Open Project Workspace (sets as active and navigates to PDF library)
  const handleOpenProject = (projId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (onSelectActiveProject) {
      onSelectActiveProject(projId);
    }
    onNavigate('library', projId);
  };

  // Unique domains for filtering
  const availableDomains = Array.from(
    new Set(projects.map((p) => p.domain).filter(Boolean) as string[])
  );

  // Filter projects
  const filteredProjects = projects.filter((p) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !searchQuery.trim() ||
      p.title.toLowerCase().includes(q) ||
      (p.domain || '').toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q);

    const matchesStatus = statusFilter === 'all' || p.status === statusFilter;
    const matchesDomain = domainFilter === 'all' || p.domain === domainFilter;

    return matchesSearch && matchesStatus && matchesDomain;
  });

  const totalPages = Math.ceil(filteredProjects.length / pageSize) || 1;
  const paginatedProjects = filteredProjects.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const columns: Column<ResearchProjectItem>[] = [
    {
      key: 'title',
      header: 'Project Title',
      render: (proj) => {
        const isCurrent = proj.id === selectedProjectId;
        return (
          <div className="min-w-0 pr-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900 truncate">
                {proj.title}
              </span>
              {isCurrent && (
                <span className="px-1.5 py-0.2 bg-slate-900 text-white text-[10px] rounded font-medium">
                  Active Workspace
                </span>
              )}
            </div>
            {proj.description && (
              <p className="text-[11px] text-gray-500 truncate mt-0.5">
                {proj.description}
              </p>
            )}
          </div>
        );
      }
    },
    {
      key: 'domain',
      header: 'Research Topic',
      width: '160px',
      render: (proj) => (
        <span className="text-gray-600 text-xs truncate block">
          {proj.domain ? (
            <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700 text-[11px] font-medium">
              {proj.domain}
            </span>
          ) : (
            <span className="text-gray-400 text-xs">—</span>
          )}
        </span>
      )
    },
    {
      key: 'paper_count',
      header: 'Papers',
      width: '90px',
      render: (proj) => (
        <span className="font-mono text-xs text-gray-700 font-medium">
          {proj.paper_count || 0}
        </span>
      )
    },
    {
      key: 'status',
      header: 'Processing Status',
      width: '120px',
      render: (proj) => (
        <StatusIndicator status={proj.status || 'active'} size="sm" />
      )
    },
    {
      key: 'created_at',
      header: 'Creation Date',
      width: '110px',
      render: (proj) => (
        <span className="text-gray-500 text-[11px]">
          {new Date(proj.created_at).toLocaleDateString()}
        </span>
      )
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '180px',
      render: (proj) => {
        const isCurrent = proj.id === selectedProjectId;
        return (
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={(e) => handleOpenProject(proj.id, e)}
              className="text-xs text-slate-900 hover:underline font-semibold flex items-center gap-1"
              title="Open Project Workspace"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>{isCurrent ? 'Open' : 'Select'}</span>
            </button>
            <span className="text-gray-300">|</span>
            <button
              type="button"
              onClick={(e) => openEditModal(proj, e)}
              className="text-xs text-gray-600 hover:text-gray-900 transition-colors"
              title="Edit Project"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
            <span className="text-gray-300">|</span>
            <button
              type="button"
              onClick={(e) => handleDeleteProject(proj.id, proj.title, e)}
              className="text-xs text-rose-600 hover:text-rose-800 transition-colors"
              title="Delete Project"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      }
    }
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-slate-800" />
            My Research Projects
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Organize research literature, cross-paper comparison matrixes, and identified gaps into isolated workspaces.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors self-start md:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Research Project</span>
        </button>
      </div>

      {/* Error Message */}
      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Search, Filter, and Status Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="w-full sm:w-64">
            <SearchInput
              value={searchQuery}
              onChange={(q) => {
                setSearchQuery(q);
                setCurrentPage(1);
              }}
              placeholder="Search by title, topic, or description..."
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-700 focus:outline-none focus:ring-1 focus:ring-slate-900"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>

          {/* Topic / Domain Filter */}
          {availableDomains.length > 0 && (
            <select
              value={domainFilter}
              onChange={(e) => {
                setDomainFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-700 focus:outline-none focus:ring-1 focus:ring-slate-900 max-w-xs truncate"
            >
              <option value="all">All Topics / Domains</option>
              {availableDomains.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          )}

          {(searchQuery || statusFilter !== 'all' || domainFilter !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
                setDomainFilter('all');
                setCurrentPage(1);
              }}
              className="text-xs text-slate-800 hover:text-slate-950 font-medium underline px-1"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="text-xs text-gray-500 whitespace-nowrap">
          Showing <span className="font-semibold text-gray-800">{filteredProjects.length}</span> of {projects.length} projects
        </div>
      </div>

      {/* Projects Table & Clean Empty States */}
      {isLoading ? (
        <div className="py-12 bg-white border border-gray-200 rounded-lg">
          <LoadingState message="Loading research projects from SQLite..." />
        </div>
      ) : projects.length === 0 ? (
        /* Empty State: No projects at all */
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center space-y-4">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto text-gray-500">
            <FolderKanban className="w-6 h-6 text-slate-700" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              No research projects found
            </h3>
            <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
              Create your first research project workspace to catalog literature, execute cross-paper comparisons, and discover research gaps.
            </p>
          </div>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create First Project</span>
          </button>
        </div>
      ) : filteredProjects.length === 0 ? (
        /* Empty State: Filter mismatch */
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center space-y-3">
          <p className="text-xs text-gray-500">
            No projects match the current filter or search criteria.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('all');
              setDomainFilter('all');
            }}
            className="text-xs text-slate-800 font-semibold underline"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedProjects}
          rowKey={(proj) => proj.id}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          totalItems={filteredProjects.length}
          pageSize={pageSize}
          onRowClick={(proj) => handleOpenProject(proj.id)}
        />
      )}

      {/* CREATE PROJECT MODAL */}
      <ModalDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Research Project"
      >
        <form onSubmit={handleCreateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Project Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Graph Attention Networks for Spatial Routing"
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
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
              placeholder="e.g. Multi-Agent Reinforcement Learning"
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
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
              placeholder="Describe the research objectives and questions investigated in this project..."
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-none font-sans"
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
              disabled={isSubmitting || !newTitle.trim()}
              className="px-4 py-1.5 text-xs font-medium bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-3.5 h-3.5" />
                  Create Project
                </>
              )}
            </button>
          </div>
        </form>
      </ModalDialog>

      {/* EDIT PROJECT MODAL */}
      <ModalDialog
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Research Project"
      >
        <form onSubmit={handleUpdateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Project Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Research Topic / Domain
            </label>
            <input
              type="text"
              value={editDomain}
              onChange={(e) => setEditDomain(e.target.value)}
              placeholder="e.g. Multi-Agent Reinforcement Learning"
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Processing Status
            </label>
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value)}
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="active">active (Active Workspace)</option>
              <option value="completed">completed (Completed Research)</option>
              <option value="archived">archived (Archived)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Scope & Description
            </label>
            <textarea
              rows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setIsEditOpen(false)}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUpdating || !editTitle.trim()}
              className="px-4 py-1.5 text-xs font-medium bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {isUpdating ? (
                <>
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </ModalDialog>
    </div>
  );
};
export default Projects;
