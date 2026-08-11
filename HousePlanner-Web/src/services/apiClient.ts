import axios from 'axios';

let inMemoryToken: string | null = null;

// Setter to update the in-memory token from our Redux auth flows
export const setInMemoryToken = (token: string | null) => {
  inMemoryToken = token;
};

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios request interceptor to inject the Bearer token dynamically
apiClient.interceptors.request.use(
  (config) => {
    if (inMemoryToken && config.headers) {
      config.headers.Authorization = `Bearer ${inMemoryToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default apiClient;
