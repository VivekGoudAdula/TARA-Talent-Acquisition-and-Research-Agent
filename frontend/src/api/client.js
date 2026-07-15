import axios from 'axios';

// In dev, Vite proxies /api → http://localhost:8000 (axios uses relative URLs).
// EventSource cannot use the Vite proxy reliably — use API_BASE_URL for SSE.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.DEV ? 'http://localhost:8000' : '');

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Suppress 404s — hooks handle "not found" gracefully (return null / empty state).
    // Only log unexpected errors so the console stays clean.
    const status = err.response?.status;
    const isTimeout = err.code === 'ECONNABORTED' || err.message?.includes('timeout');
    if (status !== 404 && !isTimeout) {
      console.error('[API Error]', err.config?.url, status, err.message);
    }
    return Promise.reject(err);
  }
);

export default api;
