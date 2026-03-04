import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Importamos todas las páginas
import Dashboard from './pages/Dashboard';
import Test from './pages/Test';
import PanelAlumno from './pages/PanelAlumno';
import Repaso from './pages/Repaso'; 
import Esquema from './pages/Esquema';
import Auth from './pages/Auth';

// 1. CREAMOS EL VIGILANTE DE SEGURIDAD
// Esta función comprueba si existe una "pulsera" (token) guardada. 
// Si no la hay, te expulsa inmediatamente a la pantalla de login.
const RutaProtegida = ({ children }) => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* La puerta de entrada es libre (no tiene vigilante) */}
        <Route path="/login" element={<Auth />} />
        
        {/* A partir de aquí, envolvemos TODA la academia con el vigilante */}
        <Route path="/" element={<RutaProtegida><Dashboard /></RutaProtegida>} />
        <Route path="/test" element={<RutaProtegida><Test /></RutaProtegida>} />
        <Route path="/panel" element={<RutaProtegida><PanelAlumno /></RutaProtegida>} />
        <Route path="/repaso" element={<RutaProtegida><Repaso /></RutaProtegida>} />
        <Route path="/esquema" element={<RutaProtegida><Esquema /></RutaProtegida>} /> 
      </Routes>
    </BrowserRouter>
  );
}