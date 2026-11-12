import React from 'react';

export type StatusVariant =
  | 'completed'
  | 'processing'
  | 'pending'
  | 'failed'
  | 'supported'
  | 'partially_supported'
  | 'contradicted'
  | 'insufficient_evidence'
  | 'active'
  | 'archived'
  | 'neutral';

interface StatusIndicatorProps {
  status: string;
  variant?: StatusVariant;
  label?: string;
  size?: 'sm' | 'md';
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  variant,
  label,
  size = 'md'
}) => {
  const norm = (variant || status || 'neutral').toLowerCase().replace(/\s+/g, '_');

  let dotColor = 'bg-gray-400';
  let badgeClasses = 'bg-gray-50 text-gray-700 border-gray-200';

  if (norm.includes('completed') || norm.includes('supported') || norm.includes('active') || norm === 'success') {
    dotColor = 'bg-emerald-600';
    badgeClasses = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (norm.includes('processing') || norm.includes('running')) {
    dotColor = 'bg-blue-600 animate-pulse';
    badgeClasses = 'bg-blue-50 text-blue-800 border-blue-200';
  } else if (norm.includes('partial') || norm.includes('pending') || norm.includes('condition')) {
    dotColor = 'bg-amber-500';
    badgeClasses = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (norm.includes('failed') || norm.includes('contradicted') || norm.includes('error')) {
    dotColor = 'bg-rose-600';
    badgeClasses = 'bg-rose-50 text-rose-800 border-rose-200';
  } else if (norm.includes('insufficient') || norm.includes('archived')) {
    dotColor = 'bg-gray-500';
    badgeClasses = 'bg-gray-100 text-gray-700 border-gray-200';
  }

  const displayText = label || status.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded ${
        size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-0.5 text-xs'
      } ${badgeClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className="capitalize">{displayText}</span>
    </span>
  );
};

