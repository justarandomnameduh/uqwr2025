import React, { useState, useEffect } from 'react';
import { ChevronDown, RefreshCw, Cpu, AlertCircle, CheckCircle, Play } from 'lucide-react';
import { apiService } from '../services/api';

interface ModelInfo {
  display_name: string;
  description: string;
  supports_images: boolean;
  supports_video: boolean;
  memory_requirements: string;
}

interface AvailableModelsResponse {
  status: string;
  available_models: Record<string, ModelInfo>;
  current_model_id: string | null;
  is_task_running: boolean;
}

interface ModelSelectorProps {
  onModelChange?: (modelId: string) => void;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ 
  onModelChange, 
  disabled = false 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<Record<string, ModelInfo>>({});
  const [currentModelId, setCurrentModelId] = useState<string | null>(null);
  const [isTaskRunning, setIsTaskRunning] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [switchError, setSwitchError] = useState<string | null>(null);

  // Load available models on component mount
  useEffect(() => {
    loadAvailableModels();
  }, []);

  const loadAvailableModels = async () => {
    try {
      const response: AvailableModelsResponse = await apiService.getAvailableModels();
      setAvailableModels(response.available_models);
      setCurrentModelId(response.current_model_id);
      setIsTaskRunning(response.is_task_running);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load available models:', err);
      setError('Failed to load available models');
    }
  };

  const handleModelSwitch = async (modelId: string) => {
    if (modelId === currentModelId || isSwitching || isTaskRunning) {
      return;
    }

    setIsSwitching(true);
    setSwitchError(null);

    try {
      await apiService.switchModel(modelId);
      setCurrentModelId(modelId);
      setIsOpen(false);
      onModelChange?.(modelId);
      
      // Reload available models to get updated status
      await loadAvailableModels();
    } catch (err: any) {
      console.error('Failed to switch model:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Failed to switch model';
      setSwitchError(errorMessage);
    } finally {
      setIsSwitching(false);
    }
  };

  const canSwitchModel = !disabled && !isTaskRunning && !isSwitching;
  const currentModel = currentModelId ? availableModels[currentModelId] : null;
  const hasNoModelLoaded = !currentModelId;

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-600 text-sm">
        <AlertCircle className="w-4 h-4" />
        <span>{error}</span>
        <button
          onClick={loadAvailableModels}
          className="text-blue-600 hover:text-blue-800 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Model selector button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={!canSwitchModel}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg border text-sm min-w-[200px]
          ${canSwitchModel
            ? hasNoModelLoaded 
              ? 'bg-blue-50 hover:bg-blue-100 border-blue-300 text-blue-700'
              : 'bg-white hover:bg-gray-50 border-gray-300 text-gray-700'
            : 'bg-gray-100 border-gray-200 text-gray-500 cursor-not-allowed'
          }
          ${isOpen ? 'ring-2 ring-blue-500 ring-opacity-50' : ''}
        `}
      >
        {hasNoModelLoaded ? (
          <Play className="w-4 h-4 text-blue-600" />
        ) : (
          <Cpu className="w-4 h-4" />
        )}
        <span className="min-w-0 flex-1 text-left truncate">
          {currentModel ? currentModel.display_name : 'Select a model to start'}
        </span>
        {isSwitching ? (
          <RefreshCw className="w-4 h-4 animate-spin" />
        ) : (
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        )}
      </button>

      {/* Status indicators */}
      <div className="flex items-center gap-1 mt-1 text-xs">
        {hasNoModelLoaded && !isSwitching && (
          <div className="flex items-center gap-1 text-blue-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span>No model loaded - select one to begin</span>
          </div>
        )}
        {isTaskRunning && (
          <div className="flex items-center gap-1 text-orange-600">
            <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
            <span>Task running</span>
          </div>
        )}
        {currentModel && !isTaskRunning && !hasNoModelLoaded && (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle className="w-3 h-3" />
            <span>Ready</span>
          </div>
        )}
        {switchError && (
          <div className="flex items-center gap-1 text-red-600">
            <AlertCircle className="w-3 h-3" />
            <span className="truncate">{switchError}</span>
          </div>
        )}
        {isSwitching && (
          <div className="flex items-center gap-1 text-blue-600">
            <RefreshCw className="w-3 h-3 animate-spin" />
            <span>Loading model...</span>
          </div>
        )}
      </div>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown content */}
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-20 max-h-96 overflow-y-auto">
            <div className="p-3 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">
                  {hasNoModelLoaded ? 'Choose Your First Model' : 'Switch Model'}
                </h3>
                <button
                  onClick={loadAvailableModels}
                  className="text-gray-500 hover:text-gray-700"
                  disabled={isSwitching}
                >
                  <RefreshCw className={`w-4 h-4 ${isSwitching ? 'animate-spin' : ''}`} />
                </button>
              </div>
              {hasNoModelLoaded && (
                <p className="text-xs text-blue-600 mt-1">
                  💡 Select a model below to start using the VLM chatbot
                </p>
              )}
              {!canSwitchModel && !hasNoModelLoaded && (
                <p className="text-xs text-gray-500 mt-1">
                  {isTaskRunning ? 'Cannot switch while task is running' : 'Model switching disabled'}
                </p>
              )}
            </div>

            <div className="py-1">
              {Object.entries(availableModels).map(([modelId, modelInfo]) => {
                const isSelected = modelId === currentModelId;
                const isDisabled = !canSwitchModel || isSwitching;

                return (
                  <button
                    key={modelId}
                    onClick={() => handleModelSwitch(modelId)}
                    disabled={isDisabled}
                    className={`
                      w-full px-4 py-3 text-left hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed
                      ${isSelected ? 'bg-blue-50 border-r-2 border-blue-500' : ''}
                      ${hasNoModelLoaded && !isDisabled ? 'hover:bg-blue-50' : ''}
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${isSelected ? 'text-blue-700' : hasNoModelLoaded ? 'text-blue-700' : 'text-gray-900'}`}>
                        {modelInfo.display_name}
                      </span>
                      {isSelected ? (
                        <CheckCircle className="w-4 h-4 text-blue-600" />
                      ) : hasNoModelLoaded ? (
                        <Play className="w-4 h-4 text-blue-600" />
                      ) : null}
                    </div>
                    
                    <p className="text-xs text-gray-600 mt-1">
                      {modelInfo.description}
                    </p>
                    
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span>{modelInfo.memory_requirements}</span>
                      {modelInfo.supports_images && (
                        <span className="flex items-center gap-1">
                          📷 Images
                        </span>
                      )}
                      {modelInfo.supports_video && (
                        <span className="flex items-center gap-1">
                          🎥 Video
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
              
              {Object.keys(availableModels).length === 0 && (
                <div className="px-4 py-6 text-center text-gray-500">
                  <AlertCircle className="w-6 h-6 mx-auto mb-2" />
                  <p>No models available</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}; 