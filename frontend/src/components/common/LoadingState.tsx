import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
  size = 'md',
  className = ''
}) => {
  const iconSize = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-6 h-6' : 'w-5 h-5';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  return (
    <div className={`flex flex-col items-center justify-center py-8 text-gray-500 ${className}`}>
      <Loader2 className={`${iconSize} animate-spin text-gray-700 mb-2`} />
      <span className={`${textSize} font-medium text-gray-600`}>{message}</span>
    </div>
  );
};

