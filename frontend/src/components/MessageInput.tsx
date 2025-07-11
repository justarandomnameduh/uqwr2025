import React, { useState, useRef, useEffect } from 'react';
import { UploadedImage } from '../types';
import AudioUpload from './AudioUpload';

interface MessageInputProps {
  onSendMessage: (message: string, selectedImages: UploadedImage[]) => void;
  selectedImages: UploadedImage[];
  onRemoveSelectedImage: (image: UploadedImage) => void;
  onAudioLoadingChange?: (isLoading: boolean) => void;
  isGenerating: boolean;
  disabled: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  selectedImages,
  onRemoveSelectedImage,
  onAudioLoadingChange,
  isGenerating,
  disabled
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
    if ((!message.trim() && selectedImages.length === 0) || isGenerating || disabled) return;

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

  const canSend = (message.trim() || selectedImages.length > 0) && !isGenerating && !disabled;

  return (
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
                onClick={() => onRemoveSelectedImage(image)}
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

      <form onSubmit={handleSubmit} className="input-form">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={disabled ? "Backend disconnected..." : "Type your message..."}
          className="input-textarea"
          disabled={disabled || isGenerating}
          rows={1}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <AudioUpload
            onTranscriptionComplete={handleTranscriptionComplete}
            onLoadingChange={onAudioLoadingChange}
            disabled={disabled || isGenerating}
          />
          <button
            type="submit"
            disabled={!canSend}
            className={`input-button ${canSend ? 'input-button-send' : ''}`}
          >
            ➤
          </button>
        </div>
      </form>

      {selectedImages.length > 0 && (
        <div style={{ textAlign: 'center', fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem' }}>
          {selectedImages.length} image(s) selected • Press Enter to send
        </div>
      )}
    </div>
  );
};

export default MessageInput; 