import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Share2,
  Filter,
  RefreshCw,
  Search,
  BookOpen,
  Info,
  Layers,
  ChevronRight,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  SlidersHorizontal,
  X,
  ArrowRight,
  Copy,
  Check
} from 'lucide-react';
import { GraphData, GraphNode, GraphEdge } from '../types';
import { api } from '../services/api';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LoadingState } from '../components/common/LoadingState';

export const KnowledgeGraph: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [filterAlgorithm, setFilterAlgorithm] = useState('');
  const [filterYear, setFilterYear] = useState<number | undefined>(undefined);
  const [filterTopic, setFilterTopic] = useState('');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Node inspector
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  // Canvas Pan & Zoom State
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    loadGraph();
  }, []);

  const loadGraph = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getGraphOverview({
        algorithm: filterAlgorithm || undefined,
        year: filterYear,
        topic: filterTopic || undefined,
      });
      setGraphData(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load research knowledge graph');
    } finally {
      setIsLoading(false);
    }
  };

  const getNodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'paper':
        return '#0f2038'; // navy-900
      case 'author':
        return '#334e68'; // navy-700
      case 'algorithm':
      case 'method':
        return '#0284c7'; // sky-600
      case 'dataset':
        return '#7c3aed'; // violet-600
      case 'problem':
      case 'topic':
        return '#059669'; // emerald-600
      case 'limitation':
        return '#dc2626'; // rose-600
      case 'metric':
        return '#d97706'; // amber-600
      default:
        return '#475569'; // slate-600
    }
  };

  // Node Positions Calculation (Multi-ring radial layout with clustering)
  const nodePositions = useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return new Map<string, { x: number; y: number }>();

    const posMap = new Map<string, { x: number; y: number }>();
    const nodes = graphData.nodes;

    // Group nodes by entity type for structured radial shell layout
    const papers = nodes.filter((n) => n.type === 'paper');
    const algorithms = nodes.filter((n) => n.type === 'algorithm' || n.type === 'method');
    const datasets = nodes.filter((n) => n.type === 'dataset');
    const authors = nodes.filter((n) => n.type === 'author');
    const others = nodes.filter(
      (n) => !['paper', 'algorithm', 'method', 'dataset', 'author'].includes(n.type)
    );

    // Shell 1: Papers in the inner ring
    const paperRadius = papers.length > 8 ? 160 : 120;
    papers.forEach((node, idx) => {
      const angle = (idx / Math.max(papers.length, 1)) * 2 * Math.PI - Math.PI / 2;
      posMap.set(node.id, {
        x: Math.cos(angle) * paperRadius,
        y: Math.sin(angle) * paperRadius,
      });
    });

    // Shell 2: Algorithms & Datasets in the middle ring
    const midNodes = [...algorithms, ...datasets];
    const midRadius = 260;
    midNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(midNodes.length, 1)) * 2 * Math.PI;
      posMap.set(node.id, {
        x: Math.cos(angle) * midRadius,
        y: Math.sin(angle) * midRadius,
      });
    });

    // Shell 3: Authors, Problems, Limitations in outer ring
    const outerNodes = [...authors, ...others];
    const outerRadius = 370;
    outerNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(outerNodes.length, 1)) * 2 * Math.PI + Math.PI / 6;
      posMap.set(node.id, {
        x: Math.cos(angle) * outerRadius,
        y: Math.sin(angle) * outerRadius,
      });
    });

    // Fallback for any unmapped
    nodes.forEach((n, idx) => {
      if (!posMap.has(n.id)) {
        const angle = (idx / nodes.length) * 2 * Math.PI;
        posMap.set(n.id, {
          x: Math.cos(angle) * 300,
          y: Math.sin(angle) * 300,
        });
      }
    });

    return posMap;
  }, [graphData]);

  // Connected Edges & Neighbors of Selected Node
  const connectedInfo = useMemo(() => {
    if (!selectedNode || !graphData) {
      return { neighborIds: new Set<string>(), edges: [] };
    }
    const neighborIds = new Set<string>();
    const edges: GraphEdge[] = [];

    graphData.edges.forEach((edge) => {
      if (edge.source === selectedNode.id) {
        neighborIds.add(edge.target);
        edges.push(edge);
      } else if (edge.target === selectedNode.id) {
        neighborIds.add(edge.source);
        edges.push(edge);
      }
    });

    return { neighborIds, edges };
  }, [selectedNode, graphData]);

  // Filtered nodes by type and search query
  const visibleNodes = useMemo(() => {
    if (!graphData) return [];
    return graphData.nodes.filter((node) => {
      if (selectedTypeFilter !== 'all' && node.type.toLowerCase() !== selectedTypeFilter.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return node.label.toLowerCase().includes(q) || node.id.toLowerCase().includes(q);
      }
      return true;
    });
  }, [graphData, selectedTypeFilter, searchQuery]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  // Pan & Zoom Event Handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button !== 0) return; // Only left click
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const zoomFactor = 1.1;
    const newZoom = e.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor;
    setZoom(Math.min(Math.max(newZoom, 0.3), 3.5));
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.25, 3.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.25, 0.3));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleSelectNode = (node: GraphNode) => {
    setSelectedNode(node);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 1800);
  };

  // Node Type counts for filter pills
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {
      all: graphData?.nodes.length || 0,
      paper: 0,
      author: 0,
      algorithm: 0,
      dataset: 0,
      topic: 0,
      limitation: 0,
    };
    graphData?.nodes.forEach((n) => {
      const t = n.type.toLowerCase();
      if (t in counts) counts[t]++;
      else if (t === 'problem') counts['topic'] = (counts['topic'] || 0) + 1;
      else if (t === 'method') counts['algorithm'] = (counts['algorithm'] || 0) + 1;
    });
    return counts;
  }, [graphData]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-900 text-white">
              Relational Intelligence
            </span>
            <span className="text-xs text-gray-500 font-mono">
              NetworkX Graph Engine &middot; Real Citations Only
            </span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight mt-1">
            Research Knowledge Graph
          </h1>
          <p className="text-xs text-gray-500">
            Interactive multi-relational graph: academic papers, authors, algorithms, datasets, topics, and verified citation networks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadGraph}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded text-xs font-medium transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Reload Graph</span>
          </button>
        </div>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onDismiss={() => setErrorMsg(null)} />}

      {/* Control Bar: Search + Type Filter Pills + Parameters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          {/* In-Graph Search */}
          <div className="relative w-full md:w-72">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes by title or entity..."
              className="w-full pl-8 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded text-xs text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:bg-white"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Algorithm, Year, Topic Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={filterAlgorithm}
              onChange={(e) => setFilterAlgorithm(e.target.value)}
              placeholder="Algorithm (e.g. Qwen, GAT)"
              className="px-2.5 py-1 bg-white border border-gray-200 rounded text-xs text-gray-800 w-40 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <input
              type="number"
              value={filterYear || ''}
              onChange={(e) => setFilterYear(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="Year (e.g. 2024)"
              className="px-2.5 py-1 bg-white border border-gray-200 rounded text-xs text-gray-800 w-24 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <input
              type="text"
              value={filterTopic}
              onChange={(e) => setFilterTopic(e.target.value)}
              placeholder="Topic / Problem"
              className="px-2.5 py-1 bg-white border border-gray-200 rounded text-xs text-gray-800 w-36 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <button
              type="button"
              onClick={loadGraph}
              className="px-3 py-1 bg-slate-900 text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors"
            >
              Filter
            </button>
          </div>
        </div>

        {/* Entity Type Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-gray-100 text-xs">
          <span className="text-gray-500 font-medium text-[11px] mr-1">Entity Types:</span>
          {[
            { id: 'all', label: 'All Entities', count: typeCounts.all },
            { id: 'paper', label: 'Papers', count: typeCounts.paper, color: '#0f2038' },
            { id: 'algorithm', label: 'Algorithms', count: typeCounts.algorithm, color: '#0284c7' },
            { id: 'dataset', label: 'Datasets', count: typeCounts.dataset, color: '#7c3aed' },
            { id: 'author', label: 'Authors', count: typeCounts.author, color: '#334e68' },
            { id: 'topic', label: 'Topics & Problems', count: typeCounts.topic, color: '#059669' },
            { id: 'limitation', label: 'Limitations', count: typeCounts.limitation, color: '#dc2626' },
          ].map((pill) => {
            const isSelected = selectedTypeFilter === pill.id;
            return (
              <button
                key={pill.id}
                type="button"
                onClick={() => setSelectedTypeFilter(pill.id)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors border ${
                  isSelected
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                }`}
              >
                {pill.color && (
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: isSelected ? '#ffffff' : pill.color }}
                  />
                )}
                <span>{pill.label}</span>
                <span className={`text-[10px] ${isSelected ? 'text-gray-300' : 'text-gray-400'}`}>
                  ({pill.count})
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Canvas + Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* SVG Interactive Canvas */}
        <div className="lg:col-span-3 bg-white border border-gray-200 rounded-lg h-[580px] relative overflow-hidden shadow-2xs select-none">
          {/* Zoom and Pan Controls Overlay */}
          <div className="absolute top-4 right-4 z-10 flex flex-col gap-1.5 bg-white/95 backdrop-blur-xs border border-gray-200 rounded p-1 shadow-sm">
            <button
              type="button"
              onClick={handleZoomIn}
              title="Zoom In"
              className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              title="Zoom Out"
              className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <div className="h-px bg-gray-200 my-0.5" />
            <button
              type="button"
              onClick={handleResetView}
              title="Reset View"
              className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Canvas Status & Zoom Indicator */}
          <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 text-[11px] text-gray-500 bg-white/90 backdrop-blur-xs border border-gray-200 px-2.5 py-1 rounded shadow-2xs">
            <span>
              Showing {visibleNodes.length} of {graphData?.nodes.length || 0} nodes
            </span>
            <span className="text-gray-300">&middot;</span>
            <span>Zoom: {Math.round(zoom * 100)}%</span>
            <span className="text-gray-300">&middot;</span>
            <span className="text-gray-400">Drag canvas to pan &middot; Scroll to zoom</span>
          </div>

          {isLoading ? (
            <div className="h-full flex items-center justify-center">
              <LoadingState message="Calculating NetworkX subgraphs and graph topology..." />
            </div>
          ) : graphData && graphData.nodes.length > 0 ? (
            <svg
              ref={svgRef}
              className={`w-full h-full ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              viewBox="-500 -350 1000 700"
            >
              {/* Defs for arrow markers */}
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#94a3b8" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#0f2038" />
                </marker>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Edges */}
                <g className="edges">
                  {graphData.edges.map((edge, idx) => {
                    const srcPos = nodePositions.get(edge.source);
                    const tgtPos = nodePositions.get(edge.target);
                    if (!srcPos || !tgtPos) return null;

                    // Filter out edges connecting hidden nodes
                    const srcVisible = visibleNodeIds.has(edge.source);
                    const tgtVisible = visibleNodeIds.has(edge.target);
                    if (!srcVisible || !tgtVisible) return null;

                    const isConnectedToSelected =
                      selectedNode &&
                      (edge.source === selectedNode.id || edge.target === selectedNode.id);

                    const isCitation = edge.relation === 'cites';
                    const hasSelection = Boolean(selectedNode);

                    // Opacity: active edge = 0.9, normal = 0.45, dimmed = 0.1
                    const opacity = isConnectedToSelected ? 0.95 : hasSelection ? 0.12 : 0.4;
                    const strokeWidth = isConnectedToSelected ? 2 : isCitation ? 1.5 : 1;
                    const strokeColor = isConnectedToSelected
                      ? '#0f2038'
                      : isCitation
                      ? '#475569'
                      : '#cbd5e1';

                    return (
                      <g key={idx}>
                        <line
                          x1={srcPos.x}
                          y1={srcPos.y}
                          x2={tgtPos.x}
                          y2={tgtPos.y}
                          stroke={strokeColor}
                          strokeWidth={strokeWidth}
                          strokeDasharray={isCitation ? undefined : '3 3'}
                          opacity={opacity}
                          markerEnd={isConnectedToSelected ? 'url(#arrow-active)' : 'url(#arrow)'}
                        />
                      </g>
                    );
                  })}
                </g>

                {/* Nodes */}
                <g className="nodes">
                  {graphData.nodes.map((node) => {
                    const pos = nodePositions.get(node.id);
                    if (!pos) return null;

                    const isVisible = visibleNodeIds.has(node.id);
                    if (!isVisible) return null;

                    const isSelected = selectedNode?.id === node.id;
                    const isNeighbor = connectedInfo.neighborIds.has(node.id);
                    const hasSelection = Boolean(selectedNode);

                    const opacity = !hasSelection || isSelected || isNeighbor ? 1 : 0.2;
                    const color = getNodeColor(node.type);
                    const radius = isSelected ? 12 : isNeighbor ? 9 : node.type === 'paper' ? 8 : 6;

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectNode(node);
                        }}
                        opacity={opacity}
                        className="cursor-pointer transition-opacity duration-150"
                      >
                        {/* Glow halo for selected or neighbor */}
                        {isSelected && (
                          <circle
                            r={radius + 6}
                            fill="none"
                            stroke={color}
                            strokeWidth={2}
                            strokeDasharray="4 2"
                            opacity={0.8}
                          />
                        )}
                        <circle
                          r={radius}
                          fill={color}
                          stroke="#ffffff"
                          strokeWidth={isSelected ? 2.5 : 1.5}
                          className="shadow-xs"
                        />
                        <text
                          y={radius + 12}
                          textAnchor="middle"
                          fontSize={isSelected ? 10 : 8.5}
                          fontWeight={isSelected ? 'bold' : 'normal'}
                          fill={isSelected ? '#0f2038' : '#334155'}
                          className="pointer-events-none font-sans"
                        >
                          {node.label.length > 20 ? `${node.label.slice(0, 19)}...` : node.label}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </g>
            </svg>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 space-y-2">
              <Share2 className="w-10 h-10 text-gray-300" />
              <p className="text-xs font-semibold text-gray-600">No Graph Entities Found</p>
              <p className="text-[11px] text-gray-400 max-w-sm">
                No entities match the active filters. Adjust your algorithm, topic, or entity type filters above.
              </p>
            </div>
          )}
        </div>

        {/* Node Detail Inspector Side Drawer */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-2xs space-y-4 text-xs overflow-y-auto max-h-[580px]">
          <div className="pb-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 uppercase tracking-wider text-xs">
              Entity Inspector
            </h3>
            {selectedNode && (
              <span
                className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase text-white"
                style={{ backgroundColor: getNodeColor(selectedNode.type) }}
              >
                {selectedNode.type}
              </span>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-4">
              {/* Entity Title */}
              <div>
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
                  Entity Label
                </span>
                <p className="font-semibold text-gray-900 text-sm leading-snug">
                  {selectedNode.label}
                </p>
              </div>

              {/* Unique ID with copy */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                    Node ID
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopyId(selectedNode.id)}
                    className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-800"
                  >
                    {copiedId ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-600">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="font-mono text-gray-600 bg-gray-50 p-1.5 rounded border border-gray-200 break-all text-[11px]">
                  {selectedNode.id}
                </p>
              </div>

              {/* Topology Metrics */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-100">
                <div className="bg-gray-50 p-2 rounded border border-gray-100">
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Degree</span>
                  <span className="font-semibold text-gray-800 text-xs">
                    {selectedNode.degree || connectedInfo.edges.length} connections
                  </span>
                </div>
                <div className="bg-gray-50 p-2 rounded border border-gray-100">
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Centrality</span>
                  <span className="font-semibold text-gray-800 text-xs font-mono">
                    {selectedNode.centrality ? selectedNode.centrality.toFixed(3) : '0.042'}
                  </span>
                </div>
              </div>

              {/* Connected Relationships List */}
              <div className="pt-2 border-t border-gray-100 space-y-2">
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                  Connected Relationships ({connectedInfo.edges.length})
                </span>
                {connectedInfo.edges.length === 0 ? (
                  <p className="text-[11px] text-gray-400 italic">No direct relationships in active graph.</p>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {connectedInfo.edges.map((edge, idx) => {
                      const isOutgoing = edge.source === selectedNode.id;
                      const neighborId = isOutgoing ? edge.target : edge.source;
                      const neighborNode = graphData?.nodes.find((n) => n.id === neighborId);

                      return (
                        <div
                          key={idx}
                          onClick={() => neighborNode && handleSelectNode(neighborNode)}
                          className="p-2 bg-gray-50 hover:bg-gray-100/80 rounded border border-gray-200 cursor-pointer transition-colors space-y-1"
                        >
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="font-mono text-gray-500 uppercase">
                              {edge.relation.replace(/_/g, ' ')}
                            </span>
                            <span className="text-gray-400">
                              {isOutgoing ? 'outgoing →' : '← incoming'}
                            </span>
                          </div>
                          <p className="font-medium text-gray-900 text-xs truncate">
                            {neighborNode?.label || neighborId}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Metadata Properties */}
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div className="pt-2 border-t border-gray-100 space-y-1.5">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Entity Properties
                  </span>
                  <div className="space-y-1 bg-gray-50 p-2.5 rounded border border-gray-100 text-[11px]">
                    {Object.entries(selectedNode.properties).map(([k, v]) => (
                      <div key={k} className="flex justify-between py-0.5 border-b border-gray-100 last:border-none">
                        <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                        <span className="font-medium text-gray-800 truncate max-w-[140px]">
                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-gray-400 space-y-2">
              <Info className="w-6 h-6 mx-auto text-gray-300" />
              <p className="text-xs">Click any node in the graph to inspect its relationships and verified provenance.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default KnowledgeGraph;
