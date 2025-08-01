import axios from 'axios';
import type {
  UploadResponse,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  ModelInfo,
  TranscriptionResponse,
  TranscriptionModelInfo
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes timeout for VLM generation
});

interface AvailableModelsResponse {
  status: string;
  available_models: Record<string, {
    display_name: string;
    description: string;
    supports_images: boolean;
    supports_video: boolean;
    memory_requirements: string;
  }>;
  current_model_id: string | null;
  is_task_running: boolean;
}

interface SwitchModelResponse {
  status: string;
  message: string;
  current_model_id?: string;
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

  // Get available models
  async getAvailableModels(): Promise<AvailableModelsResponse> {
    const response = await api.get('/model/available');
    return response.data;
  }

  // Switch/load model
  async switchModel(modelId: string): Promise<SwitchModelResponse> {
    const response = await api.post('/model/switch', { model_id: modelId });
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

  // Generate streaming VLM response
  async generateResponseStream(
    request: GenerateRequest,
    onToken: (token: string) => void,
    onStart?: (metadata: { text_input: string; images_used: number }) => void,
    onError?: (error: string) => void,
    onDone?: () => void
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Stream not supported');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'start':
                  onStart?.(data);
                  break;
                case 'token':
                  onToken(data.content);
                  break;
                case 'done':
                  onDone?.();
                  return;
                case 'error':
                  onError?.(data.message);
                  return;
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      onError?.(error instanceof Error ? error.message : 'Unknown streaming error');
    }
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