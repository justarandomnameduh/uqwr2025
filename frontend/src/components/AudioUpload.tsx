import React, { useRef, useState } from 'react';
import { AudioFile } from '../types';
import { apiService } from '../services/api';

interface AudioUploadProps {
  onTranscriptionComplete: (transcriptionText: string) => void;
  onLoadingChange?: (isLoading: boolean) => void;
  disabled?: boolean;
}

const AudioUpload: React.FC<AudioUploadProps> = ({
  onTranscriptionComplete,
  onLoadingChange,
  disabled = false
}) => {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const validFiles = Array.from(files).filter(file => {
      const isAudio = file.type.startsWith('audio/') || 
                     /\.(mp3|wav|flac|ogg|m4a|aac|mp4|mov|avi|mkv)$/i.test(file.name);
      const isValidSize = file.size <= 100 * 1024 * 1024; // 100MB
      return isAudio && isValidSize;
    });

    if (validFiles.length === 0) {
      alert('Please select valid audio files (MP3, WAV, FLAC, OGG, M4A, AAC, or video files)');
      return;
    }

    // Process the first file (we'll handle one at a time for now)
    const audioFile = validFiles[0];
    const newAudioFile: AudioFile = {
      id: Date.now().toString(),
      file: audioFile,
      name: audioFile.name,
      isTranscribing: true,
    };

    setAudioFiles(prev => [newAudioFile, ...prev]);
    setIsTranscribing(true);
    onLoadingChange?.(true);

    try {
      const response = await apiService.uploadAndTranscribe(audioFile, false);
      
      if (response.status === 'success') {
        // Update the audio file with transcription result
        setAudioFiles(prev => prev.map(af => 
          af.id === newAudioFile.id 
            ? { ...af, isTranscribing: false, transcriptionText: response.transcription_text }
            : af
        ));

        // Call the callback to append text to chat input
        onTranscriptionComplete(response.transcription_text);
      } else {
        throw new Error('Transcription failed');
      }
    } catch (error: any) {
      console.error('Transcription error:', error);
      const errorMessage = error.response?.data?.message || error.message || 'Transcription failed';
      
      setAudioFiles(prev => prev.map(af => 
        af.id === newAudioFile.id 
          ? { ...af, isTranscribing: false, transcriptionError: errorMessage }
          : af
      ));
      
      alert(`Transcription failed: ${errorMessage}`);
    } finally {
      setIsTranscribing(false);
      onLoadingChange?.(false);
    }
  };

  const handleButtonClick = () => {
    if (disabled || isTranscribing) return;
    fileInputRef.current?.click();
  };

  const removeAudioFile = (fileId: string) => {
    setAudioFiles(prev => prev.filter(af => af.id !== fileId));
  };

  return (
    <>
      {/* Audio Upload Button */}
      <button
        type="button"
        onClick={handleButtonClick}
        disabled={disabled || isTranscribing}
        className="audio-upload-button"
        title="Upload audio file for transcription"
        style={{
          width: '2.5rem',
          height: '2.5rem',
          borderRadius: '0.375rem',
          border: '1px solid #d1d5db',
          backgroundColor: disabled || isTranscribing ? '#f3f4f6' : '#ffffff',
          color: disabled || isTranscribing ? '#9ca3af' : '#374151',
          cursor: disabled || isTranscribing ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.2rem',
          transition: 'all 0.2s',
          marginRight: '0.5rem'
        }}
        onMouseOver={(e) => {
          if (!disabled && !isTranscribing) {
            e.currentTarget.style.backgroundColor = '#f9fafb';
            e.currentTarget.style.borderColor = '#9ca3af';
          }
        }}
        onMouseOut={(e) => {
          if (!disabled && !isTranscribing) {
            e.currentTarget.style.backgroundColor = '#ffffff';
            e.currentTarget.style.borderColor = '#d1d5db';
          }
        }}
      >
        {isTranscribing ? <span className="spinner-char">⟳</span> : '🎵'}
      </button>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,.mp3,.wav,.flac,.ogg,.m4a,.aac,.mp4,.mov,.avi,.mkv"
        onChange={(e) => handleFileSelect(e.target.files)}
        style={{ display: 'none' }}
      />

      {/* Recent transcriptions list (optional, can be hidden) */}
      {audioFiles.length > 0 && (
        <div 
          style={{ 
            position: 'absolute',
            bottom: '100%',
            left: 0,
            right: 0,
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            marginBottom: '0.5rem',
            padding: '1rem',
            maxHeight: '200px',
            overflowY: 'auto',
            zIndex: 10
          }}
        >
          <div style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
            Recent Transcriptions
          </div>
          {audioFiles.slice(0, 3).map((audioFile) => (
            <div 
              key={audioFile.id}
              style={{
                padding: '0.5rem',
                borderRadius: '0.25rem',
                border: '1px solid #e5e7eb',
                marginBottom: '0.5rem',
                backgroundColor: '#f9fafb'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                    📎 {audioFile.name}
                  </div>
                  {audioFile.isTranscribing && (
                    <div style={{ fontSize: '0.75rem', color: '#3b82f6' }}>
                      ⟳ Transcribing...
                    </div>
                  )}
                  {audioFile.transcriptionText && (
                    <div style={{ fontSize: '0.75rem', color: '#059669' }}>
                      ✓ "{audioFile.transcriptionText.slice(0, 50)}..."
                    </div>
                  )}
                  {audioFile.transcriptionError && (
                    <div style={{ fontSize: '0.75rem', color: '#dc2626' }}>
                      ✗ {audioFile.transcriptionError}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => removeAudioFile(audioFile.id)}
                  style={{
                    marginLeft: '0.5rem',
                    width: '1.25rem',
                    height: '1.25rem',
                    borderRadius: '50%',
                    border: 'none',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
};

export default AudioUpload; 