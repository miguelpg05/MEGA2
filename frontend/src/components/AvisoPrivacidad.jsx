import React, { useState } from 'react';
import { apiFetch } from '../api';
import { useAuth } from '../auth/AuthContext';
import EnlacePrivacidad from './EnlacePrivacidad';

// Aceptación explícita de la política de privacidad (RGPD). Bloquea la plataforma
// hasta que el usuario la acepta; se vuelve a pedir si cambia la versión.
export default function AvisoPrivacidad() {
  const { recargar } = useAuth();
  const [marcado, setMarcado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  const aceptar = async () => {
    setEnviando(true);
    setError('');
    try {
      const r = await apiFetch('/api/auth/privacidad/aceptar', { method: 'POST' });
      if (!r.ok) throw new Error();
      await recargar();
    } catch {
      setError('No se pudo guardar. Inténtalo de nuevo.');
      setEnviando(false);
    }
  };

  const salir = async () => {
    try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch { /* da igual */ }
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 font-sans">
      <div role="dialog" aria-modal="true" aria-labelledby="titulo-privacidad"
        className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-sm border border-gray-100">
        <img src="/logo-192.png" alt="" width="48" height="48" className="w-12 h-12 mb-4" />
        <h1 id="titulo-privacidad" className="text-xl font-bold text-gray-800">Antes de empezar: tu privacidad</h1>
        <p className="text-gray-600 mt-3 text-sm leading-relaxed">
          Para usar la plataforma, Academia MEGA guarda tu nombre, tu correo de la academia y tus resultados
          (tests, respuestas, fallos para el repaso y uso del resumen con IA). Los usamos para tu preparación,
          tu progreso y el ranking de tu clase, donde tus compañeros te ven como «Nombre e inicial» y del que
          puedes ocultarte cuando quieras.
        </p>
        <p className="text-gray-600 mt-2 text-sm leading-relaxed">
          Puedes pedir a la academia una copia de tus datos o su eliminación.
        </p>
        <label className="flex items-start gap-3 mt-5 cursor-pointer select-none">
          <input type="checkbox" checked={marcado} onChange={(e) => setMarcado(e.target.checked)}
            className="mt-1 w-4 h-4 accent-orange-500" />
          <span className="text-sm text-gray-700">
            He leído y acepto la <EnlacePrivacidad>política de privacidad</EnlacePrivacidad>.
          </span>
        </label>
        {error && <p role="alert" className="text-sm text-red-600 mt-3">{error}</p>}
        <div className="flex flex-col-reverse sm:flex-row gap-3 mt-6">
          <button onClick={salir} className="flex-1 py-3 rounded-2xl border border-gray-200 text-gray-600 font-semibold hover:bg-gray-50 cursor-pointer">
            Salir
          </button>
          <button onClick={aceptar} disabled={!marcado || enviando}
            className="flex-1 py-3 rounded-2xl bg-orange-500 hover:bg-orange-600 text-white font-semibold cursor-pointer disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">
            {enviando ? 'Guardando…' : 'Aceptar y continuar'}
          </button>
        </div>
      </div>
    </div>
  );
}
