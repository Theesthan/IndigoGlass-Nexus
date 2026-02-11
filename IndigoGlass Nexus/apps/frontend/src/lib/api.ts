// =============================================================================
// IndigoGlass Nexus - API Client
// =============================================================================

import axios, { AxiosError, AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = Cookies.get('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          
          Cookies.set('access_token', access_token, { expires: 1 / 96 }); // 15 min
          Cookies.set('refresh_token', newRefreshToken, { expires: 7 });
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          Cookies.remove('access_token');
          Cookies.remove('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// =============================================================================
// Auth API
// =============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
  };
}

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', data);
    return response.data;
  },
  
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
  },
  
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// =============================================================================
// KPI API
// =============================================================================

export interface KpiOverview {
  total_revenue: number;
  revenue_trend: number;
  total_orders: number;
  orders_trend: number;
  avg_fill_rate: number;
  fill_rate_trend: number;
  total_co2_kg: number;
  co2_trend: number;
  on_time_delivery_pct: number;
  otd_trend: number;
}

export const kpiApi = {
  getOverview: async (): Promise<KpiOverview> => {
    const response = await api.get('/kpis/overview');
    return response.data;
  },
  
  getTrends: async (metric: string, days: number = 30) => {
    const response = await api.get(`/kpis/trends/${metric}`, { params: { days } });
    return response.data;
  },
};

// =============================================================================
// Forecast API
// =============================================================================

export interface ForecastRecord {
  date: string;
  product_id: string;
  product_name: string;
  location_id: string;
  location_name: string;
  forecast_qty: number;
  forecast_lower: number;
  forecast_upper: number;
  actual_qty?: number;
}

export const forecastApi = {
  getForecasts: async (params?: { 
    product_id?: string; 
    location_id?: string;
    start_date?: string;
    end_date?: string;
  }) => {
    const response = await api.get('/forecast', { params });
    return response.data;
  },
  
  getAccuracy: async () => {
    const response = await api.get('/forecast/accuracy');
    return response.data;
  },
  
  getModels: async () => {
    const response = await api.get('/forecast/models');
    return response.data;
  },
};

// =============================================================================
// Inventory API
// =============================================================================

export interface InventoryRisk {
  product_id: string;
  product_name: string;
  location_id: string;
  location_name: string;
  quantity_available: number;
  days_of_supply: number;
  risk_level: 'critical' | 'low' | 'ok';
}

export const inventoryApi = {
  getRisk: async () => {
    const response = await api.get('/inventory/risk');
    return response.data;
  },
  
  getWarehouses: async () => {
    const response = await api.get('/inventory/warehouses');
    return response.data;
  },
  
  getHeatmap: async () => {
    const response = await api.get('/inventory/heatmap');
    return response.data;
  },
};

// =============================================================================
// Optimizer API
// =============================================================================

export interface RoutePlanRequest {
  origin: {
    id: string;
    latitude: number;
    longitude: number;
  };
  destinations: Array<{
    id: string;
    name: string;
    latitude: number;
    longitude: number;
    demand: number;
  }>;
  num_vehicles: number;
}

export const optimizerApi = {
  planRoute: async (data: RoutePlanRequest) => {
    const response = await api.post('/optimizer/plan', data);
    return response.data;
  },
  
  getHistory: async () => {
    const response = await api.get('/optimizer/history');
    return response.data;
  },
};

// =============================================================================
// Sustainability API
// =============================================================================

export const sustainabilityApi = {
  getKpis: async () => {
    const response = await api.get('/sustainability/kpis');
    return response.data;
  },
  
  getByMode: async () => {
    const response = await api.get('/sustainability/by-mode');
    return response.data;
  },
  
  getHotspots: async () => {
    const response = await api.get('/sustainability/hotspots');
    return response.data;
  },
  
  getTrend: async (days: number = 30) => {
    const response = await api.get('/sustainability/trend', { params: { days } });
    return response.data;
  },
};

// =============================================================================
// Graph API
// =============================================================================

export const graphApi = {
  getNetwork: async () => {
    const response = await api.get('/graph/network');
    return response.data;
  },
  
  getImpact: async (nodeId: string, depth: number = 2) => {
    const response = await api.get('/graph/impact', { params: { node_id: nodeId, depth } });
    return response.data;
  },
  
  getCriticalPath: async () => {
    const response = await api.get('/graph/critical-path');
    return response.data;
  },
};

// =============================================================================
// Export API
// =============================================================================

export const exportApi = {
  downloadSales: async (format: 'csv' | 'json' = 'csv') => {
    const response = await api.get('/exports/sales', { 
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
  
  downloadForecast: async (format: 'csv' | 'json' = 'csv') => {
    const response = await api.get('/exports/forecast', {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
  
  generateReport: async (reportType: string) => {
    const response = await api.post('/exports/report', { type: reportType });
    return response.data;
  },
};
