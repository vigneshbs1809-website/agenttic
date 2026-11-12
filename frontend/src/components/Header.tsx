import React from 'react';
import { RefreshCw, Database, Cpu } from 'lucide-react';
import { SystemHealth } from '../types';

interface HeaderProps {
  title: string;
  subtitle?: string;
  health: SystemHealth | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  actions?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  health,
  onRefresh,
  isRefreshing = false,
  actions
}) => {
  return (
    <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-between shrink-0 select-none">
      {/* Title & Subtitle */}
      <div className="flex items-center gap-3 min-w-0">
        <div>
          <h1 className="text-sm font-semibold text-gray-900 tracking-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-[11px] text-gray-500 truncate -mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Right controls: Health telemetry & actions */}
      <div className="flex items-center gap-3">
        {/* Minimal Health Indicators */}
        <div className="hidden md:flex items-center gap-3 pr-2 text-xs text-gray-500">
          <div className="flex items-center gap-1.5" title="SQLite Database WAL Mode">
            <Database className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[11px] text-gray-600 font-medium">SQLite WAL</span>
          </div>

          <span className="text-gray-300">|</span>

          <div className="flex items-center gap-1.5" title="Local Model Engine">
            <Cpu className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[11px] text-gray-600 font-medium">
              {health?.ollama_model || 'qwen3:1.7b'}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        {actions && <div className="flex items-center gap-2">{actions}</div>}

        {/* Refresh */}
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 text-gray-400 hover:text-gray-700 rounded border border-gray-200 hover:bg-gray-50 transition-colors disabled:opacity-50"
            title="Refresh data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-gray-700' : ''}`} />
          </button>
        )}
      </div>
    </header>
  );
};
