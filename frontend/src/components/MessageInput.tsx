import React, { useState, useRef, useEffect } from 'react';
import { Send, X } from 'lucide-react';
import type { UploadedImage } from '../types';
import { AudioUpload } from './AudioUpload';

interface MessageInputProps {
  onSendMessage: (message: string, selectedImages: UploadedImage[]) => void;
  selectedImages: UploadedImage[];
  onRemoveSelectedImage: (image: UploadedImage) => void;
  onAudioLoadingChange?: (isLoading: boolean) => void;
  isGenerating: boolean;
  disabled: boolean;
  isWaitingForLogConfirmation?: boolean;
  isConnected?: boolean;
  currentModelId?: string | null;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  selectedImages,
  onRemoveSelectedImage,
  onAudioLoadingChange,
  isGenerating,
  disabled,
  isWaitingForLogConfirmation = false,
  isConnected = true,
  currentModelId = null
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((!message.trim() && selectedImages.length === 0) || isGenerating || disabled || isWaitingForLogConfirmation) return;

    onSendMessage(message, selectedImages);
    setMessage('');
  };

  const handleTranscriptionComplete = (transcriptionText: string) => {
    // Append transcription to existing message with a space if there's already text
    setMessage(prev => {
      const separator = prev.trim() ? ' ' : '';
      return prev + separator + transcriptionText;
    });
    
    // Focus the textarea after transcription
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  };

  const canSend = (message.trim() || selectedImages.length > 0) && !isGenerating && !disabled && !isWaitingForLogConfirmation;

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* Selected Images Preview */}
      {selectedImages.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {selectedImages.map((image) => (
            <div
              key={image.id}
              className="relative inline-block"
            >
              <img
                src={image.url}
                alt="Selected"
                className="w-16 h-16 object-cover rounded-lg border border-gray-200"
              />
              <button
                onClick={() => onRemoveSelectedImage(image)}
                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
              >
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              disabled ? 
                (!isConnected ? "Backend disconnected..." :
                 !currentModelId ? "Please select a model..." :
                 "Please create or select a session...") :
              isWaitingForLogConfirmation ? "Waiting for backend confirmation..." :
              isGenerating ? "AI is thinking..." :
              "Type your message..."
            }
            className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            disabled={disabled || isGenerating || isWaitingForLogConfirmation}
            rows={1}
            style={{ minHeight: '48px', maxHeight: '120px' }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
        </div>
        
        <div className="flex items-center gap-2">
          <AudioUpload
            onTranscriptionComplete={handleTranscriptionComplete}
            onLoadingChange={onAudioLoadingChange}
            disabled={disabled || isGenerating || isWaitingForLogConfirmation}
          />
          
          <button
            type="submit"
            disabled={!canSend}
            className={`
              flex items-center justify-center w-12 h-12 rounded-lg transition-all
              ${canSend
                ? 'bg-blue-500 hover:bg-blue-600 active:scale-95 text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>

      {selectedImages.length > 0 && (
        <div className="mt-2 text-center text-sm text-gray-500">
          {selectedImages.length} image(s) selected • Press Enter to send
        </div>
      )}
    </div>
  );
}; 