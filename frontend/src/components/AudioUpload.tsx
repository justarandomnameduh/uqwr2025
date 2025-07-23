import React, { useState, useRef } from 'react';
import { Mic, Upload, Loader2 } from 'lucide-react';
import type { AudioFile } from '../types';
import { apiService } from '../services/api';

interface AudioUploadProps {
  onTranscriptionComplete: (text: string) => void;
  onLoadingChange?: (isLoading: boolean) => void;
  disabled?: boolean;
}

export const AudioUpload: React.FC<AudioUploadProps> = ({
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
      
      if (response.status === 'success' && response.transcription_text) {
        // Update the audio file with transcription
        setAudioFiles(prev => 
          prev.map(af => 
            af.id === newAudioFile.id 
              ? { ...af, isTranscribing: false, transcriptionText: response.transcription_text }
              : af
          )
        );
        
        // Call the callback with the transcription text
        onTranscriptionComplete(response.transcription_text);
      } else {
        throw new Error('Transcription failed or empty result');
      }
    } catch (error: any) {
      console.error('Transcription error:', error);
      
      setAudioFiles(prev => 
        prev.map(af => 
          af.id === newAudioFile.id 
            ? { ...af, isTranscribing: false, transcriptionError: error.message || 'Transcription failed' }
            : af
        )
      );
      
      alert(`Transcription failed: ${error.message || 'Unknown error'}`);
    } finally {
      setIsTranscribing(false);
      onLoadingChange?.(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => fileInputRef.current?.click()}
      disabled={disabled || isTranscribing}
      className={`
        flex items-center justify-center w-10 h-10 rounded-lg border transition-all
        ${disabled || isTranscribing 
          ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed' 
          : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400 hover:bg-gray-50 active:scale-95'
        }
      `}
      title={disabled ? 'Audio transcription disabled' : 'Upload audio file for transcription'}
    >
      {isTranscribing ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,video/*,.mp3,.wav,.flac,.ogg,.m4a,.aac,.mp4,.mov,.avi,.mkv"
        onChange={(e) => handleFileSelect(e.target.files)}
        className="hidden"
        disabled={disabled || isTranscribing}
      />
    </button>
  );
}; 