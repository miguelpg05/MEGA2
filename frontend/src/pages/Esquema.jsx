import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import MermaidDiagram from '../components/MermaidDiagram';
import { apiFetch } from '../api';

export default function Esquema() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaNombre = location.state?.temaNombre || "Tema General";

  const [codigoDiagrama, setCodigoDiagrama] = useState('');
  // Inicializamos en true, así no hace falta volver a llamarlo en el useEffect
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    apiFetch('/api/ia/esquema', {
      method: 'POST',
      body: JSON.stringify({ tema_nombre: temaNombre })
    })
      .then(res => res.json())
      .then(datos => {
        console.log("Respuesta del Backend:", datos.esquema_codigo); // <-- Chivato para ver qué llega
        setCodigoDiagrama(datos.esquema_codigo);
        setCargando(false);
      })
      .catch(error => {
        console.error("Error al cargar el esquema:", error);
        setCodigoDiagrama("mindmap\nroot((Error de Red))\n Verifique conexión");
        setCargando(false);
      });
  }, [temaNombre]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4 font-sans relative">
      <div className="w-full max-w-6xl flex justify-between items-center mb-6">
        <button 
          onClick={() => navigate('/')} 
          className="text-gray-500 hover:text-gray-700 transition-colors font-medium flex items-center gap-2 bg-white px-4 py-2 rounded-xl shadow-sm border border-gray-100 cursor-pointer"
        >
          <span>←</span> Volver
        </button>
        <div className="text-sm font-bold text-orange-600 bg-orange-100 px-4 py-2 rounded-full flex items-center gap-2">
          <span>🧠</span> Mapa Visual
        </div>
      </div>

      <div className="w-full max-w-6xl bg-white rounded-[2rem] shadow-xl border border-gray-100 p-8 min-h-[70vh] flex flex-col">
        <h2 className="text-3xl font-bold text-gray-800 text-center mb-2">{temaNombre}</h2>
        <p className="text-gray-500 text-center mb-8">Mapa mental generado por IA</p>

        <div className="flex-1 flex items-center justify-center bg-orange-50/30 rounded-3xl border border-orange-100/50 p-4 overflow-hidden">
          {cargando ? (
            <div className="flex flex-col items-center justify-center animate-pulse p-12">
              <span className="text-7xl mb-6 opacity-50">🎨</span>
              <div className="text-orange-600 font-bold text-2xl">Dibujando el mapa mental...</div>
              <div className="text-gray-500 mt-2">Estructurando conceptos visualmente</div>
            </div>
          ) : (
            <div className="w-full h-full animate-fade-in flex justify-center">
                 <MermaidDiagram code={codigoDiagrama} />
            </div>
          )}
        </div>
        <p className="text-center text-xs text-gray-400 mt-6">Puedes hacer scroll si el diagrama es muy grande.</p>
      </div>
    </div>
  );
}