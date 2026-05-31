import axios from 'axios';

// This will use Vercel's URL in production, and localhost on your computer!
export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const api = {
  // Auth
  register: (data) => axios.post(`${API_URL}/auth/register`, data),
  login: (credentials) => axios.post(`${API_URL}/auth/login`, credentials),
  
  // Elders
  getMyElders: () => {
    const token = localStorage.getItem('aarogya_token');
    // Added cache buster here to ensure new patients appear instantly
    return axios.get(`${API_URL}/elder-monitor/my-elders?t=${new Date().getTime()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  
  registerElder: (data) => {
    const token = localStorage.getItem('aarogya_token');
    return axios.post(`${API_URL}/elder-monitor/register`, data, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },

  // Health Logs
  getHistory: (elderId, days = 7) => {
    const token = localStorage.getItem('aarogya_token');
    // Cache buster added to the end of the URL
    return axios.get(`${API_URL}/elder-monitor/history/${elderId}?days=${days}&t=${new Date().getTime()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },

  logHealth: (data) => {
    const token = localStorage.getItem('aarogya_token');
    return axios.post(`${API_URL}/elder-monitor/log`, data, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },

  // Alerts
  getAlerts: (elderId, unresolvedOnly = true) => {
    const token = localStorage.getItem('aarogya_token');
    // Cache buster added to the end of the URL
    return axios.get(`${API_URL}/elder-monitor/alerts/${elderId}?unresolved_only=${unresolvedOnly}&t=${new Date().getTime()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  }
};