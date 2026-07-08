import api from './client';

// Auth
export const registerUser = (data) => api.post('/api/auth/register', data);
export const loginUser = (data) => api.post('/api/auth/login', data);
export const getMe = () => api.get('/api/auth/me');

// Buildings & devices
export const listBuildings = () => api.get('/api/buildings');
export const createBuilding = (data) => api.post('/api/buildings', data);
export const listDevices = (buildingId) =>
  api.get('/api/devices', { params: buildingId ? { building_id: buildingId } : {} });
export const createDevice = (data) => api.post('/api/devices', data);

// Datasets
export const listDatasets = () => api.get('/api/datasets');
export const uploadDataset = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Forecasts
export const generateForecast = (data) => api.post('/api/forecasts/generate', data);
export const getLatestForecast = (deviceId) => api.get(`/api/forecasts/latest/${deviceId}`);
export const getForecastsForDevice = (deviceId) => api.get(`/api/forecasts/device/${deviceId}`);

// Anomalies
export const detectAnomalies = (deviceId, method) =>
  api.post(`/api/anomalies/detect/${deviceId}`, null, { params: { method } });
export const getAnomaliesForDevice = (deviceId) => api.get(`/api/anomalies/device/${deviceId}`);
export const getPeakAnalysis = (deviceId) => api.get(`/api/anomalies/peaks/${deviceId}`);

// Recommendations
export const generateRecommendations = (deviceId) =>
  api.post(`/api/recommendations/generate/${deviceId}`);
export const getRecommendationsForDevice = (deviceId) =>
  api.get(`/api/recommendations/device/${deviceId}`);
export const getRecommendationsForBuilding = (buildingId) =>
  api.get(`/api/recommendations/building/${buildingId}`);

// Simulations
export const runSimulation = (data) => api.post('/api/simulations/run', data);
export const getSimulationsForBuilding = (buildingId) =>
  api.get(`/api/simulations/building/${buildingId}`);

// Analytics
export const getDeviceHistory = (deviceId, days = 30) =>
  api.get(`/api/analytics/device/${deviceId}/history`, { params: { days } });
export const getBuildingSummary = (buildingId) =>
  api.get(`/api/analytics/building/${buildingId}/summary`);
export const getForecastAccuracy = (deviceId) =>
  api.get(`/api/analytics/device/${deviceId}/forecast-accuracy`);
