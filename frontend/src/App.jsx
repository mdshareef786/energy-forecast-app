import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Buildings from './pages/Buildings';
import BuildingDetail from './pages/BuildingDetail';
import DeviceDetail from './pages/DeviceDetail';
import DatasetUpload from './pages/DatasetUpload';
import LiveMonitor from './pages/LiveMonitor';

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />

      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/buildings" element={<Buildings />} />
                <Route path="/buildings/:buildingId" element={<BuildingDetail />} />
                <Route path="/devices/:deviceId" element={<DeviceDetail />} />
                <Route path="/datasets" element={<DatasetUpload />} />
                <Route path="/live" element={<LiveMonitor />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
