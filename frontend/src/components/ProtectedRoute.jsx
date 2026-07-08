import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, roles }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex items-center justify-center h-full p-12">
        <div className="text-center">
          <p className="text-[var(--accent-danger)] font-mono-data text-sm mb-2">ACCESS DENIED</p>
          <p className="text-[var(--text-secondary)]">Your role ({user.role}) doesn't have permission to view this page.</p>
        </div>
      </div>
    );
  }

  return children;
}
