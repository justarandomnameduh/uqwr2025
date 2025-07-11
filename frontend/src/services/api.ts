import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes timeout for VLM generation
});

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



class ApiService {
  // Health check
  async checkHealth(): Promise<HealthResponse> {
    const response = await api.get('/health');
    return response.data;
  }

  // Get model information
  async getModelInfo(): Promise<ModelInfo> {
    const response = await api.get('/model/info');
    return response.data;
  }

  // Upload files
  async uploadFiles(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Generate VLM response
  async generateResponse(request: GenerateRequest): Promise<GenerateResponse> {
    const response = await api.post('/generate', request);
    return response.data;
  }

  // Get uploaded file URL
  getFileUrl(filename: string): string {
    return `${API_BASE_URL}/uploads/${filename}`;
  }

  // Delete uploaded file
  async deleteFile(filename: string): Promise<void> {
    await api.delete(`/uploads/${filename}`);
  }

  // Reload model
  async reloadModel(): Promise<{ status: string; message: string }> {
    const response = await api.post('/model/reload');
    return response.data;
  }

  // Transcription API methods
  async getTranscriptionModelInfo(): Promise<TranscriptionModelInfo> {
    const response = await api.get('/transcription/model/info');
    return response.data;
  }

  async reloadTranscriptionModel(): Promise<{ status: string; message: string }> {
    const response = await api.post('/transcription/model/reload');
    return response.data;
  }

  async uploadAndTranscribe(audioFile: File, returnTimestamps: boolean = false): Promise<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('return_timestamps', returnTimestamps.toString());
    formData.append('keep_mp3', 'false'); // Don't keep MP3 files to save storage

    const response = await api.post('/transcription/upload_and_transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes timeout for transcription
    });
    return response.data;
  }

}

export const apiService = new ApiService();
export default apiService; 