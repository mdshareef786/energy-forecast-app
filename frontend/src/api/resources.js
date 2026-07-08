import api from './client';

export const authApi = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  me: () => api.get('/api/auth/me'),
};

export const assetsApi = {
  listBuildings: () => api.get('/api/buildings'),
  createBuilding: (data) => api.post('/api/buildings', data),
  listDevices: (buildingId) => api.get('/api/devices', { params: buildingId ? { building_id: buildingId } : {} }),
  createDevice: (data) => api.post('/api/devices', data),
};

export const datasetsApi = {
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list: () => api.get('/api/datasets'),
};

export const forecastsApi = {
  generate: (data) => api.post('/api/forecasts/generate', data),
  forDevice: (deviceId) => api.get(`/api/forecasts/device/${deviceId}`),
  latest: (deviceId) => api.get(`/api/forecasts/latest/${deviceId}`),
};

export const anomaliesApi = {
  detect: (deviceId, method) => api.post(`/api/anomalies/detect/${deviceId}`, null, { params: { method } }),
  forDevice: (deviceId) => api.get(`/api/anomalies/device/${deviceId}`),
  peaks: (deviceId) => api.get(`/api/anomalies/peaks/${deviceId}`),
};

export const recommendationsApi = {
  generate: (deviceId) => api.post(`/api/recommendations/generate/${deviceId}`),
  forDevice: (deviceId) => api.get(`/api/recommendations/device/${deviceId}`),
  forBuilding: (buildingId) => api.get(`/api/recommendations/building/${buildingId}`),
};

export const simulationsApi = {
  run: (data) => api.post('/api/simulations/run', data),
  forBuilding: (buildingId) => api.get(`/api/simulations/building/${buildingId}`),
};

export const analyticsApi = {
  deviceHistory: (deviceId, days = 30) => api.get(`/api/analytics/device/${deviceId}/history`, { params: { days } }),
  buildingSummary: (buildingId) => api.get(`/api/analytics/building/${buildingId}/summary`),
  forecastAccuracy: (deviceId) => api.get(`/api/analytics/device/${deviceId}/forecast-accuracy`),
};
