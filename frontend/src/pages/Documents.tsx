import React, { useState } from 'react';
import { Upload, Trash2, FileText, CheckCircle2, Clock, AlertCircle, Search, Layers } from 'lucide-react';
import { Document } from '../types';
import { api } from '../services/api';

interface DocumentsProps {
  documents: Document[];
  onRefresh: () => void;
}

export const Documents: React.FC<DocumentsProps> = ({ documents, onRefresh }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Please select a valid PDF file.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(file);
      onRefresh();
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document and its vector embeddings?')) return;
    setDeletingId(id);
    try {
      await api.deleteDocument(id);
      onRefresh();
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = documents.filter(d =>
    d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
    (d.authors && d.authors.some(a => a.toLowerCase().includes(searchFilter.toLowerCase())))
  );

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Document Library</h2>
          <p className="text-xs text-slate-400">Manage research PDFs, inspect PyMuPDF extractions and vector chunking</p>
        </div>

        <div className="flex items-center gap-3">
          <label className="relative cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg text-sm transition shadow-lg shadow-emerald-500/20">
            <Upload className="w-4 h-4" />
            <span>{isUploading ? 'Ingesting PDF...' : 'Upload PDF Paper'}</span>
            <input
              type="file"
              accept=".pdf"
              disabled={isUploading}
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {uploadError && (
        <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search papers by title or author..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
        </div>
        <span className="text-xs text-slate-400">
          Showing {filtered.length} of {documents.length} papers
        </span>
      </div>

      {/* Documents Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/90 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6 font-semibold">Document Title</th>
                <th className="py-3.5 px-6 font-semibold">Authors</th>
                <th className="py-3.5 px-6 font-semibold">Pages</th>
                <th className="py-3.5 px-6 font-semibold">Chunks</th>
                <th className="py-3.5 px-6 font-semibold">Status</th>
                <th className="py-3.5 px-6 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="font-medium">No documents found</p>
                    <p className="text-xs mt-1">Upload research papers using the button above.</p>
                  </td>
                </tr>
              ) : (
                filtered.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-medium text-slate-100 max-w-sm truncate" title={doc.title}>
                            {doc.title}
                          </div>
                          <div className="text-xs text-slate-500 font-mono mt-0.5">
                            {doc.filename} • {(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-400 max-w-xs truncate">
                      {doc.authors && doc.authors.length > 0 ? doc.authors.join(', ') : 'Not detected'}
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-300 font-mono">
                      {doc.total_pages || '-'}
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-300 font-mono">
                      <span className="inline-flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-blue-400" />
                        {doc.chunk_count || 0}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          doc.processed_status === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : doc.processed_status === 'processing'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {doc.processed_status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                        {doc.processed_status === 'processing' && <Clock className="w-3 h-3" />}
                        {doc.processed_status === 'failed' && <AlertCircle className="w-3 h-3" />}
                        {doc.processed_status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        disabled={deletingId === doc.id}
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

