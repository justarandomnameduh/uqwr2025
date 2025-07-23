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

// API Types
export interface UploadedFile {
  original_name: string;
  saved_name: string;
  path: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  files: UploadedFile[];
}

export interface GenerateRequest {
  text: string;
  image_paths?: string[];
  max_new_tokens?: number;
  temperature?: number;
}

export interface GenerateResponse {
  status: string;
  response: string;
  text_input: string;
  images_used: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  vlm_model_loaded: boolean;
  vlm_model_info: any;
  transcription_model_loaded?: boolean;
  transcription_model_info?: any;
}

export interface ModelInfo {
  model_name: string;
  device: string;
  device_map: string;
  is_loaded: boolean;
  supports_images: boolean;
  supports_video: boolean;
}

export interface TranscriptionResponse {
  status: string;
  transcription_text: string;
  transcription_chunks?: any[];
  mp3_filename?: string;
  original_filename: string;
  return_timestamps: boolean;
}

export interface TranscriptionModelInfo {
  model_name: string;
  device: string;
  is_loaded: boolean;
  supports_audio: boolean;
  supported_formats: string[];
} 