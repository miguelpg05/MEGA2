import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ResumenIA() {
  // AHORA ES UN ARRAY: Guardamos los temas en una lista para permitir varios
  const [temasSeleccionados, setTemasSeleccionados] = useState(['Tema 1: La Constitución Española']);
  const [tiempo, setTiempo] = useState(15);
  const [nivel, setNivel] = useState('Intermedio');
  const [generando, setGenerando] = useState(false);
  const [resumen, setResumen] = useState('');

  // Lista de temas disponibles en tu plataforma
  const temasDisponibles = [
    "Tema 1: La Constitución Española",
    "Tema 2: El Gobierno y la Administración",
    "Derecho Constitucional (General)"
  ];

  // Función para marcar o desmarcar un tema
  const toggleTema = (tema) => {
    setTemasSeleccionados((prev) => {
      // Si ya está seleccionado, lo quitamos
      if (prev.includes(tema)) {
        return prev.filter(t => t !== tema);
      } 
      // Si no está seleccionado, lo añadimos
      else {
        return [...prev, tema];
      }
    });
  };

  const manejarGenerar = async () => {
    // Pequeña validación: que haya al menos un tema marcado
    if (temasSeleccionados.length === 0) {
      setResumen("⚠️ Por favor, selecciona al menos un tema para poder generar el resumen.");
      return;
    }

    setGenerando(true);
    setResumen(''); // Limpiamos el anterior
    
    try {
      const response = await fetch('http://127.0.0.1:8000/api/ia/resumir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          tiempo: tiempo, 
          nivel: nivel,
          // Unimos todos los temas seleccionados separados por coma
          // Ej: "Tema 1: La Constitución Española, Tema 2: El Gobierno..."
          tema: temasSeleccionados.join(', ')
        })
      });
      
      const data = await response.json();
      setResumen(data.resumen);
    } catch (error) {
      console.error("Error con la IA:", error);
      setResumen("Vaya, parece que la IA está descansando. Inténtalo de nuevo en un momento.");
    } finally {
      setGenerando(false);
    }
  };

  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-8 shadow-sm mb-8">
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">✨</span>
        <h2 className="text-xl font-semibold text-gray-800">Resumen Inteligente</h2>
      </div>

      {/* NUEVO: Selector Múltiple de Temas */}
      <div className="mb-8">
        <label className="block text-sm font-medium text-gray-500 mb-3">¿Qué temas quieres combinar en tu resumen?</label>
        <div className="flex flex-col gap-3">
          {temasDisponibles.map((tema) => {
            const estaSeleccionado = temasSeleccionados.includes(tema);
            return (
              <button
                key={tema}
                onClick={() => toggleTema(tema)}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all cursor-pointer text-left ${
                  estaSeleccionado 
                    ? 'border-orange-500 bg-orange-50 text-orange-700 font-medium' 
                    : 'border-gray-100 text-gray-500 hover:border-orange-200 hover:bg-orange-50/30'
                }`}
              >
                {/* Casilla de verificación visual */}
                <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                  estaSeleccionado ? 'bg-orange-500 border-orange-500 text-white' : 'border-gray-300 bg-white'
                }`}>
                  {estaSeleccionado && <span className="text-sm font-bold">✓</span>}
                </div>
                {tema}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* Selector de Tiempo */}
        <div>
          <label className="block text-sm font-medium text-gray-500 mb-3">¿Cuánto tiempo tienes?</label>
          <div className="flex gap-3">
            {[5, 15, 30].map((t) => (
              <button
                key={t}
                onClick={() => setTiempo(t)}
                className={`flex-1 py-2 rounded-xl border-2 transition-all cursor-pointer ${
                  tiempo === t ? 'border-orange-500 bg-orange-50 text-orange-600 font-medium' : 'border-gray-100 text-gray-400 hover:border-orange-200'
                }`}
              >
                {t} min
              </button>
            ))}
          </div>
        </div>

        {/* Selector de Nivel */}
        <div>
          <label className="block text-sm font-medium text-gray-500 mb-3">Tu nivel en estos temas</label>
          <div className="flex gap-3">
            {['Principiante', 'Intermedio', 'Avanzado'].map((n) => (
              <button
                key={n}
                onClick={() => setNivel(n)}
                className={`flex-1 py-2 text-xs md:text-sm rounded-xl border-2 transition-all cursor-pointer ${
                  nivel === n ? 'border-orange-500 bg-orange-50 text-orange-600 font-medium' : 'border-gray-100 text-gray-400 hover:border-orange-200'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={manejarGenerar}
        disabled={generando || temasSeleccionados.length === 0}
        className="w-full py-4 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl font-bold shadow-lg shadow-orange-500/20 transition-all cursor-pointer disabled:bg-gray-200 disabled:shadow-none"
      >
        {generando ? 'IA combinando temario...' : 'Generar resumen a medida'}
      </button>

      {/* Resultado del Resumen */}
      {resumen && (
        <div className="mt-8 p-8 bg-white rounded-2xl border border-orange-100 shadow-sm animate-fade-in text-gray-700 leading-relaxed prose prose-orange max-w-none">
          <ReactMarkdown>{resumen}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}