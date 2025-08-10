import React, { useState, useEffect, useRef } from 'react';
import { Trash2, FileImage, MessageSquare } from 'lucide-react';
import type { Message, UploadedImage, ModelInfo } from '../types';
import { apiService } from '../services/api';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ImageUpload } from './ImageUpload';
import { StatusBar } from './StatusBar';
import { ModelSelector } from './ModelSelector';
import { v4 as uuidv4 } from 'uuid';

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<UploadedImage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isWaitingForLogConfirmation, setIsWaitingForLogConfirmation] = useState(false);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentModelId, setCurrentModelId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check backend connection and model status
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const health = await apiService.checkHealth();
        setIsConnected(health.status === 'healthy');
        
        const info = await apiService.getModelInfo();
        setModelInfo(info);
        
        // Get current model ID from available models response
        try {
          const availableModels = await apiService.getAvailableModels();
          setCurrentModelId(availableModels.current_model_id || null);
        } catch (err) {
          console.error('Failed to get current model ID:', err);
        }
        setError(null);
      } catch (err) {
        setIsConnected(false);
        setError('Failed to connect to backend. Make sure the backend server is running.');
        console.error('Connection error:', err);
      }
    };

    checkConnection();
    // Check connection every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleModelChange = async (modelId: string) => {
    // Update current model ID and refresh model info
    setCurrentModelId(modelId);
    try {
      const info = await apiService.getModelInfo();
      setModelInfo(info);
    } catch (err) {
      console.error('Failed to refresh model info:', err);
    }
  };

  const handleSendMessage = async (text: string, imagesToSend: UploadedImage[]) => {
    if (!text.trim() && imagesToSend.length === 0) return;

    // Check if model is loaded
    if (!currentModelId) {
      setError('Please select and load a model before sending messages.');
      return;
    }

    const userMessage: Message = {
      id: uuidv4(),
      type: 'user',
      content: text,
      images: imagesToSend.map(img => img.uploadedPath || ''),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsGenerating(true);
    setError(null);

    // Create an assistant message placeholder for streaming
    const assistantMessageId = uuidv4();
    const assistantMessage: Message = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const request = {
        text: text,
        image_paths: imagesToSend.map(img => img.uploadedPath).filter(Boolean) as string[],
        max_new_tokens: 512,
        temperature: 0.7,
      };

      await apiService.generateResponseStream(
        request,
        // onToken - append each token to the assistant message
        (token: string) => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: msg.content + token }
              : msg
          ));
        },
        // onStart - optional metadata handling
        (metadata) => {
          console.log('Streaming started:', metadata);
        },
        // onError - handle streaming errors
        (error: string) => {
          console.error('Streaming error:', error);
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { 
                  ...msg, 
                  content: msg.content || `Error: ${error}`,
                  isStreaming: false 
                }
              : msg
          ));
          setError('Failed to generate response. Please try again.');
          // Reset states on streaming error
          setIsGenerating(false);
          setIsWaitingForLogConfirmation(false);
        },
        // onDone - finalize the message and wait for log confirmation
        async () => {
          // First update the message to stop streaming
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, isStreaming: false }
              : msg
          ));
          
          // Set waiting state (keeps input locked)
          setIsWaitingForLogConfirmation(true);
          
          // Get the final message for logging
          setMessages(prev => {
            const assistantMsg = prev.find(msg => msg.id === assistantMessageId);
            if (assistantMsg) {
              // Send the completed assistant message to backend for logging
              apiService.logAssistantMessage({
                message_id: assistantMsg.id,
                content: assistantMsg.content,
                timestamp: assistantMsg.timestamp.toISOString(),
                user_input: text,
                images_used: imagesToSend.length
              }).then(() => {
                // Backend confirmed receipt - unlock input
                setIsWaitingForLogConfirmation(false);
                setIsGenerating(false);
              }).catch(err => {
                console.error('Failed to log assistant message:', err);
                // Even if logging fails, unlock the input
                setIsWaitingForLogConfirmation(false);
                setIsGenerating(false);
              });
            } else {
              // No message found, unlock anyway
              setIsWaitingForLogConfirmation(false);
              setIsGenerating(false);
            }
            
            return prev;
          });
        }
      );
    } catch (err: any) {
      console.error('Generation error:', err);
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessageId 
          ? { 
              ...msg, 
              content: `Error: ${err.message || 'Failed to generate response'}`,
              isStreaming: false 
            }
          : msg
      ));
      setError('Failed to generate response. Please try again.');
      // Reset states on generation error
      setIsGenerating(false);
      setIsWaitingForLogConfirmation(false);
    } finally {
      // Note: setIsGenerating(false) is now handled in onDone callback after log confirmation
      // Only set to false here if there was an error during streaming setup
      if (isWaitingForLogConfirmation) {
        setIsGenerating(false);
        setIsWaitingForLogConfirmation(false);
      }
    }

    // Clear selected images after sending
    setSelectedImages([]);
  };

  const handleImageUpload = (newImages: UploadedImage[]) => {
    setUploadedImages(prev => {
      // Update existing images or add new ones
      const updatedImages = [...prev];
      newImages.forEach(newImg => {
        const existingIndex = updatedImages.findIndex(img => img.id === newImg.id);
        if (existingIndex >= 0) {
          updatedImages[existingIndex] = newImg;
        } else {
          updatedImages.push(newImg);
        }
      });
      return updatedImages;
    });
  };

  const handleRemoveImage = (imageToRemove: UploadedImage) => {
    // Remove from uploaded images
    setUploadedImages(prev => prev.filter(img => img.id !== imageToRemove.id));
    // Remove from selected images
    setSelectedImages(prev => prev.filter(img => img.id !== imageToRemove.id));
    // Revoke object URL to free memory
    URL.revokeObjectURL(imageToRemove.url);
  };

  const toggleImageSelection = (image: UploadedImage) => {
    setSelectedImages(prev => {
      const isSelected = prev.some(selected => selected.id === image.id);
      if (isSelected) {
        return prev.filter(selected => selected.id !== image.id);
      } else {
        return [...prev, image];
      }
    });
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  const clearImages = () => {
    uploadedImages.forEach(img => {
      URL.revokeObjectURL(img.url);
    });
    setUploadedImages([]);
    setSelectedImages([]);
  };

  const handleAudioLoadingChange = (isLoading: boolean) => {
    setIsAudioLoading(isLoading);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Audio Loading Overlay */}
      {isAudioLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white rounded-xl p-6 flex flex-col items-center gap-4 shadow-xl">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-700 font-medium">Processing audio...</p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-3">
              <MessageSquare className="w-8 h-8 text-blue-500" />
              VLM Chat
            </h1>
            <p className="text-gray-600 mt-1">Vision-Language Model Interface</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={clearChat}
              disabled={messages.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Clear Chat
            </button>
            <button
              onClick={clearImages}
              disabled={uploadedImages.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <FileImage className="w-4 h-4" />
              Clear Images
            </button>
          </div>
        </div>
        
        {/* Model Selector */}
        <div className="mb-4">
          <ModelSelector 
            onModelChange={handleModelChange}
            disabled={isGenerating || isAudioLoading}
          />
        </div>
        
        <StatusBar 
          isConnected={isConnected}
          modelInfo={modelInfo}
          error={error}
        />
      </div>

      {/* Main content */}
      <div className={`flex flex-1 overflow-hidden ${isAudioLoading ? 'opacity-60 pointer-events-none' : ''}`}>
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          <MessageList 
            messages={messages}
            isGenerating={isGenerating}
            messagesEndRef={messagesEndRef}
          />
          
          <MessageInput
            onSendMessage={handleSendMessage}
            selectedImages={selectedImages}
            onRemoveSelectedImage={toggleImageSelection}
            onAudioLoadingChange={handleAudioLoadingChange}
            isGenerating={isGenerating}
            disabled={!isConnected || !currentModelId}
            isWaitingForLogConfirmation={isWaitingForLogConfirmation}
          />
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          <ImageUpload
            onImageUpload={handleImageUpload}
            uploadedImages={uploadedImages}
            selectedImages={selectedImages}
            onRemoveImage={handleRemoveImage}
            onToggleSelection={toggleImageSelection}
          />
        </div>
      </div>
    </div>
  );
}; 