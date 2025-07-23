import React from 'react';
import { Wifi, WifiOff, AlertCircle } from 'lucide-react';
import type { ModelInfo } from '../types';

interface StatusBarProps {
  isConnected: boolean;
  modelInfo: ModelInfo | null;
  error: string | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({ isConnected, modelInfo, error }) => {
  return (
    <div className="flex items-center justify-between text-sm bg-gray-50 p-3 rounded-lg border">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-green-600 font-medium">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-red-600 font-medium">Disconnected</span>
            </>
          )}
        </div>
        
        {modelInfo && (
          <div className="flex items-center gap-2 text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span>
              {modelInfo.model_name} 
              {modelInfo.is_loaded && <span className="text-green-600 ml-1">(Loaded)</span>}
            </span>
          </div>
        )}
      </div>
      
      {error && (
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">Error: {error}</span>
        </div>
      )}
    </div>
  );
}; 