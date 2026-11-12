import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  BarChart2,
  PieChart as PieIcon,
  RefreshCw,
  BookOpen,
  Calendar,
  Layers,
  Cpu,
  AlertTriangle,
  Compass,
  Sparkles,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
  AreaChart,
  Area,
  Legend
} from 'recharts';
import {
  ResearchProjectItem,
  ResearchTrendsResponse,
  YearTrend,
  AlgorithmTrend,
  DatasetTrend,
  TopicTrend,
  LimitationTrend,
  EmergingDirectionTrend,
  UnderexploredArea
} from '../types';
import { api } from '../services/api';

const COLORS = [
  '#10b981', // emerald-500
  '#06b6d4', // cyan-500
  '#3b82f6', // blue-500
  '#8b5cf6', // purple-500
  '#f59e0b', // amber-500
  '#ec4899', // pink-500
  '#14b8a6', // teal-500
  '#6366f1', // indigo-500
];

export const TrendAnalysis: React.FC = () => {
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [trends, setTrends] = useState<ResearchTrendsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
      loadTrends('');
    } catch (err) {
      console.warn('Could not load projects', err);
      loadTrends('');
    }
  };

  const loadTrends = async (projId: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      let res: ResearchTrendsResponse;
      if (projId) {
        res = await api.getProjectTrends(projId);
      } else {
        res = await api.getCorpusTrends();
      }
      setTrends(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load research trends');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProjectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const pId = e.target.value;
    setSelectedProjectId(pId);
    loadTrends(pId);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Module B: Empirical Literature Analytics
            </span>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              100% Genuine SQLite Aggregations (Zero Fabricated Trends)
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 mt-1">Research Trend Analysis</h1>
          <p className="text-sm text-slate-400">
            Multi-dimensional longitudinal analytics computed directly from SQLite records: publication trajectories, frequently used algorithms and benchmarks, research topic distributions, recurring limitations, and underexplored areas.
          </p>
        </div>

        {/* Project Selector & Refresh */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2">
            <BookOpen className="w-4 h-4 text-emerald-400" />
            <select
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="bg-transparent text-xs text-slate-200 focus:outline-none"
            >
              <option value="" className="bg-slate-900">
                -- All Literature Corpus --
              </option>
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-900">
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => loadTrends(selectedProjectId)}
            disabled={isLoading}
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl transition-colors disabled:opacity-50"
            title="Refresh trends"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Bar */}
      {trends && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 uppercase font-semibold">Analyzed Papers</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
              {trends.total_papers_analyzed}
            </div>
            <span className="text-[11px] text-slate-500">Indexed in SQLite database</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 uppercase font-semibold">Structured Analyses</span>
            <div className="text-2xl font-bold text-teal-400 mt-1 font-mono">
              {trends.total_analyses_analyzed}
            </div>
            <span className="text-[11px] text-slate-500">14-dimension deep dives</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 uppercase font-semibold">Identified Gaps</span>
            <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
              {trends.total_gaps_analyzed}
            </div>
            <span className="text-[11px] text-slate-500">Explicit and implicit gaps</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 uppercase font-semibold">Unique Algorithms</span>
            <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">
              {trends.top_algorithms.length}
            </div>
            <span className="text-[11px] text-slate-500">Extracted from methodologies</span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-400 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Charts Grid */}
      {trends && (
        <div className="space-y-6">
          {/* Row 1: Publications by Year & Topic Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 1. Publications by Year */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-200">Publications by Year</h3>
                </div>
                <span className="text-xs text-slate-400">Annual & Cumulative</span>
              </div>
              <p className="text-xs text-slate-400">
                Temporal distribution of research papers across the ingested corpus.
              </p>

              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trends.publications_by_year}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                    <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                      itemStyle={{ color: '#34d399' }}
                    />
                    <Bar dataKey="paper_count" name="Papers Published" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 2. Research Topic Distribution */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <PieIcon className="w-4 h-4 text-teal-400" />
                  <h3 className="text-sm font-bold text-slate-200">Research Topic Distribution</h3>
                </div>
                <span className="text-xs text-slate-400">Categorical Breakdown</span>
              </div>
              <p className="text-xs text-slate-400">
                Core conceptual domains represented across the analyzed research corpus.
              </p>

              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={trends.topic_distribution}
                      dataKey="count"
                      nameKey="topic"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                      fontSize={11}
                    >
                      {trends.topic_distribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Row 2: Frequently Used Algorithms & Frequently Used Datasets */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 3. Frequently Used Algorithms */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-400" />
                  <h3 className="text-sm font-bold text-slate-200">Frequently Used Algorithms</h3>
                </div>
                <span className="text-xs text-slate-400">Methodology Entities</span>
              </div>
              <p className="text-xs text-slate-400">
                Most recurring algorithmic architectures, models, and optimization protocols.
              </p>

              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    layout="vertical"
                    data={trends.top_algorithms}
                    margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                    <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      stroke="#94a3b8"
                      fontSize={10}
                      width={120}
                      tickFormatter={(val) => (val.length > 18 ? `${val.slice(0, 18)}...` : val)}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                      formatter={(val: any, name: any, item: any) => [
                        `${val} papers (${item.payload.percentage}%)`,
                        'Usage Frequency',
                      ]}
                    />
                    <Bar dataKey="count" name="Paper Count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 4. Frequently Evaluated Datasets */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-400" />
                  <h3 className="text-sm font-bold text-slate-200">Frequently Evaluated Datasets</h3>
                </div>
                <span className="text-xs text-slate-400">Experimental Benchmarks</span>
              </div>
              <p className="text-xs text-slate-400">
                Primary benchmarks and simulation environments utilized in experimental evaluations.
              </p>

              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    layout="vertical"
                    data={trends.top_datasets}
                    margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                    <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      stroke="#94a3b8"
                      fontSize={10}
                      width={120}
                      tickFormatter={(val) => (val.length > 18 ? `${val.slice(0, 18)}...` : val)}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                      formatter={(val: any, name: any, item: any) => [
                        `${val} papers (${item.payload.percentage}%)`,
                        'Evaluated Frequency',
                      ]}
                    />
                    <Bar dataKey="count" name="Paper Count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Row 3: Common Limitations */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-200">Common Research Limitations</h3>
              </div>
              <span className="text-xs text-slate-400">Recurring Literature Bottlenecks</span>
            </div>
            <p className="text-xs text-slate-400">
              Frequently cited bottlenecks explicitly stated by paper authors and synthesized across gap analyses.
            </p>

            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trends.common_limitations}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                  <XAxis
                    dataKey="limitation"
                    stroke="#94a3b8"
                    fontSize={10}
                    tickFormatter={(val) => (val.length > 20 ? `${val.slice(0, 20)}...` : val)}
                  />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                    formatter={(val: any, name: any, item: any) => [
                      `${val} papers citing [${item.payload.category}]`,
                      'Citations Count',
                    ]}
                  />
                  <Bar dataKey="count" name="Citation Frequency" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Row 4: Emerging Research Directions & Underexplored Areas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Emerging Directions */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-200">Emerging Research Directions</h3>
                </div>
                <span className="text-xs text-emerald-400 font-semibold">Future Trajectories</span>
              </div>
              <p className="text-xs text-slate-400">
                Actionable research avenues recommended in author future work and system-inferred opportunities.
              </p>

              <div className="space-y-2.5 max-h-80 overflow-y-auto">
                {trends.emerging_directions.map((ed, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-200">{ed.direction}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        Score: {ed.recency_score}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span>Suggested across {ed.mention_count} paper future work sections</span>
                      <span className="text-slate-500 truncate max-w-[150px]">
                        {ed.suggested_by[0] || ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Underexplored Areas */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-slate-200">Underexplored Research Frontiers</h3>
                </div>
                <span className="text-xs text-cyan-400 font-semibold">High Potential Gaps</span>
              </div>
              <p className="text-xs text-slate-400">
                Documented research gaps with zero or minimal evaluated implementations in the analyzed corpus.
              </p>

              <div className="space-y-2.5 max-h-80 overflow-y-auto">
                {trends.underexplored_areas.map((ua, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-200">{ua.area}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 uppercase">
                        {ua.gap_category}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{ua.reason}</p>
                    <div className="text-[10px] text-slate-500 flex items-center gap-2">
                      <span>Identified in gaps: {ua.identified_in_gaps}</span>
                      <span>•</span>
                      <span className={ua.evaluated_in_papers === 0 ? 'text-amber-400 font-semibold' : ''}>
                        Evaluated implementations: {ua.evaluated_in_papers}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

