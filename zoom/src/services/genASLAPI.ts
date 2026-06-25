import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  ASLTranslationRequest, 
  ASLTranslationResponse, 
  ASLRecognitionRequest, 
  ASLRecognitionResponse,
  GenASLAPIResponse 
} from '@/types/zoom';

interface GenASLConfig {
  apiUrl: string;
  apiKey?: string;
  timeout?: number;
}

class GenASLAPIService {
  private client: AxiosInstance;
  private config: GenASLConfig;

  constructor(config: GenASLConfig) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.apiUrl,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` })
      }
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('GenASL API Error:', error);
        throw new Error(`API Error: ${error.response?.data?.message || error.message}`);
      }
    );
  }

  /**
   * Translate speech/text to ASL
   */
  async translateToASL(request: ASLTranslationRequest): Promise<ASLTranslationResponse> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<ASLTranslationResponse>> = 
        await this.client.post('/audio-to-sign', request);

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Translation failed');
      }

      return response.data.data!;
    } catch (error) {
      console.error('Failed to translate to ASL:', error);
      throw error;
    }
  }

  /**
   * Recognize ASL from video and convert to text
   */
  async recognizeASL(request: ASLRecognitionRequest): Promise<ASLRecognitionResponse> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<ASLRecognitionResponse>> = 
        await this.client.post('/sign-to-text', request);

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Recognition failed');
      }

      return response.data.data!;
    } catch (error) {
      console.error('Failed to recognize ASL:', error);
      throw error;
    }
  }

  /**
   * Get translation status (for long-running operations)
   */
  async getTranslationStatus(translationId: string): Promise<ASLTranslationResponse> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<ASLTranslationResponse>> = 
        await this.client.get(`/translation-status/${translationId}`);

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Failed to get status');
      }

      return response.data.data!;
    } catch (error) {
      console.error('Failed to get translation status:', error);
      throw error;
    }
  }

  /**
   * Get recognition status (for long-running operations)
   */
  async getRecognitionStatus(recognitionId: string): Promise<ASLRecognitionResponse> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<ASLRecognitionResponse>> = 
        await this.client.get(`/recognition-status/${recognitionId}`);

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Failed to get status');
      }

      return response.data.data!;
    } catch (error) {
      console.error('Failed to get recognition status:', error);
      throw error;
    }
  }

  /**
   * Convert text to speech (for accessibility)
   */
  async textToSpeech(text: string, voiceId?: string): Promise<ArrayBuffer> {
    try {
      const response = await this.client.post('/text-to-speech', 
        { text, voiceId },
        { responseType: 'arraybuffer' }
      );

      return response.data;
    } catch (error) {
      console.error('Failed to convert text to speech:', error);
      throw error;
    }
  }

  /**
   * Upload video file for processing
   */
  async uploadVideo(videoBlob: Blob, fileName: string): Promise<string> {
    try {
      const formData = new FormData();
      formData.append('video', videoBlob, fileName);

      const response: AxiosResponse<GenASLAPIResponse<{ uploadUrl: string }>> = 
        await this.client.post('/upload-video', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Upload failed');
      }

      return response.data.data!.uploadUrl;
    } catch (error) {
      console.error('Failed to upload video:', error);
      throw error;
    }
  }

  /**
   * Get available sign languages
   */
  async getAvailableLanguages(): Promise<string[]> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<{ languages: string[] }>> = 
        await this.client.get('/languages');

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Failed to get languages');
      }

      return response.data.data!.languages;
    } catch (error) {
      console.error('Failed to get available languages:', error);
      throw error;
    }
  }

  /**
   * Get user usage statistics
   */
  async getUsageStats(userId: string): Promise<any> {
    try {
      const response: AxiosResponse<GenASLAPIResponse<any>> = 
        await this.client.get(`/usage-stats/${userId}`);

      if (!response.data.success) {
        throw new Error(response.data.error?.message || 'Failed to get usage stats');
      }

      return response.data.data!;
    } catch (error) {
      console.error('Failed to get usage stats:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  /**
   * Update API configuration
   */
  updateConfig(newConfig: Partial<GenASLConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    // Update axios instance
    if (newConfig.apiUrl) {
      this.client.defaults.baseURL = newConfig.apiUrl;
    }
    
    if (newConfig.timeout) {
      this.client.defaults.timeout = newConfig.timeout;
    }
    
    if (newConfig.apiKey) {
      this.client.defaults.headers['Authorization'] = `Bearer ${newConfig.apiKey}`;
    }
  }
}

// Create and export service instance
let genASLAPI: GenASLAPIService;

export const initGenASLAPI = (config: GenASLConfig): GenASLAPIService => {
  genASLAPI = new GenASLAPIService(config);
  return genASLAPI;
};

export const getGenASLAPI = (): GenASLAPIService => {
  if (!genASLAPI) {
    throw new Error('GenASL API not initialized. Call initGenASLAPI() first.');
  }
  return genASLAPI;
};

export default GenASLAPIService;
