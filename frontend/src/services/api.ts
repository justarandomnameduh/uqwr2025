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
  model_loaded: boolean;
  model_info: any;
}

export interface ModelInfo {
  model_name: string;
  device: string;
  device_map: string;
  is_loaded: boolean;
  supports_images: boolean;
  supports_audio: boolean;
  supports_video: boolean;
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
}

export const apiService = new ApiService();
export default apiService; 