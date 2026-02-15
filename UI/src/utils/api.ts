/**
 * API configuration
 * Uses VITE_API_URL environment variable to determine the backend URL
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Build full API URL from endpoint
 * @param endpoint - API endpoint path (e.g., '/jobs', '/upload')
 * @returns Full API URL
 */
export const getApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};
