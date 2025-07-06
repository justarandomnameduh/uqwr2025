import React from 'react';
import { ModelInfo } from '../services/api';

interface StatusBarProps {
  isConnected: boolean;
  modelInfo: ModelInfo | null;
  error: string | null;
}

const StatusBar: React.FC<StatusBarProps> = ({ isConnected, modelInfo, error }) => {
  return (
    <div className="status-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span className={isConnected ? 'status-connected' : 'status-disconnected'}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
        {modelInfo && (
          <span style={{ color: '#6b7280' }}>
            {modelInfo.model_name} {modelInfo.is_loaded}
          </span>
        )}
      </div>
      {error && (
        <span className="status-error"> Error: {error}</span>
      )}
    </div>
  );
};

export default StatusBar; 