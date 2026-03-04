import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import Test from './pages/Test';
import PanelAlumno from './pages/PanelAlumno';
import Repaso from './pages/Repaso'; 
import Esquema from './pages/Esquema';
import Auth from './pages/Auth'; // <-- 1. Importamos la nueva página

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Auth />} /> {/* <-- 2. Añadimos la ruta */}
        
        <Route path="/" element={<Dashboard />} />
        <Route path="/test" element={<Test />} />
        <Route path="/panel" element={<PanelAlumno />} />
        <Route path="/repaso" element={<Repaso />} />
        <Route path="/esquema" element={<Esquema />} /> 
      </Routes>
    </BrowserRouter>
  );
}