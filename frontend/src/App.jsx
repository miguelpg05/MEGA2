import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Importamos todas las páginas
import Dashboard from './pages/Dashboard';
import Test from './pages/Test';
import PanelAlumno from './pages/PanelAlumno';
import Repaso from './pages/Repaso';
import Esquema from './pages/Esquema';
import Auth from './pages/Auth';
import TestListado from './pages/TestListado';
import MaterialTema from './pages/MaterialTema';
import Admin from './pages/Admin';

import { AuthProvider, useAuth } from './auth/AuthContext';
import { PantallaCarga } from './components/Estado';

// VIGILANTE DE SEGURIDAD
// Además de comprobar que existe un token, valida la sesión contra el backend
// (/api/auth/me vía AuthContext). Mientras valida muestra una pantalla de carga;
// si la sesión no es válida, expulsa al login.
function RutaProtegida({ children }) {
  const token = localStorage.getItem('token');
  const { usuario, cargando } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (cargando) {
    return <PantallaCarga texto="Validando tu sesión..." />;
  }
  if (!usuario) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// Guardián para el panel de administración: exige rol admin (profesor) o superadmin.
function RutaStaff({ children }) {
  const token = localStorage.getItem('token');
  const { usuario, cargando } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (cargando) {
    return <PantallaCarga texto="Validando tu sesión..." />;
  }
  if (!usuario) {
    return <Navigate to="/login" replace />;
  }
  if (usuario.rol !== 'admin' && usuario.rol !== 'superadmin') {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* La puerta de entrada es libre (no tiene vigilante) */}
          <Route path="/login" element={<Auth />} />

          {/* A partir de aquí, envolvemos TODA la academia con el vigilante */}
          <Route path="/" element={<RutaProtegida><Dashboard /></RutaProtegida>} />
          <Route path="/test" element={<RutaProtegida><Test /></RutaProtegida>} />
          <Route path="/panel" element={<RutaProtegida><PanelAlumno /></RutaProtegida>} />
          <Route path="/repaso" element={<RutaProtegida><Repaso /></RutaProtegida>} />
          <Route path="/esquema" element={<RutaProtegida><Esquema /></RutaProtegida>} />
          <Route path="/listado-tests" element={<RutaProtegida><TestListado /></RutaProtegida>} />
          <Route path="/material" element={<RutaProtegida><MaterialTema /></RutaProtegida>} />

          {/* Panel de administración: solo profesores/admins */}
          <Route path="/admin" element={<RutaStaff><Admin /></RutaStaff>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
