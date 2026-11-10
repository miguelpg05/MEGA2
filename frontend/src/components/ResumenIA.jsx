import React, { useState, useEffect, useCallback } from 'react';
import ApuntesMarkdown from './ApuntesMarkdown';
import { apiFetch } from '../api';
import { MensajeError } from './Estado';

export default function ResumenIA() {
  const [temasDisponibles, setTemasDisponibles] = useState([]); // [{id, nombre}]
  const [materiales, setMateriales] = useState([]);             // [{id, nombre_archivo, tema_nombre}]

  const [fuente, setFuente] = useState('temas');   // 'temas' | 'texto' | id-de-pdf
  const [temasSeleccionados, setTemasSeleccionados] = useState([]);
  const [textoLibre, setTextoLibre] = useState('');
  const [verSinPdf, setVerSinPdf] = useState(false);

  const [tiempo, setTiempo] = useState(15);
  const [nivel, setNivel] = useState('Intermedio');
  const [generando, setGenerando] = useState(false);
  const [resumen, setResumen] = useState('');
  const [info, setInfo] = useState(null); // { titulo, documentos, recortado }
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

  // Nº de PDFs de cada tema: solo se pueden resumir temas con material
  const pdfsPorTema = materiales.reduce((acc, m) => ({ ...acc, [m.tema_id]: (acc[m.tema_id] || 0) + 1 }), {});

  // Primero los temas con PDF; los que no tienen se pliegan para no alargar la página
  const temasConPdf = temasDisponibles.filter((t) => pdfsPorTema[t.id]);
  const temasSinPdf = temasDisponibles.filter((t) => !pdfsPorTema[t.id]);
  const temasAMostrar = verSinPdf ? [...temasConPdf, ...temasSinPdf] : temasConPdf;

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
    setInfo(null);
    try {
      const response = await apiFetch('/api/ia/resumir', { method: 'POST', body: JSON.stringify(cuerpo) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo generar el resumen.');
      setResumen(data.resumen);
      setInfo({ titulo: cuerpo.tema, documentos: data.documentos || [], recortado: Boolean(data.recortado) });
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
          <option value="temas">📚 Temas seleccionados (usa sus PDFs)</option>
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
          <p className="text-xs text-gray-400 mb-3">El resumen se hace con los <strong>PDFs de la academia</strong> de los temas que marques. Los temas sin PDF no se pueden resumir.</p>
          {temasDisponibles.length === 0 && (
            <p className="text-sm text-gray-400 italic">Aún no hay temas disponibles para tus cursos.</p>
          )}
          <div className="flex flex-col gap-3">
            {temasDisponibles.length > 0 && temasConPdf.length === 0 && (
              <p className="text-sm text-gray-400 italic">Ningún tema tiene PDF todavía. Puedes pegar un texto propio.</p>
            )}
            {temasAMostrar.map((t) => {
              const estaSeleccionado = temasSeleccionados.includes(t.id);
              const nPdfs = pdfsPorTema[t.id] || 0;
              return (
                <button
                  key={t.id}
                  onClick={() => nPdfs && toggleTema(t.id)}
                  disabled={!nPdfs}
                  title={nPdfs ? undefined : 'Este tema aún no tiene PDF'}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left ${!nPdfs ? 'border-gray-100 text-gray-300 cursor-not-allowed' : estaSeleccionado ? 'border-orange-500 bg-orange-50 text-orange-700 font-medium cursor-pointer' : 'border-gray-100 text-gray-500 hover:border-orange-200 hover:bg-orange-50/30 cursor-pointer'}`}
                >
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${estaSeleccionado ? 'bg-orange-500 border-orange-500 text-white' : 'border-gray-300 bg-white'}`}>
                    {estaSeleccionado && <span className="text-sm font-bold">✓</span>}
                  </div>
                  <span className="flex-1">{t.nombre}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${nPdfs ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-400'}`}>
                    {nPdfs ? `📄 ${nPdfs} PDF${nPdfs > 1 ? 's' : ''}` : 'sin PDF'}
                  </span>
                </button>
              );
            })}
            {temasSinPdf.length > 0 && (
              <button
                onClick={() => setVerSinPdf((v) => !v)}
                className="self-start text-sm text-gray-500 hover:text-orange-600 font-medium cursor-pointer"
                aria-expanded={verSinPdf}
              >
                {verSinPdf ? 'Ocultar temas sin material' : `Ver ${temasSinPdf.length} ${temasSinPdf.length === 1 ? 'tema' : 'temas'} sin material ▾`}
              </button>
            )}
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
        <article className="mt-8 bg-white rounded-3xl border border-orange-100 shadow-sm animate-fade-in overflow-hidden">
          <header className="px-6 sm:px-8 py-5 bg-gradient-to-r from-orange-500 to-amber-500 text-white">
            <p className="text-xs font-semibold uppercase tracking-wider text-orange-100">Apuntes generados · {tiempo} min · {nivel}</p>
            <h3 className="text-xl sm:text-2xl font-bold mt-1">{info?.titulo}</h3>
            {info?.documentos?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {info.documentos.map((d) => (
                  <span key={d} className="text-xs bg-white/20 rounded-full px-2.5 py-1">📄 {d}</span>
                ))}
              </div>
            )}
          </header>
          {info?.recortado && (
            <p className="mx-6 sm:mx-8 mt-5 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5">
              ℹ️ El material es largo: la IA ha trabajado con fragmentos repartidos por todo el documento. Para estudiar a fondo, consulta también el PDF completo.
            </p>
          )}
          <div className="px-6 sm:px-8 py-6">
            <ApuntesMarkdown markdown={resumen} />
          </div>
        </article>
      )}
    </div>
  );
}
