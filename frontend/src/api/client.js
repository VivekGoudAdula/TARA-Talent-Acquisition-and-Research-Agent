import axios from 'axios';

// In dev, Vite proxies /api → http://localhost:8000
// In production, set VITE_API_BASE_URL to your backend URL
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
    if (status !== 404) {
      console.error('[API Error]', err.config?.url, status, err.message);
    }
    return Promise.reject(err);
  }
);

export default api;
