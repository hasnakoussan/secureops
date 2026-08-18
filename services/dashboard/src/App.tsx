import { type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ScanList } from "./pages/ScanList";
import { ScanDetail } from "./pages/ScanDetail";
import { NewScan } from "./pages/NewScan";
import { Team } from "./pages/Team";
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <p className="text-sm text-[var(--color-text-muted)]">Chargement...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/scans"
        element={
          <ProtectedRoute>
            <ScanList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scans/:id"
        element={
          <ProtectedRoute>
            <ScanDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/new-scan"
        element={
          <ProtectedRoute>
            <NewScan />
          </ProtectedRoute>
        }
      />
      <Route
         path="/team"
         element={
           <ProtectedRoute>
             <Team />
           </ProtectedRoute>
         }
       />
      <Route path="*" element={<Navigate to="/scans" replace />} />
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
