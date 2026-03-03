import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// Importamos TODAS las páginas que hemos ido creando
import Dashboard from './pages/Dashboard';
import Test from './pages/Test';
import PanelAlumno from './pages/PanelAlumno';
import Repaso from './pages/Repaso'; 
import Esquema from './pages/Esquema'; // <-- ¡AQUÍ ESTÁ EL CULPABLE DE TU PANTALLA BLANCA!

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/test" element={<Test />} />
        <Route path="/panel" element={<PanelAlumno />} />
        <Route path="/repaso" element={<Repaso />} />
        {/* Y aquí registramos la ruta para que React sepa qué cargar */}
        <Route path="/esquema" element={<Esquema />} /> 
      </Routes>
    </BrowserRouter>
  );
}