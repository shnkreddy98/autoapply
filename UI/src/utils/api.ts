/**
 * API configuration
 * Uses VITE_API_URL environment variable to determine the backend URL
 */

import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Configure axios to send cookies with all requests
axios.defaults.withCredentials = true;

// Add response interceptor to handle 401 errors
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear user data and redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * Build full API URL from endpoint
 * @param endpoint - API endpoint path (e.g., '/jobs', '/upload')
 * @returns Full API URL
 */
export const getApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};
