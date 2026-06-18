/**
 * api/client.ts
 * Axios HTTP client pre-configured for the ISRO AQI & HCHO backend API.
 * Base URL: http://localhost:8000/api/v1
 * Includes request/response interceptors for error handling and logging.
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

/* ─── Base Instance ───────────────────────────────────────────────────────────── */
export const apiClient = axios.create({
  baseURL: 'http://localhost:8001/api/v1',
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/* ─── Request Interceptor ─────────────────────────────────────────────────────── */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Could attach auth token here if needed
    // config.headers.Authorization = `Bearer ${token}`;
    if (import.meta.env.DEV) {
      console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.params ?? '');
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('[API] Request error:', error.message);
    return Promise.reject(error);
  }
);

/* ─── Response Interceptor ────────────────────────────────────────────────────── */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const url    = error.config?.url;

    if (status === 404) {
      console.warn(`[API] 404 Not Found: ${url}`);
    } else if (status === 422) {
      console.warn(`[API] 422 Validation Error: ${url}`, error.response?.data);
    } else if (status && status >= 500) {
      console.error(`[API] Server Error ${status}: ${url}`, error.response?.data);
    } else if (error.code === 'ECONNABORTED') {
      console.error('[API] Request timed out');
    } else if (!error.response) {
      console.warn('[API] Network error — is the backend running on port 8001?');
    }

    return Promise.reject(error);
  }
);

export default apiClient;
