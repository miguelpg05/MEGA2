import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiFetch } from '../api';
import { Cargando, MensajeError } from '../components/Estado';

export default function MaterialTema() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaId = location.state?.temaId;
  const temaNombre = location.state?.temaNombre || 'Tema';

  const [materiales, setMateriales] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [abriendo, setAbriendo] = useState(null);

  const cargar = useCallback(() => {
    if (!temaId) return;
    apiFetch(`/api/temas/${temaId}/materiales`)
      .then((r) => {
        if (!r.ok) throw new Error('respuesta no OK');
        return r.json();
      })
      .then((datos) => { setMateriales(datos); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, [temaId]);

  useEffect(() => {
    if (!temaId) {
      navigate('/');
      return;
    }
    cargar();
  }, [temaId, navigate, cargar]);

  const reintentar = () => { setCargando(true); setError(false); cargar(); };

  // El PDF va protegido por token, así que lo descargamos con la cabecera de
  // autorización y lo abrimos como blob en una pestaña nueva.
  const abrirPdf = async (material) => {
    setAbriendo(material.id);
    try {
      const res = await apiFetch(`/api/temas/${temaId}/materiales/${material.id}/descargar`);
      if (!res.ok) throw new Error('No se pudo abrir el PDF');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      alert('No se pudo abrir el PDF. Inténtalo de nuevo.');
    } finally {
      setAbriendo(null);
    }
  };

  const enMB = (b) => `${((b || 0) / (1024 * 1024)).toFixed(2)} MB`;

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-3xl mx-auto">
        <header className="mb-6 flex flex-wrap justify-between items-center gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-light text-gray-900">
              Material de <span className="font-semibold text-orange-500">{temaNombre}</span>
            </h1>
            <p className="text-gray-500 text-sm mt-1">Apuntes y documentos en PDF de este tema</p>
          </div>
          <button onClick={() => navigate('/')} className="text-sm bg-gray-100 text-gray-600 px-4 py-2 rounded-xl hover:bg-gray-200 cursor-pointer">← Volver</button>
        </header>

        {cargando ? (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm">
            <Cargando texto="Cargando material..." />
          </div>
        ) : error ? (
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
            <MensajeError texto="No se pudo cargar el material de este tema." onReintentar={reintentar} />
          </div>
        ) : materiales.length === 0 ? (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm text-center">
            <div className="text-4xl mb-3">📄</div>
            <p className="text-gray-600 font-medium">Este tema todavía no tiene material.</p>
            <p className="text-gray-400 text-sm mt-1">Tu profesor lo subirá desde el panel de administración.</p>
          </div>
        ) : (
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm divide-y divide-gray-100">
            {materiales.map((m) => (
              <div key={m.id} className="p-4 flex flex-wrap justify-between items-center gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 truncate">📄 {m.nombre_archivo}</p>
                  <p className="text-xs text-gray-400">{enMB(m.tamano_bytes)}</p>
                </div>
                <button
                  onClick={() => abrirPdf(m)}
                  disabled={abriendo === m.id}
                  className="shrink-0 px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-xl transition-colors cursor-pointer disabled:opacity-60"
                >
                  {abriendo === m.id ? 'Abriendo…' : 'Abrir PDF'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
