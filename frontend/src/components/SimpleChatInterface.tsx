import React, { useState, useEffect, useRef } from 'react';
import { Message, UploadedImage } from '../types';
import { apiService, GenerateRequest, ModelInfo } from '../services/api';
import { v4 as uuidv4 } from 'uuid';

const SimpleChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<UploadedImage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [message]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!message.trim() && selectedImages.length === 0) || isGenerating || !isConnected) return;

    const userMessage: Message = {
      id: uuidv4(),
      type: 'user',
      content: message,
      images: selectedImages.map(img => img.uploadedPath || ''),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsGenerating(true);
    setError(null);

    try {
      const request: GenerateRequest = {
        text: message,
        image_paths: selectedImages.map(img => img.uploadedPath).filter(Boolean) as string[],
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

    setMessage('');
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

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    const validFiles = Array.from(files).filter(file => {
      const isImage = file.type.startsWith('image/');
      const isValidSize = file.size <= 16 * 1024 * 1024;
      return isImage && isValidSize;
    });
    if (validFiles.length > 0) {
      handleImageUpload(validFiles);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
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

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const canSend = (message.trim() || selectedImages.length > 0) && !isGenerating && isConnected;

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
            <button
              onClick={() => setMessages([])}
              className="btn"
            >
              Clear Chat
            </button>
            <button
              onClick={() => {
                uploadedImages.forEach(img => URL.revokeObjectURL(img.url));
                setUploadedImages([]);
                setSelectedImages([]);
              }}
              className="btn"
            >
              Clear Images
            </button>
          </div>
        </div>
        
        {/* Status Bar */}
        <div className="status-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className={isConnected ? 'status-connected' : 'status-disconnected'}>
              {isConnected ? '✓ Connected' : '✗ Disconnected'}
            </span>
            {modelInfo && (
              <span style={{ color: '#6b7280' }}>
                🖥️ {modelInfo.model_name} {modelInfo.is_loaded && '• Loaded'}
              </span>
            )}
          </div>
          {error && (
            <span className="status-error">⚠️ {error}</span>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="chat-main">
        {/* Chat area */}
        <div className="chat-area">
          {/* Messages */}
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-content">
                  <div className="welcome-icon">🤖</div>
                  <h3 className="welcome-title">Welcome to VLM Chat</h3>
                  <p className="welcome-text">
                    Start a conversation by typing a message or uploading images. 
                    The AI can understand both text and images!
                  </p>
                </div>
              </div>
            ) : (
              <div>
                {messages.map((msg) => (
                  <div key={msg.id} className={`message ${msg.type === 'user' ? 'message-user' : 'message-assistant'}`}>
                    <div className="message-content">
                      <div className={`message-avatar ${msg.type === 'user' ? 'message-avatar-user' : 'message-avatar-assistant'}`}>
                        {msg.type === 'user' ? '👤' : '🤖'}
                      </div>
                      <div>
                        <div className={`message-bubble ${msg.type === 'user' ? 'message-bubble-user' : 'message-bubble-assistant'}`}>
                          {msg.images && msg.images.length > 0 && (
                            <div style={{ marginBottom: '0.75rem', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                              {msg.images.map((imagePath, index) => (
                                <div key={index} style={{ position: 'relative' }}>
                                  <img
                                    src={apiService.getFileUrl(imagePath)}
                                    alt={`Uploaded image ${index + 1}`}
                                    style={{ width: '100%', height: '6rem', objectFit: 'cover', borderRadius: '0.25rem', border: '1px solid #e5e7eb' }}
                                  />
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="message-text">{msg.content}</div>
                        </div>
                        <div className="message-timestamp">
                          {formatTime(msg.timestamp)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Typing indicator */}
                {isGenerating && (
                  <div className="message message-assistant">
                    <div className="message-content">
                      <div className="message-avatar message-avatar-assistant">🤖</div>
                      <div className="message-bubble message-bubble-assistant">
                        <div className="typing-indicator">
                          <div className="typing-dot"></div>
                          <div className="typing-dot"></div>
                          <div className="typing-dot"></div>
                        </div>
                        <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>AI is thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="input-container">
            {/* Selected images preview */}
            {selectedImages.length > 0 && (
              <div style={{ marginBottom: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {selectedImages.map((image) => (
                  <div key={image.id} style={{ position: 'relative' }}>
                    <img
                      src={image.url}
                      alt={`Selected ${image.file.name}`}
                      style={{ width: '4rem', height: '4rem', objectFit: 'cover', borderRadius: '0.25rem', border: '2px solid #3b82f6' }}
                    />
                    <button
                      onClick={() => toggleImageSelection(image)}
                      style={{
                        position: 'absolute',
                        top: '-0.5rem',
                        right: '-0.5rem',
                        width: '1.5rem',
                        height: '1.5rem',
                        backgroundColor: '#ef4444',
                        color: 'white',
                        borderRadius: '50%',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleSendMessage} className="input-form">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={!isConnected ? "Backend disconnected..." : "Type your message..."}
                className="input-textarea"
                disabled={!isConnected || isGenerating}
                rows={1}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
              />
              <button
                type="button"
                disabled={true}
                className="input-button input-button-audio"
                title="Audio input - Coming soon"
              >
                🎤
              </button>
              <button
                type="submit"
                disabled={!canSend}
                className={`input-button ${canSend ? 'input-button-send' : ''}`}
              >
                ➤
              </button>
            </form>

            {selectedImages.length > 0 && (
              <div style={{ textAlign: 'center', fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem' }}>
                📷 {selectedImages.length} image(s) selected • Press Enter to send
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-title">
              📷 <span>Image Upload</span>
            </div>
            <p className="sidebar-subtitle">
              Upload images to use in your conversation
            </p>
          </div>

          <div className="upload-area">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            >
              <div className="upload-icon">📤</div>
              <p className="upload-text">
                Drag and drop images here, or click to select files
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn"
              >
                📁 Select Files
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => handleFileSelect(e.target.files)}
                style={{ display: 'none' }}
              />
            </div>

            <div className="upload-info">
              <p>• Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP</p>
              <p>• Maximum file size: 16MB</p>
              <p>• Multiple files can be selected</p>
            </div>
          </div>

          <div className="images-list">
            <h4 style={{ fontWeight: 500, color: '#111827', marginBottom: '1rem' }}>
              Available Images ({uploadedImages.length})
            </h4>
            
            {uploadedImages.length === 0 ? (
              <div className="images-empty">
                <div className="images-empty-icon">🖼️</div>
                <p className="images-empty-text">No images uploaded yet</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {uploadedImages.map((image) => {
                  const isSelected = selectedImages.some(img => img.id === image.id);
                  return (
                    <div
                      key={image.id}
                      onClick={() => toggleImageSelection(image)}
                      style={{
                        position: 'relative',
                        cursor: 'pointer',
                        border: isSelected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                        borderRadius: '0.25rem',
                        overflow: 'hidden'
                      }}
                    >
                      <img
                        src={image.url}
                        alt={image.file.name}
                        style={{
                          width: '4rem',
                          height: '4rem',
                          objectFit: 'cover',
                          opacity: image.isUploading ? 0.5 : 1
                        }}
                      />
                      {image.isUploading && (
                        <div style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          backgroundColor: 'rgba(255, 255, 255, 0.8)'
                        }}>
                          ⟳
                        </div>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveImage(image.id);
                        }}
                        style={{
                          position: 'absolute',
                          top: '0.125rem',
                          right: '0.125rem',
                          width: '1.25rem',
                          height: '1.25rem',
                          backgroundColor: 'rgba(239, 68, 68, 0.8)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '50%',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        ×
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleChatInterface; 