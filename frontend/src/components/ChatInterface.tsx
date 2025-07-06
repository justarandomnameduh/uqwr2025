import React, { useState, useEffect, useRef } from 'react';
import { Message, UploadedImage } from '../types';
import { apiService, GenerateRequest, ModelInfo } from '../services/api';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ImageUpload from './ImageUpload';
import StatusBar from './StatusBar';
import { v4 as uuidv4 } from 'uuid';

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<UploadedImage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check backend connection and model status
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const health = await apiService.checkHealth();
        setIsConnected(health.status === 'healthy');
        
        const info = await apiService.getModelInfo();
        setModelInfo(info);
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

  const handleSendMessage = async (text: string, imagesToSend: UploadedImage[]) => {
    if (!text.trim() && imagesToSend.length === 0) return;

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

    try {
      const request: GenerateRequest = {
        text: text,
        image_paths: imagesToSend.map(img => img.uploadedPath).filter(Boolean) as string[],
        max_new_tokens: 512,
        temperature: 0.7,
      };

      const response = await apiService.generateResponse(request);

      const assistantMessage: Message = {
        id: uuidv4(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('Generation error:', err);
      const errorMessage: Message = {
        id: uuidv4(),
        type: 'assistant',
        content: `Error: ${err.response?.data?.message || err.message || 'Failed to generate response'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setError('Failed to generate response. Please try again.');
    } finally {
      setIsGenerating(false);
    }

    // Clear selected images after sending
    setSelectedImages([]);
  };

  const handleImageUpload = async (files: File[]) => {
    const newImages: UploadedImage[] = files.map(file => ({
      id: uuidv4(),
      file,
      url: URL.createObjectURL(file),
      isUploading: true,
    }));

    setUploadedImages(prev => [...prev, ...newImages]);

    try {
      const response = await apiService.uploadFiles(files);
      
      setUploadedImages(prev => 
        prev.map(img => {
          const uploadedFile = response.files.find(f => f.original_name === img.file.name);
          if (uploadedFile) {
            return {
              ...img,
              uploadedPath: uploadedFile.path,
              isUploading: false,
            };
          }
          return img;
        })
      );
    } catch (err: any) {
      console.error('Upload error:', err);
      setUploadedImages(prev =>
        prev.map(img => 
          newImages.find(newImg => newImg.id === img.id)
            ? { ...img, isUploading: false, uploadError: 'Upload failed' }
            : img
        )
      );
      setError('Failed to upload images. Please try again.');
    }
  };

  const handleRemoveImage = async (imageId: string) => {
    const imageToRemove = uploadedImages.find(img => img.id === imageId);
    
    setUploadedImages(prev => prev.filter(img => img.id !== imageId));
    setSelectedImages(prev => prev.filter(img => img.id !== imageId));

    if (imageToRemove) {
      URL.revokeObjectURL(imageToRemove.url);
      if (imageToRemove.uploadedPath) {
        try {
          await apiService.deleteFile(imageToRemove.uploadedPath);
        } catch (err) {
          console.error('Failed to delete file from server:', err);
        }
      }
    }
  };

  const toggleImageSelection = (image: UploadedImage) => {
    setSelectedImages(prev => {
      const isSelected = prev.some(img => img.id === image.id);
      if (isSelected) {
        return prev.filter(img => img.id !== image.id);
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

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-content">
          <div>
            <h1 className="chat-title">VLM Chat</h1>
            <p className="chat-subtitle">Vision-Language Model Interface</p>
          </div>
          <div className="chat-buttons">
            <button onClick={clearChat} className="btn">
              Clear Chat
            </button>
            <button onClick={clearImages} className="btn">
              Clear Images
            </button>
          </div>
        </div>
        
        <StatusBar 
          isConnected={isConnected}
          modelInfo={modelInfo}
          error={error}
        />
      </div>

      {/* Main content */}
      <div className="chat-main">
        {/* Chat area */}
        <div className="chat-area">
          <MessageList 
            messages={messages}
            isGenerating={isGenerating}
            apiService={apiService}
            messagesEndRef={messagesEndRef}
          />
          
          <MessageInput
            onSendMessage={handleSendMessage}
            selectedImages={selectedImages}
            onRemoveSelectedImage={toggleImageSelection}
            isGenerating={isGenerating}
            disabled={!isConnected}
          />
        </div>

        {/* Sidebar */}
        <div className="sidebar">
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

export default ChatInterface; 