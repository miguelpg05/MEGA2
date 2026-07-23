import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import MermaidDiagram from '../components/MermaidDiagram';
import { apiFetch } from '../api';
import { MensajeError } from '../components/Estado';

export default function Esquema() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaId = location.state?.temaId || null;
  const temaNombre = location.state?.temaNombre || 'Tema General';

  const [materiales, setMateriales] = useState([]);
  const [fuente, setFuente] = useState('tema');   // 'tema' | 'texto' | id-de-pdf (número)
  const [textoLibre, setTextoLibre] = useState('');

  const [codigoDiagrama, setCodigoDiagrama] = useState('');
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState('');

  // Cargamos los PDFs del tema para poder elegir uno como fuente
  useEffect(() => {
    if (!temaId) return;
    apiFetch(`/api/temas/${temaId}/materiales`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setMateriales(Array.isArray(d) ? d : []))
      .catch(() => setMateriales([]));
  }, [temaId]);

  const generar = useCallback(async () => {
    setError('');
    setGenerando(true);
    setCodigoDiagrama('');

    const cuerpo = { tema_nombre: temaNombre, tema_id: temaId };
    if (fuente === 'texto') {
      if (!textoLibre.trim()) { setError('Escribe o pega algún texto para generar el esquema.'); setGenerando(false); return; }
      cuerpo.texto = textoLibre;
    } else if (fuente !== 'tema') {
      cuerpo.material_id = Number(fuente);
    }

    try {
      const res = await apiFetch('/api/ia/esquema', { method: 'POST', body: JSON.stringify(cuerpo) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'No se pudo generar el esquema.');
      setCodigoDiagrama(data.esquema_codigo);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerando(false);
    }
  }, [temaNombre, temaId, fuente, textoLibre]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4 font-sans">
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

      <div className="w-full max-w-6xl bg-white rounded-[2rem] shadow-xl border border-gray-100 p-5 sm:p-8 min-h-[70vh] flex flex-col">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 text-center mb-2">{temaNombre}</h2>
        <p className="text-gray-500 text-center mb-6">Mapa mental generado por IA</p>

        {/* Selector de material fuente */}
        <div className="bg-gray-50 rounded-2xl p-4 mb-6">
          <label className="block text-sm font-medium text-gray-600 mb-2">¿Sobre qué material generamos el esquema?</label>
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={fuente}
              onChange={(e) => setFuente(e.target.value)}
              className="flex-1 px-4 py-2 rounded-xl bg-white border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="tema">Solo el tema (por su título)</option>
              {materiales.map((m) => (
                <option key={m.id} value={m.id}>📄 {m.nombre_archivo}</option>
              ))}
              <option value="texto">✍️ Escribir / pegar mi propio texto</option>
            </select>
            <button
              onClick={generar}
              disabled={generando}
              className="px-6 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {generando ? 'Generando…' : 'Generar esquema'}
            </button>
          </div>

          {fuente === 'texto' && (
            <textarea
              value={textoLibre}
              onChange={(e) => setTextoLibre(e.target.value)}
              rows={5}
              placeholder="Pega aquí el texto del temario sobre el que quieres el mapa mental…"
              className="mt-3 w-full px-4 py-2 rounded-xl bg-white border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500"
            />
          )}
          {temaId && materiales.length === 0 && (
            <p className="text-xs text-gray-400 mt-2">Este tema no tiene PDFs; puedes generar por el título o pegar tu propio texto.</p>
          )}
        </div>

        {error && (
          <div className="mb-4">
            <MensajeError texto={error} onReintentar={generar} />
          </div>
        )}

        <div className="flex-1 flex items-center justify-center bg-orange-50/30 rounded-3xl border border-orange-100/50 p-2 sm:p-4 overflow-auto">
          {generando ? (
            <div className="flex flex-col items-center justify-center animate-pulse p-12">
              <span className="text-7xl mb-6 opacity-50">🎨</span>
              <div className="text-orange-600 font-bold text-2xl">Dibujando el mapa mental…</div>
              <div className="text-gray-500 mt-2">Estructurando conceptos visualmente</div>
            </div>
          ) : codigoDiagrama ? (
            <div className="w-full h-full animate-fade-in flex justify-center">
              <MermaidDiagram code={codigoDiagrama} />
            </div>
          ) : (
            <div className="text-center text-gray-400 p-12">
              <div className="text-5xl mb-3 opacity-50">🗺️</div>
              <p className="font-medium">Elige el material y pulsa «Generar esquema».</p>
            </div>
          )}
        </div>
        <p className="text-center text-xs text-gray-400 mt-6">Puedes hacer scroll si el diagrama es muy grande.</p>
      </div>
    </div>
  );
}
