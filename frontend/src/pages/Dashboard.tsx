import React from 'react';
import { BookOpen, Layers, Share2, Cpu, ArrowUpRight, Upload, Search, Sparkles } from 'lucide-react';
import { Document, SystemHealth } from '../types';

interface DashboardProps {
  documents: Document[];
  health: SystemHealth | null;
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ documents, health, onNavigate }) => {
  const completedDocs = documents.filter(d => d.processed_status === 'completed');
  const totalChunks = documents.reduce((acc, curr) => acc + (curr.chunk_count || 0), 0);

  const stats = [
    {
      title: 'Literature Papers',
      value: documents.length,
      sub: `${completedDocs.length} fully indexed`,
      icon: BookOpen,
      color: 'emerald',
    },
    {
      title: 'Vector Chunks',
      value: totalChunks,
      sub: 'ChromaDB persistent',
      icon: Layers,
      color: 'blue',
    },
    {
      title: 'Local Intelligence',
      value: health?.ollama_connected ? 'Active' : 'Standby',
      sub: `${health?.ollama_model || 'qwen3:1.7b'} (CPU)`,
      icon: Cpu,
      color: 'teal',
    },
    {
      title: 'Knowledge Graph',
      value: completedDocs.length > 0 ? `${completedDocs.length * 3}+ Nodes` : '0 Nodes',
      sub: 'NetworkX co-occurrence',
      icon: Share2,
      color: 'purple',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-slate-800 p-8">
        <div className="relative z-10 space-y-3 max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Windows 11 & 8 GB RAM Optimized
          </span>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            Scientific Literature Intelligence Platform
          </h2>
          <p className="text-slate-400 text-sm leading-relaxed">
            Ingest scientific PDFs locally, extract semantic chunks via PyMuPDF, search with nomic-embed-text vectors,
            synthesize cross-paper insights using local Qwen, and explore relational knowledge graphs.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => onNavigate('orchestrator')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-semibold rounded-lg text-sm transition shadow-lg shadow-emerald-500/20"
            >
              <Sparkles className="w-4 h-4" />
              Run 8-Agent Workflow
            </button>
            <button
              onClick={() => onNavigate('documents')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg text-sm transition border border-slate-700"
            >
              <Upload className="w-4 h-4" />
              Upload Papers
            </button>
            <button
              onClick={() => onNavigate('chat')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg text-sm transition border border-slate-700"
            >
              <Search className="w-4 h-4" />
              Synthesize Research
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 transition-all">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{stat.title}</span>
                <div className="p-2 bg-slate-800/80 rounded-lg text-emerald-400">
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-slate-100">{stat.value}</div>
                <div className="text-xs text-slate-400 mt-1">{stat.sub}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column: Recent Papers & System Architecture Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Recent Papers */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800/80 rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="font-semibold text-slate-100 text-base">Recent Literature</h3>
              <p className="text-xs text-slate-400">Latest research papers added to your local library</p>
            </div>
            <button
              onClick={() => onNavigate('documents')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
            >
              View all ({documents.length})
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-800 rounded-lg">
              <BookOpen className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-400 font-medium">No documents in library yet</p>
              <p className="text-xs text-slate-500 mt-1">Upload PDF research papers to initialize vector indexing</p>
              <button
                onClick={() => onNavigate('documents')}
                className="mt-4 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg text-slate-200 border border-slate-700 transition"
              >
                Upload First PDF
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {documents.slice(0, 5).map((doc) => (
                <div key={doc.id} className="py-3.5 flex items-center justify-between">
                  <div className="space-y-1 max-w-md">
                    <h4 className="text-sm font-medium text-slate-200 truncate">{doc.title}</h4>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>{doc.authors && doc.authors.length > 0 ? doc.authors.join(', ') : 'Unknown Authors'}</span>
                      {doc.total_pages && <span>• {doc.total_pages} pages</span>}
                      <span>• {(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      doc.processed_status === 'completed'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : doc.processed_status === 'processing'
                        ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {doc.processed_status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: 8GB Memory Allocation Monitor */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 space-y-5">
          <div>
            <h3 className="font-semibold text-slate-100 text-base">Resource Budget (8 GB)</h3>
            <p className="text-xs text-slate-400">Strict allocation to avoid Windows paging/thrashing</p>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
                <span>Ollama (qwen3:1.7b)</span>
                <span>~1.5 GB</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-teal-400 rounded-full" style={{ width: '22%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
                <span>ChromaDB Vector Store</span>
                <span>~0.3 GB</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-400 rounded-full" style={{ width: '5%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
                <span>FastAPI + SQLite + PyMuPDF</span>
                <span>~0.3 GB</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-400 rounded-full" style={{ width: '5%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
                <span>Windows 11 OS Reserved</span>
                <span>~3.5 GB</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-slate-600 rounded-full" style={{ width: '45%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-emerald-400 mb-1.5 font-mono font-medium">
                <span>Available Headroom Safety</span>
                <span>~2.4 GB</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500/40 rounded-full" style={{ width: '23%' }} />
              </div>
            </div>
          </div>

          <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg text-xs text-slate-400 space-y-1">
            <span className="font-semibold text-slate-300 block">Engineering Rule:</span>
            <span>Ollama keep-alive is configured to 5m to automatically unload LLM weights from host RAM when idle.</span>
          </div>
        </div>
      </div>
    </div>
  );
};

