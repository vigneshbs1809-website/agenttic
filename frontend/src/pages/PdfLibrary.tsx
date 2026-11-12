import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  Upload,
  RefreshCw,
  Trash2,
  ExternalLink,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Search,
  Filter,
  Eye,
  AlignLeft,
  X,
  FileCheck,
  FolderOpen
} from 'lucide-react';
import { Document, ResearchProjectItem } from '../types';
import { api } from '../services/api';
import { DataTable, Column } from '../components/common/DataTable';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { SearchInput } from '../components/common/SearchInput';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { ModalDialog } from '../components/common/ModalDialog';
import { LoadingState } from '../components/common/LoadingState';

interface PdfLibraryProps {
  documents: Document[];
  projects: ResearchProjectItem[];
  selectedProjectId?: string;
  onRefresh: () => void;
  onNavigate: (tab: string, contextId?: string) => void;
}

export const PdfLibrary: React.FC<PdfLibraryProps> = ({
  documents,
  projects,
  selectedProjectId,
  onRefresh,
  onNavigate
}) => {
  // Search & Filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [projectFilter, setProjectFilter] = useState<string>(selectedProjectId || 'all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Upload modal & Drag-and-drop state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadProject, setUploadProject] = useState<string>(selectedProjectId || '');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);

  // Metadata Inspector Modal State
  const [metadataDoc, setMetadataDoc] = useState<Document | null>(null);

  // Extracted Text Inspector Modal State
  const [textDoc, setTextDoc] = useState<Document | null>(null);
  const [sections, setSections] = useState<any[]>([]);
  const [loadingSections, setLoadingSections] = useState(false);
  const [sectionsError, setSectionsError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectedProjectId) {
      setProjectFilter(selectedProjectId);
      setUploadProject(selectedProjectId);
    }
  }, [selectedProjectId]);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes <= 0) return '0 KB';
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // File Validation Helper
  const validateAndAddFiles = (incomingFiles: FileList | File[]) => {
    setUploadError(null);
    const valid: File[] = [];
    const rejectedReasons: string[] = [];

    Array.from(incomingFiles).forEach((file) => {
      // 1. PDF extension & MIME validation
      const isPdf =
        file.type === 'application/pdf' ||
        file.name.toLowerCase().endsWith('.pdf');

      if (!isPdf) {
        rejectedReasons.push(`"${file.name}" is not a PDF.`);
        return;
      }

      // 2. Non-empty file validation
      if (file.size === 0) {
        rejectedReasons.push(`"${file.name}" is empty (0 bytes).`);
        return;
      }

      // 3. Max size check (100 MB limit)
      if (file.size > 100 * 1024 * 1024) {
        rejectedReasons.push(`"${file.name}" exceeds 100 MB limit.`);
        return;
      }

      valid.push(file);
    });

    if (rejectedReasons.length > 0) {
      setUploadError(`Some files were rejected:\n${rejectedReasons.join('\n')}`);
    }

    if (valid.length > 0) {
      setSelectedFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name));
        const newUnique = valid.filter((f) => !existingNames.has(f.name));
        return [...prev, ...newUnique];
      });
    }
  };

  // Drag and drop event handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const removeFileFromQueue = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Submit Uploads
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      if (selectedFiles.length === 1) {
        setUploadProgressText(`Uploading ${selectedFiles[0].name}...`);
        await api.uploadDocument(selectedFiles[0], uploadProject || undefined);
      } else {
        setUploadProgressText(`Batch processing ${selectedFiles.length} PDF documents...`);
        const result = await api.uploadBatchDocuments(selectedFiles, uploadProject || undefined);
        if (result.errors && result.errors.length > 0) {
          setUploadError(`Batch completed with warnings: ${result.errors.join('; ')}`);
        }
      }

      onRefresh();
      setIsUploadOpen(false);
      setSelectedFiles([]);
      setUploadProgressText('');
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload and process PDF documents');
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
    }
  };

  // Reprocess Document
  const handleReprocess = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionInProgressId(docId);
    try {
      await api.reprocessDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Reprocessing failed');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Delete Document
  const handleDelete = async (docId: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (
      !window.confirm(
        `Delete "${title}"?\nThis removes document text, metadata, and ChromaDB vector embeddings from SQLite.`
      )
    ) {
      return;
    }
    setActionInProgressId(docId);
    try {
      await api.deleteDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete document');
    } finally {
      setActionInProgressId(null);
    }
  };

  // View Extracted Text / Sections
  const handleOpenExtractedText = async (doc: Document, e: React.MouseEvent) => {
    e.stopPropagation();
    setTextDoc(doc);
    setLoadingSections(true);
    setSectionsError(null);
    try {
      const data = await api.getDocumentSections(doc.id);
      setSections(data);
    } catch (err: any) {
      setSectionsError(err.message || 'Failed to load extracted sections from SQLite');
    } finally {
      setLoadingSections(false);
    }
  };

  // Filtered documents
  const filteredDocs = documents.filter((doc) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !searchQuery.trim() ||
      (doc.title || '').toLowerCase().includes(q) ||
      (doc.filename || '').toLowerCase().includes(q) ||
      (doc.authors || []).some((a) => a.toLowerCase().includes(q));

    const matchesProject =
      projectFilter === 'all' || doc.project_id === projectFilter;

    const matchesStatus =
      statusFilter === 'all' || doc.processed_status === statusFilter;

    return matchesSearch && matchesProject && matchesStatus;
  });

  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;
  const paginatedDocs = filteredDocs.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Table Columns
  const columns: Column<Document>[] = [
    {
      key: 'filename',
      header: 'File Name',
      render: (doc) => (
        <div className="min-w-0 pr-4">
          <div className="flex items-center gap-1.5 font-medium text-gray-900 truncate font-mono text-xs">
            <FileText className="w-3.5 h-3.5 text-slate-700 shrink-0" />
            <span className="truncate">{doc.filename}</span>
          </div>
          <div className="text-[11px] text-gray-500 truncate mt-0.5 font-sans">
            {doc.title || 'Untitled Document'}
          </div>
        </div>
      )
    },
    {
      key: 'file_size_bytes',
      header: 'File Size',
      width: '100px',
      render: (doc) => (
        <span className="text-gray-600 font-mono text-xs">
          {formatFileSize(doc.file_size_bytes)}
        </span>
      )
    },
    {
      key: 'created_at',
      header: 'Upload Date',
      width: '110px',
      render: (doc) => (
        <span className="text-gray-500 text-[11px] font-mono">
          {new Date(doc.created_at).toLocaleDateString()}
        </span>
      )
    },
    {
      key: 'processed_status',
      header: 'Processing Status',
      width: '130px',
      render: (doc) => (
        <div className="flex items-center gap-1.5">
          <StatusIndicator status={doc.processed_status} size="sm" />
          {actionInProgressId === doc.id && (
            <span className="w-3 h-3 border-2 border-slate-700/30 border-t-slate-700 rounded-full animate-spin shrink-0" />
          )}
        </div>
      )
    },
    {
      key: 'project_id',
      header: 'Associated Project',
      width: '160px',
      render: (doc) => {
        const proj = projects.find((p) => p.id === doc.project_id);
        return (
          <span className="text-gray-600 text-xs truncate block" title={proj?.title}>
            {proj ? (
              <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700 text-[11px] font-medium truncate inline-block max-w-[140px]">
                {proj.title}
              </span>
            ) : (
              <span className="text-gray-400 text-xs">Workspace</span>
            )}
          </span>
        );
      }
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '180px',
      render: (doc) => (
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setMetadataDoc(doc);
            }}
            className="text-xs text-gray-600 hover:text-gray-900 transition-colors p-1"
            title="View Extracted Metadata"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={(e) => handleOpenExtractedText(doc, e)}
            className="text-xs text-gray-600 hover:text-gray-900 transition-colors p-1"
            title="View Extracted Sections & Text"
          >
            <AlignLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={(e) => handleReprocess(doc.id, e)}
            disabled={actionInProgressId === doc.id}
            className="text-xs text-gray-600 hover:text-gray-900 disabled:opacity-40 transition-colors p-1"
            title="Reprocess Document"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={(e) => handleDelete(doc.id, doc.filename, e)}
            disabled={actionInProgressId === doc.id}
            className="text-xs text-rose-600 hover:text-rose-800 disabled:opacity-40 transition-colors p-1"
            title="Delete Document"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-800" />
            PDF Document Library & Ingestion
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Section-aware PDF parser and persistent document indexer. Manage uploaded files, extracted sections, and vector embeddings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload PDFs</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="w-full sm:w-64">
            <SearchInput
              value={searchQuery}
              onChange={(q) => {
                setSearchQuery(q);
                setCurrentPage(1);
              }}
              placeholder="Search filename, title, or authors..."
            />
          </div>

          {/* Project Filter */}
          <select
            value={projectFilter}
            onChange={(e) => {
              setProjectFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-700 focus:outline-none focus:ring-1 focus:ring-slate-900 max-w-xs truncate"
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>

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
            <option value="completed">Completed</option>
            <option value="metadata_only">Metadata Only</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>

          {(searchQuery || projectFilter !== 'all' || statusFilter !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setProjectFilter('all');
                setStatusFilter('all');
                setCurrentPage(1);
              }}
              className="text-xs text-slate-800 hover:text-slate-950 font-medium underline px-1"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="text-xs text-gray-500 whitespace-nowrap">
          Showing <span className="font-semibold text-gray-800">{filteredDocs.length}</span> of {documents.length} documents
        </div>
      </div>

      {/* Document Library Table */}
      {filteredDocs.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center space-y-4">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto text-gray-500">
            <FileText className="w-6 h-6 text-slate-700" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              No documents found
            </h3>
            <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
              {searchQuery || projectFilter !== 'all' || statusFilter !== 'all'
                ? 'No documents match the specified search or filter criteria.'
                : 'Upload research PDFs to catalog them in SQLite and generate section-aware vector embeddings.'}
            </p>
          </div>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold shadow-xs transition-colors inline-flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload First PDF</span>
          </button>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedDocs}
          rowKey={(doc) => doc.id}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          totalItems={filteredDocs.length}
          pageSize={pageSize}
          onRowClick={(doc) => onNavigate('analysis', doc.id)}
        />
      )}

      {/* DRAG-AND-DROP & MULTIPLE UPLOAD MODAL */}
      <ModalDialog
        isOpen={isUploadOpen}
        onClose={() => {
          if (!isUploading) {
            setIsUploadOpen(false);
            setSelectedFiles([]);
            setUploadError(null);
          }
        }}
        title="Upload Academic PDF Documents"
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          {uploadError && <ErrorMessage message={uploadError} onDismiss={() => setUploadError(null)} />}

          {/* Target Project Selection */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Associate with Project Workspace
            </label>
            <select
              value={uploadProject}
              onChange={(e) => setUploadProject(e.target.value)}
              disabled={isUploading}
              className="w-full px-3 py-1.5 text-xs bg-white border border-gray-300 rounded text-gray-800 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="">General Workspace (Unassigned)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-slate-900 bg-slate-50'
                : 'border-gray-300 hover:border-gray-400 bg-gray-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              onChange={(e) => {
                if (e.target.files) validateAndAddFiles(e.target.files);
              }}
              className="hidden"
            />
            <div className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center mx-auto mb-2 text-slate-800">
              <Upload className="w-5 h-5" />
            </div>
            <p className="text-xs font-semibold text-gray-800">
              Drag & drop PDF files here, or <span className="text-slate-900 underline">browse</span>
            </p>
            <p className="text-[11px] text-gray-500 mt-1">
              Multiple files supported &bull; PDF documents only &bull; Up to 100 MB per file
            </p>
          </div>

          {/* Queue of Selected Files */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
                <span>Selected Documents ({selectedFiles.length})</span>
                <button
                  type="button"
                  onClick={() => setSelectedFiles([])}
                  disabled={isUploading}
                  className="text-[11px] text-rose-600 hover:underline"
                >
                  Clear All
                </button>
              </div>

              <div className="max-h-36 overflow-y-auto space-y-1.5 border border-gray-200 rounded p-2 bg-white">
                {selectedFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs p-1.5 bg-gray-50 rounded border border-gray-100"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span className="font-mono text-gray-800 truncate">{file.name}</span>
                      <span className="text-gray-400 font-mono text-[10px]">
                        ({formatFileSize(file.size)})
                      </span>
                    </div>
                    {!isUploading && (
                      <button
                        type="button"
                        onClick={() => removeFileFromQueue(idx)}
                        className="text-gray-400 hover:text-rose-600 p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progress / Status feedback */}
          {uploadProgressText && (
            <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800 flex items-center gap-2">
              <span className="w-3 h-3 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
              <span>{uploadProgressText}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
            <button
              type="button"
              disabled={isUploading}
              onClick={() => {
                setIsUploadOpen(false);
                setSelectedFiles([]);
              }}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || selectedFiles.length === 0}
              className="px-4 py-1.5 text-xs font-semibold bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {isUploading ? (
                <>
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing Ingestion...
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  Upload & Process {selectedFiles.length > 0 ? `(${selectedFiles.length})` : ''}
                </>
              )}
            </button>
          </div>
        </form>
      </ModalDialog>

      {/* METADATA INSPECTOR MODAL */}
      <ModalDialog
        isOpen={Boolean(metadataDoc)}
        onClose={() => setMetadataDoc(null)}
        title="Extracted Document Metadata"
      >
        {metadataDoc && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-gray-50 border border-gray-200 rounded space-y-2">
              <div>
                <span className="font-semibold text-gray-500 uppercase tracking-wider block text-[10px]">
                  Paper Title
                </span>
                <p className="font-medium text-gray-900 mt-0.5">
                  {metadataDoc.title || metadataDoc.filename}
                </p>
              </div>

              <div>
                <span className="font-semibold text-gray-500 uppercase tracking-wider block text-[10px]">
                  Authors
                </span>
                <p className="text-gray-800 mt-0.5">
                  {metadataDoc.authors && metadataDoc.authors.length > 0
                    ? metadataDoc.authors.join(', ')
                    : 'Not Reported'}
                </p>
              </div>

              {metadataDoc.abstract && (
                <div>
                  <span className="font-semibold text-gray-500 uppercase tracking-wider block text-[10px]">
                    Abstract
                  </span>
                  <p className="text-gray-700 mt-0.5 leading-relaxed max-h-32 overflow-y-auto">
                    {metadataDoc.abstract}
                  </p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 font-mono">
              <div className="p-2 border border-gray-200 rounded">
                <span className="text-gray-500 block text-[10px]">Publication Year</span>
                <span className="text-gray-900 font-semibold">{metadataDoc.publication_year || '—'}</span>
              </div>
              <div className="p-2 border border-gray-200 rounded">
                <span className="text-gray-500 block text-[10px]">Total Pages</span>
                <span className="text-gray-900 font-semibold">{metadataDoc.total_pages || 1}</span>
              </div>
              <div className="p-2 border border-gray-200 rounded">
                <span className="text-gray-500 block text-[10px]">File Size</span>
                <span className="text-gray-900 font-semibold">{formatFileSize(metadataDoc.file_size_bytes)}</span>
              </div>
              <div className="p-2 border border-gray-200 rounded">
                <span className="text-gray-500 block text-[10px]">Section Chunks</span>
                <span className="text-gray-900 font-semibold">{metadataDoc.chunk_count}</span>
              </div>
            </div>

            {metadataDoc.doi && (
              <div className="p-2 border border-gray-200 rounded font-mono text-[11px]">
                <span className="text-gray-500 block text-[10px]">DOI</span>
                <span className="text-gray-800">{metadataDoc.doi}</span>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setMetadataDoc(null)}
                className="px-3 py-1.5 text-xs bg-slate-900 text-white rounded hover:bg-slate-800 font-medium"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </ModalDialog>

      {/* EXTRACTED TEXT & SECTIONS INSPECTOR MODAL */}
      <ModalDialog
        isOpen={Boolean(textDoc)}
        onClose={() => setTextDoc(null)}
        title={`Extracted Text & Sections: ${textDoc?.filename || 'Document'}`}
      >
        <div className="space-y-3 text-xs">
          {loadingSections ? (
            <div className="py-8">
              <LoadingState message="Retrieving parsed academic sections from SQLite..." />
            </div>
          ) : sectionsError ? (
            <ErrorMessage message={sectionsError} onDismiss={() => setSectionsError(null)} />
          ) : sections.length === 0 ? (
            <p className="text-xs text-gray-500 py-6 text-center">
              No sections extracted for this document. If this paper was added via metadata only, upload a PDF to extract text.
            </p>
          ) : (
            <div className="max-h-[480px] overflow-y-auto space-y-3 pr-1">
              {sections.map((sec: any, idx: number) => (
                <div key={sec.id || idx} className="p-3 bg-gray-50 border border-gray-200 rounded space-y-1.5">
                  <div className="flex items-center justify-between border-b border-gray-200 pb-1">
                    <span className="font-semibold text-gray-900 font-mono text-xs">
                      §{sec.section_index || idx + 1}. {sec.section_title || 'Section'}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200">
                      Page {sec.page_number || 'N/A'} &bull; {sec.token_count || 0} tokens
                    </span>
                  </div>
                  <p className="text-xs text-gray-800 font-mono leading-relaxed whitespace-pre-wrap">
                    {sec.preview_text || sec.content || 'No text extracted.'}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setTextDoc(null)}
              className="px-3 py-1.5 text-xs bg-slate-900 text-white rounded hover:bg-slate-800 font-medium"
            >
              Done
            </button>
          </div>
        </div>
      </ModalDialog>
    </div>
  );
};
export default PdfLibrary;
