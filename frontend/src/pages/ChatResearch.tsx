import React, { useState } from 'react';
import { Send, Sparkles, BookOpen, Quote, ChevronRight, HelpCircle, Loader2 } from 'lucide-react';
import { Document, RAGResponse, Citation } from '../types';
import { api } from '../services/api';

interface ChatResearchProps {
  documents: Document[];
}

export const ChatResearch: React.FC<ChatResearchProps> = ({ documents }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);

  const examplePrompts = [
    "What are the central methodologies and experiments proposed in these papers?",
    "Summarize the key findings, conclusions, and quantitative results.",
    "What datasets or benchmarks were used to evaluate performance?",
    "What major limitations and future research directions do the authors highlight?"
  ];

  const handleAsk = async (textToSubmit?: string) => {
    const q = textToSubmit || query;
    if (!q.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.queryLiterature(q, 4, selectedDocs);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Failed to synthesize answer');
    } finally {
      setLoading(false);
    }
  };

  const toggleDocFilter = (id: string) => {
    setSelectedDocs(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            Literature Synthesis & RAG Assistant
          </h2>
          <p className="text-xs text-slate-400">
            Powered by local Ollama (qwen3:1.7b) and ChromaDB semantic chunk retrieval
          </p>
        </div>

        {/* Paper scope filter pills */}
        {documents.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400 font-medium">Scope:</span>
            <button
              onClick={() => setSelectedDocs([])}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition ${
                selectedDocs.length === 0
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              All Library ({documents.length})
            </button>
            {documents.slice(0, 3).map((d) => (
              <button
                key={d.id}
                onClick={() => toggleDocFilter(d.id)}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition truncate max-w-[140px] ${
                  selectedDocs.includes(d.id)
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
                title={d.title}
              >
                {d.title}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Prompt Input Box */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-lg focus-within:border-emerald-500/50 transition">
        <textarea
          rows={3}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleAsk();
            }
          }}
          placeholder="Ask a scientific question, hypothesis verification, or cross-paper synthesis query..."
          className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none"
        />

        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <span>Enter to submit • Shift+Enter for newline</span>
          </div>

          <button
            onClick={() => handleAsk()}
            disabled={!query.trim() || loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-semibold rounded-lg text-xs transition shadow-md shadow-emerald-500/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Synthesizing...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Ask Literature</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Suggested Prompts */}
      {!response && !loading && (
        <div className="space-y-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> Suggested Research Prompts
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {examplePrompts.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuery(p);
                  handleAsk(p);
                }}
                className="text-left p-3.5 bg-slate-900/50 hover:bg-slate-800/60 border border-slate-800 rounded-xl text-xs text-slate-300 hover:text-slate-100 transition group flex items-start justify-between gap-3"
              >
                <span>{p}</span>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 shrink-0 transition" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-sm text-rose-400">
          {error}
        </div>
      )}

      {/* Response Box */}
      {response && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Answer */}
          <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Synthesized Synthesis
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {response.duration_ms} ms • {response.model_used}
              </span>
            </div>

            <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed whitespace-pre-wrap">
              {response.answer}
            </div>
          </div>

          {/* Citations Column */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Quote className="w-4 h-4 text-emerald-400" />
              <h3 className="font-semibold text-sm text-slate-200">Grounded Citations</h3>
            </div>

            {response.citations.length === 0 ? (
              <p className="text-xs text-slate-500">No direct chunk citations.</p>
            ) : (
              <div className="space-y-3">
                {response.citations.map((cite, idx) => (
                  <div key={idx} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-300 truncate max-w-[180px]" title={cite.document_title}>
                        {cite.document_title}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {Math.round(cite.similarity_score * 100)}% match
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-normal line-clamp-4 italic">
                      "{cite.snippet}"
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

