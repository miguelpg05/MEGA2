import React, { useState } from 'react';
import { apiFetch } from '../api';
import { useAuth } from '../auth/AuthContext';
import EnlacePrivacidad from './EnlacePrivacidad';

// «Mi cuenta»: datos básicos, aparecer o no en el ranking, descargar mis datos y
// cómo solicitar la eliminación (RGPD).
export default function MiCuenta({ onCerrar }) {
  const { usuario, recargar } = useAuth();
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState('');

  const cambiarRanking = async (visible) => {
    setGuardando(true);
    setAviso('');
    try {
      const r = await apiFetch('/api/auth/ranking', { method: 'PUT', body: JSON.stringify({ visible }) });
      if (!r.ok) throw new Error();
      await recargar();
      setAviso(visible ? 'Vuelves a aparecer en el ranking.' : 'Ya no apareces en el ranking de tu clase.');
    } catch {
      setAviso('No se pudo guardar el cambio.');
    } finally {
      setGuardando(false);
    }
  };

  const descargarDatos = async () => {
    setAviso('');
    try {
      const r = await apiFetch('/api/auth/mis-datos');
      if (!r.ok) throw new Error();
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mis_datos_academia_mega.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setAviso('No se pudieron descargar tus datos.');
    }
  };

  const visible = usuario?.mostrar_en_ranking !== false;
  const esAlumno = usuario?.rol === 'estudiante';

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-end sm:items-center justify-center p-0 sm:p-4" role="dialog" aria-modal="true" aria-labelledby="titulo-cuenta" onClick={onCerrar}>
      <div className="bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-3xl p-6 sm:p-8 shadow-xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <h2 id="titulo-cuenta" className="text-lg font-bold text-gray-800">Mi cuenta</h2>
          <button onClick={onCerrar} aria-label="Cerrar" className="text-gray-400 hover:text-gray-600 text-xl leading-none cursor-pointer">✕</button>
        </div>

        <dl className="mt-4 text-sm space-y-1">
          <div><dt className="inline text-gray-400">Nombre: </dt><dd className="inline text-gray-700">{usuario?.nombre}</dd></div>
          <div><dt className="inline text-gray-400">Correo: </dt><dd className="inline text-gray-700 break-all">{usuario?.email}</dd></div>
          {usuario?.cursos?.length > 0 && (
            <div><dt className="inline text-gray-400">Cursos: </dt><dd className="inline text-gray-700">{usuario.cursos.map((c) => c.nombre).join(', ')}</dd></div>
          )}
        </dl>

        {esAlumno && (
          <section className="mt-6 p-4 rounded-2xl bg-gray-50 border border-gray-100">
            <h3 className="font-semibold text-gray-700 text-sm">🏆 Ranking de la clase</h3>
            <p className="text-xs text-gray-500 mt-1">
              Tus compañeros te ven como «{(usuario?.nombre || '').split(' ')[0]} {((usuario?.nombre || '').split(' ')[1] || '').charAt(0)}{(usuario?.nombre || '').split(' ')[1] ? '.' : ''}». Tu progreso personal y tu repaso solo los ves tú.
            </p>
            <label className="flex items-center justify-between gap-3 mt-3 cursor-pointer">
              <span className="text-sm text-gray-700">Aparecer en el ranking</span>
              <input type="checkbox" role="switch" checked={visible} disabled={guardando}
                onChange={(e) => cambiarRanking(e.target.checked)} className="w-5 h-5 accent-orange-500" />
            </label>
          </section>
        )}

        <section className="mt-4 p-4 rounded-2xl bg-gray-50 border border-gray-100">
          <h3 className="font-semibold text-gray-700 text-sm">🔒 Tus datos</h3>
          <button onClick={descargarDatos} className="mt-3 w-full py-2.5 rounded-xl border border-orange-200 text-orange-600 text-sm font-medium hover:bg-orange-50 cursor-pointer">
            ⬇ Descargar mis datos
          </button>
          <p className="text-xs text-gray-500 mt-3 leading-relaxed">
            Para eliminar tu cuenta y todo tu historial, solicítalo a la secretaría de la academia.
            Consulta la <EnlacePrivacidad>política de privacidad</EnlacePrivacidad>.
          </p>
        </section>

        {aviso && <p role="status" className="text-sm text-gray-600 mt-4">{aviso}</p>}
      </div>
    </div>
  );
}
