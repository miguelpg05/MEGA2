import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';

// Importamos todas las páginas
import Dashboard from './pages/Dashboard';
import Repaso from './pages/Repaso';
import Auth from './pages/Auth';
import TestListado from './pages/TestListado';
import MaterialTema from './pages/MaterialTema';
import PersonalizarTest from './pages/PersonalizarTest';
import NoEncontrada from './pages/NoEncontrada';
import Privacidad from './pages/Privacidad';
import AvisoPrivacidad from './components/AvisoPrivacidad';
import ErrorBoundary from './components/ErrorBoundary';

import { AuthProvider, useAuth } from './auth/AuthContext';
import { PantallaCarga } from './components/Estado';
import { cargaDiferida } from './utils/cargaDiferida';

// Pantallas pesadas que se descargan solo cuando se abren (el alumno que entra al
// inicio no se baja el panel de administración ni el motor de tests).
const Test = cargaDiferida(() => import('./pages/Test'));
const Admin = cargaDiferida(() => import('./pages/Admin'));

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
  // RGPD: hasta aceptar la política de privacidad vigente no se entra
  if (usuario.debe_aceptar_privacidad) {
    return <AvisoPrivacidad />;
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
  if (usuario.debe_aceptar_privacidad) {
    return <AvisoPrivacidad />;
  }
  return children;
}

// Las rutas van dentro de un ErrorBoundary que se reinicia al cambiar de página:
// un fallo en una pantalla no deja la aplicación entera en blanco.
function Rutas() {
  const location = useLocation();
  return (
    <ErrorBoundary resetKey={location.pathname}>
      <Suspense fallback={<PantallaCarga texto="Cargando..." />}>
      <Routes>
        {/* La puerta de entrada es libre (no tiene vigilante) */}
        <Route path="/login" element={<Auth />} />
        <Route path="/privacidad" element={<Privacidad />} />

        {/* A partir de aquí, envolvemos TODA la academia con el vigilante */}
        <Route path="/" element={<RutaProtegida><Dashboard /></RutaProtegida>} />
        <Route path="/test" element={<RutaProtegida><Test /></RutaProtegida>} />
        {/* Ruta antigua de pruebas (mostraba siempre el tema 1): redirige al inicio */}
        <Route path="/panel" element={<Navigate to="/" replace />} />
        <Route path="/repaso" element={<RutaProtegida><Repaso /></RutaProtegida>} />
        <Route path="/personalizar" element={<RutaProtegida><PersonalizarTest /></RutaProtegida>} />
        <Route path="/listado-tests" element={<RutaProtegida><TestListado /></RutaProtegida>} />
        <Route path="/material" element={<RutaProtegida><MaterialTema /></RutaProtegida>} />

        {/* Panel de administración: solo profesores/admins */}
        <Route path="/admin" element={<RutaStaff><Admin /></RutaStaff>} />

        {/* Cualquier otra dirección: página 404 */}
        <Route path="*" element={<NoEncontrada />} />
      </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Rutas />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
