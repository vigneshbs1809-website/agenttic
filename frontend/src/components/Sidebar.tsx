import React from 'react';
import {
  LayoutDashboard,
  FolderKanban,
  Compass,
  FileText,
  FileSearch,
  Scale,
  Share2,
  Target,
  Split,
  ShieldCheck,
  FileBarChart,
  Settings,
  BookOpen,
  Cpu
} from 'lucide-react';
import { ResearchProjectItem } from '../types';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  projects?: ResearchProjectItem[];
  selectedProjectId?: string;
  onSelectProject?: (id: string) => void;
  ramPercent?: number;
  ollamaConnected?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  setCurrentTab,
  projects = [],
  selectedProjectId = '',
  onSelectProject,
  ramPercent = 0,
  ollamaConnected = false
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'projects', label: 'My Research Projects', icon: FolderKanban },
    { id: 'discover', label: 'Discover Papers', icon: Compass },
    { id: 'library', label: 'PDF Library', icon: FileText },
    { id: 'analysis', label: 'Paper Analysis', icon: FileSearch },
    { id: 'comparison', label: 'Comparative Analysis', icon: Scale },
    { id: 'graph', label: 'Knowledge Graph', icon: Share2 },
    { id: 'gaps', label: 'Research Gaps', icon: Target },
    { id: 'contradictions', label: 'Contradiction Analysis', icon: Split },
    { id: 'verification', label: 'Evidence Verification', icon: ShieldCheck },
    { id: 'reports', label: 'Research Reports', icon: FileBarChart },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-60 bg-gray-50/70 border-r border-gray-200 flex flex-col justify-between shrink-0 select-none font-sans">
      <div className="flex flex-col min-h-0">
        {/* Brand / Academic Title Header */}
        <div className="h-14 flex items-center gap-2.5 px-4 border-b border-gray-200 bg-white">
          <div className="w-7 h-7 rounded bg-slate-900 flex items-center justify-center text-white shrink-0">
            <BookOpen className="w-4 h-4 text-gray-100" />
          </div>
          <div className="min-w-0">
            <span className="font-semibold text-gray-900 text-xs tracking-tight block truncate">
              Literature Intelligence
            </span>
            <span className="text-[10px] font-medium text-gray-500 block truncate">
              Academic SaaS Platform
            </span>
          </div>
        </div>

        {/* Project Selector */}
        {projects.length > 0 && onSelectProject && (
          <div className="px-3 pt-3 pb-1 border-b border-gray-100">
            <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
              Active Project
            </label>
            <select
              value={selectedProjectId}
              onChange={(e) => onSelectProject(e.target.value)}
              className="w-full bg-white border border-gray-200 rounded text-xs text-gray-800 py-1 px-2 focus:outline-none focus:ring-1 focus:ring-slate-900 truncate"
            >
              <option value="">All Projects (Workspace)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Navigation List */}
        <nav className="p-2.5 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                  active
                    ? 'bg-slate-900 text-white font-semibold shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/60'
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-white' : 'text-gray-500'}`} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Telemetry Minimalist Footer */}
      <div className="p-3 border-t border-gray-200 bg-white text-[11px] text-gray-500 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-gray-600">
            <Cpu className="w-3.5 h-3.5 text-gray-500" />
            Host RAM
          </span>
          <span className="font-mono text-gray-700 font-medium">
            {ramPercent ? `${ramPercent}%` : '8 GB cap'}
          </span>
        </div>

        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-400">Ollama Local</span>
          <span className={`inline-flex items-center gap-1 font-medium ${ollamaConnected ? 'text-emerald-700' : 'text-gray-500'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${ollamaConnected ? 'bg-emerald-600' : 'bg-gray-400'}`} />
            {ollamaConnected ? 'Ready (qwen3)' : 'Standby'}
          </span>
        </div>
      </div>
    </aside>
  );
};
