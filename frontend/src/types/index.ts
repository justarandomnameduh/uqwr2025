export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  images?: string[];
  timestamp: Date;
  isLoading?: boolean;
}

export interface UploadedImage {
  id: string;
  file: File;
  url: string;
  uploadedPath?: string;
  isUploading?: boolean;
  uploadError?: string;
}

export interface AudioFile {
  id: string;
  file: File;
  name: string;
  duration?: number;
  isTranscribing?: boolean;
  transcriptionText?: string;
  transcriptionError?: string;
}



export interface AppState {
  messages: Message[];
  uploadedImages: UploadedImage[];
  isGenerating: boolean;
  modelInfo: any;
  isConnected: boolean;
} 