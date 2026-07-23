import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { apiFetch } from '../api';
import { MensajeError } from './Estado';

export default function ResumenIA() {
  const [temasDisponibles, setTemasDisponibles] = useState([]); // [{id, nombre}]
  const [materiales, setMateriales] = useState([]);             // [{id, nombre_archivo, tema_nombre}]

  const [fuente, setFuente] = useState('temas');   // 'temas' | 'texto' | id-de-pdf
  const [temasSeleccionados, setTemasSeleccionados] = useState([]);
  const [textoLibre, setTextoLibre] = useState('');

  const [tiempo, setTiempo] = useState(15);
  const [nivel, setNivel] = useState('Intermedio');
  const [generando, setGenerando] = useState(false);
  const [resumen, setResumen] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(() => {
    apiFetch('/api/temas')
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setTemasDisponibles(Array.isArray(d) ? d : []))
      .catch(() => setTemasDisponibles([]));
    apiFetch('/api/temas/materiales')
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setMateriales(Array.isArray(d) ? d : []))
      .catch(() => setMateriales([]));
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const toggleTema = (id) => {
    setTemasSeleccionados((prev) => prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]);
  };

  const generar = async () => {
    setError('');
    const cuerpo = { tiempo, nivel, tema: '' };

    if (fuente === 'temas') {
      if (temasSeleccionados.length === 0) { setError('Selecciona al menos un tema.'); return; }
      const seleccionados = temasDisponibles.filter((t) => temasSeleccionados.includes(t.id));
      cuerpo.tema = seleccionados.map((t) => t.nombre).join(', ');
      cuerpo.tema_ids = temasSeleccionados; // el backend usará TODOS los PDFs de estos temas
    } else if (fuente === 'texto') {
      if (!textoLibre.trim()) { setError('Escribe o pega algún texto para resumir.'); return; }
      cuerpo.tema = 'el texto aportado';
      cuerpo.texto = textoLibre;
    } else {
      const mat = materiales.find((m) => String(m.id) === String(fuente));
      cuerpo.tema = mat?.tema_nombre || 'el material seleccionado';
      cuerpo.material_id = Number(fuente);
    }

    setGenerando(true);
    setResumen('');
    try {
      const response = await apiFetch('/api/ia/resumir', { method: 'POST', body: JSON.stringify(cuerpo) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo generar el resumen.');
      setResumen(data.resumen);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerando(false);
    }
  };

  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-6 sm:p-8 shadow-sm mb-8">
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">✨</span>
        <h2 className="text-xl font-semibold text-gray-800">Resumen Inteligente</h2>
      </div>

      {/* Fuente del resumen */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-500 mb-2">¿Sobre qué material lo generamos?</label>
        <select
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500"
        >
          <option value="temas">Temas seleccionados (por su título)</option>
          {materiales.map((m) => (
            <option key={m.id} value={m.id}>📄 {m.tema_nombre ? `${m.tema_nombre} · ` : ''}{m.nombre_archivo}</option>
          ))}
          <option value="texto">✍️ Escribir / pegar mi propio texto</option>
        </select>
      </div>

      {/* Selección múltiple de temas (solo en modo "temas") */}
      {fuente === 'temas' && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-500 mb-1">¿Qué temas quieres combinar?</label>
          <p className="text-xs text-gray-400 mb-3">Se usará <strong>todo el material (PDFs)</strong> de los temas que marques.</p>
          {temasDisponibles.length === 0 && (
            <p className="text-sm text-gray-400 italic">Aún no hay temas disponibles para tus cursos.</p>
          )}
          <div className="flex flex-col gap-3">
            {temasDisponibles.map((t) => {
              const estaSeleccionado = temasSeleccionados.includes(t.id);
              return (
                <button
                  key={t.id}
                  onClick={() => toggleTema(t.id)}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all cursor-pointer text-left ${estaSeleccionado ? 'border-orange-500 bg-orange-50 text-orange-700 font-medium' : 'border-gray-100 text-gray-500 hover:border-orange-200 hover:bg-orange-50/30'}`}
                >
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${estaSeleccionado ? 'bg-orange-500 border-orange-500 text-white' : 'border-gray-300 bg-white'}`}>
                    {estaSeleccionado && <span className="text-sm font-bold">✓</span>}
                  </div>
                  {t.nombre}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Texto propio */}
      {fuente === 'texto' && (
        <div className="mb-6">
          <textarea
            value={textoLibre}
            onChange={(e) => setTextoLibre(e.target.value)}
            rows={6}
            placeholder="Pega aquí el texto del temario que quieres resumir…"
            className="w-full px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500"
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div>
          <label className="block text-sm font-medium text-gray-500 mb-3">¿Cuánto tiempo tienes?</label>
          <div className="flex gap-3">
            {[5, 15, 30].map((t) => (
              <button key={t} onClick={() => setTiempo(t)}
                className={`flex-1 py-2 rounded-xl border-2 transition-all cursor-pointer ${tiempo === t ? 'border-orange-500 bg-orange-50 text-orange-600 font-medium' : 'border-gray-100 text-gray-400 hover:border-orange-200'}`}>
                {t} min
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-500 mb-3">Tu nivel</label>
          <div className="flex gap-3">
            {['Principiante', 'Intermedio', 'Avanzado'].map((n) => (
              <button key={n} onClick={() => setNivel(n)}
                className={`flex-1 py-2 text-xs md:text-sm rounded-xl border-2 transition-all cursor-pointer ${nivel === n ? 'border-orange-500 bg-orange-50 text-orange-600 font-medium' : 'border-gray-100 text-gray-400 hover:border-orange-200'}`}>
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={generar}
        disabled={generando}
        className="w-full py-4 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl font-bold shadow-lg shadow-orange-500/20 transition-all cursor-pointer disabled:bg-gray-200 disabled:shadow-none"
      >
        {generando ? 'La IA está resumiendo…' : 'Generar resumen a medida'}
      </button>

      {error && (
        <div className="mt-6">
          <MensajeError texto={error} onReintentar={generar} />
        </div>
      )}

      {resumen && !error && (
        <div className="mt-8 p-6 sm:p-8 bg-white rounded-2xl border border-orange-100 shadow-sm animate-fade-in text-gray-700 leading-relaxed prose prose-orange max-w-none">
          <ReactMarkdown>{resumen}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
