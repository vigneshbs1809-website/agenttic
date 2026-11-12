import React, { useState, useEffect } from 'react';
import { Share2, RefreshCw, Filter, Layers, Info } from 'lucide-react';
import { GraphData, GraphNode } from '../types';
import { api } from '../services/api';

export const GraphExplorer: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const data = await api.getGraphOverview();
      setGraphData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Filter nodes
  const filteredNodes = nodes.filter(n => filterType === 'all' || n.type === filterType);
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = edges.filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));

  // Layout positions in a clean circular / clustered arrangement
  const width = 800;
  const height = 500;
  const centerX = width / 2;
  const centerY = height / 2;

  const nodePositions = new Map<string, { x: number; y: number }>();
  filteredNodes.forEach((node, idx) => {
    const angle = (idx / (filteredNodes.length || 1)) * 2 * Math.PI;
    const radius = node.type === 'document' ? 140 : 210;
    nodePositions.set(node.id, {
      x: centerX + radius * Math.cos(angle) + (Math.sin(idx * 3) * 15),
      y: centerY + radius * Math.sin(angle) + (Math.cos(idx * 2) * 15),
    });
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Share2 className="w-5 h-5 text-emerald-400" />
            Knowledge Graph Explorer
          </h2>
          <p className="text-xs text-slate-400">
            NetworkX relational network connecting research papers, authors, and cross-cutting concepts
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Filter selector */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-2" />
            {['all', 'document', 'concept', 'author'].map(t => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-2.5 py-1 rounded capitalize font-medium transition ${
                  filterType === t
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <button
            onClick={fetchGraph}
            disabled={loading}
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-lg text-xs transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Canvas + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* SVG Visualization Canvas */}
        <div className="lg:col-span-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-4 overflow-hidden relative shadow-inner">
          {filteredNodes.length === 0 ? (
            <div className="h-[500px] flex flex-col items-center justify-center text-slate-500 space-y-2">
              <Layers className="w-8 h-8 opacity-40" />
              <p className="text-sm font-medium">Knowledge graph is empty</p>
              <p className="text-xs text-slate-600">Upload papers to generate relational nodes and concept bridges.</p>
            </div>
          ) : (
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[500px] select-none">
              {/* Edges */}
              {filteredEdges.map((e, idx) => {
                const posA = nodePositions.get(e.source);
                const posB = nodePositions.get(e.target);
                if (!posA || !posB) return null;
                return (
                  <line
                    key={idx}
                    x1={posA.x}
                    y1={posA.y}
                    x2={posB.x}
                    y2={posB.y}
                    stroke="#334155"
                    strokeWidth={1.5}
                    strokeOpacity={0.6}
                  />
                );
              })}

              {/* Nodes */}
              {filteredNodes.map((n) => {
                const pos = nodePositions.get(n.id);
                if (!pos) return null;
                const isSelected = selectedNode?.id === n.id;
                const color =
                  n.type === 'document' ? '#22c55e' : n.type === 'concept' ? '#38bdf8' : '#c084fc';

                return (
                  <g
                    key={n.id}
                    className="cursor-pointer transition-transform duration-200"
                    onClick={() => setSelectedNode(n)}
                  >
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={n.type === 'document' ? 14 : 9}
                      fill={color}
                      fillOpacity={isSelected ? 1.0 : 0.75}
                      stroke={isSelected ? '#ffffff' : '#0f172a'}
                      strokeWidth={2}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 20}
                      fontSize={10}
                      textAnchor="middle"
                      fill="#94a3b8"
                      className="pointer-events-none font-medium"
                    >
                      {n.label.length > 18 ? n.label.slice(0, 16) + '...' : n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex items-center gap-4 bg-slate-950/80 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-800 text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Paper
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" /> Concept
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400" /> Author
            </span>
          </div>
        </div>

        {/* Node Inspector Side Panel */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Info className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-sm text-slate-200">Node Inspector</h3>
          </div>

          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Type</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono capitalize">
                  {selectedNode.type}
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Label</span>
                <h4 className="text-sm font-semibold text-slate-100">{selectedNode.label}</h4>
              </div>

              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">ID</span>
                <p className="text-xs text-slate-400 font-mono break-all">{selectedNode.id}</p>
              </div>

              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block mb-1">
                    Metadata
                  </span>
                  <pre className="p-2.5 bg-slate-950 rounded-lg text-[11px] text-slate-400 overflow-x-auto font-mono">
                    {JSON.stringify(selectedNode.properties, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-500">
              Click on any node in the graph to view its structural properties and connections.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

