import React, { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch, apiJson } from '../api';
import { Cargando, MensajeError } from './Estado';

// Pestaña «Alumnos (Access)» del panel: sincroniza alumnos y matrículas con el
// Access de la academia. Dos pasos con el mismo archivo: revisar y aplicar.

const fechaLegible = (f) =>
  f ? new Date(f + (String(f).endsWith('Z') ? '' : 'Z')).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

function Cifra({ valor, texto, tono = 'gris' }) {
  const tonos = {
    gris: 'bg-gray-50 text-gray-800',
    verde: 'bg-green-50 text-green-700',
    rojo: 'bg-red-50 text-red-700',
    ambar: 'bg-amber-50 text-amber-700',
  };
  return (
    <div className={`rounded-2xl p-4 ${tonos[tono]}`}>
      <p className="text-3xl font-bold">{valor}</p>
      <p className="text-xs mt-1 opacity-80">{texto}</p>
    </div>
  );
}

function ListaCambios({ titulo, filas, total, tono }) {
  const [abierta, setAbierta] = useState(false);
  if (!total) return null;
  const color = tono === 'verde' ? 'text-green-700' : 'text-red-700';
  return (
    <div className="border border-gray-100 rounded-xl">
      <button onClick={() => setAbierta(!abierta)} className="w-full flex justify-between items-center px-4 py-3 text-left cursor-pointer">
        <span className={`font-medium ${color}`}>{titulo} ({total})</span>
        <span className="text-gray-400 text-sm">{abierta ? 'Ocultar' : 'Ver detalle'}</span>
      </button>
      {abierta && (
        <div className="border-t border-gray-100 max-h-72 overflow-y-auto divide-y divide-gray-50">
          {filas.map((f, i) => (
            <div key={i} className="px-4 py-2 text-sm flex flex-col sm:flex-row sm:justify-between gap-1">
              <span className="text-gray-800">{f.nombre || f.email} <span className="text-gray-400">· {f.email}</span></span>
              <span className="text-gray-600">{f.curso}{!f.tiene_cuenta && <span className="ml-2 text-xs text-gray-400">(aún no ha entrado)</span>}</span>
            </div>
          ))}
          {total > filas.length && <p className="px-4 py-2 text-xs text-gray-400">… y {total - filas.length} más</p>}
        </div>
      )}
    </div>
  );
}

export default function SincronizacionAccess() {
  const [estado, setEstado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [archivo, setArchivo] = useState(null);
  const [revision, setRevision] = useState(null);   // resultado de la vista previa o de aplicar
  const [trabajando, setTrabajando] = useState('');
  const [aviso, setAviso] = useState('');
  const [verPendientes, setVerPendientes] = useState(false);
  const fileRef = useRef(null);

  const cargarEstado = useCallback(() => {
    apiJson('/api/admin/access/estado')
      .then((d) => { setEstado(d); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargarEstado(); }, [cargarEstado]);

  const enviar = async (aplicar) => {
    if (!archivo) return;
    setAviso('');
    setTrabajando(aplicar ? 'Aplicando cambios…' : 'Revisando el archivo…');
    try {
      const fd = new FormData();
      fd.append('archivo', archivo);
      const res = await apiJson(`/api/admin/access/sincronizar?aplicar=${aplicar}`, { method: 'POST', body: fd });
      setRevision(res);
      if (aplicar) {
        setArchivo(null);
        if (fileRef.current) fileRef.current.value = '';
        cargarEstado();
      }
    } catch (err) {
      setAviso(err.message);
      setRevision(null);
    } finally {
      setTrabajando('');
    }
  };

  const elegirArchivo = (e) => {
    setArchivo(e.target.files?.[0] || null);
    setRevision(null);
    setAviso('');
  };

  const descargarPlantilla = async () => {
    try {
      const r = await apiFetch('/api/admin/access/plantilla');
      if (!r.ok) throw new Error('No se pudo descargar la plantilla.');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = 'plantilla_alumnos_access.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setAviso(err.message); }
  };

  if (cargando) return <Cargando texto="Cargando sincronización..." className="py-12" />;
  if (error) return <MensajeError texto="No se pudo cargar el estado de la sincronización." onReintentar={() => { setCargando(true); cargarEstado(); }} />;

  const u = estado.ultima;

  return (
    <div className="space-y-6">
      {/* Estado actual */}
      <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-gray-800">Alumnos y matrículas del Access</h3>
            <p className="text-sm text-gray-500 mt-1">
              {u ? <>Última sincronización: <strong>{fechaLegible(u.fecha)}</strong>{u.autor ? ` por ${u.autor}` : ''} · {u.archivo}</> : 'Todavía no se ha sincronizado nunca.'}
            </p>
          </div>
          <button onClick={descargarPlantilla} className="shrink-0 text-sm text-orange-600 hover:bg-orange-50 px-3 py-1.5 rounded-lg cursor-pointer">
            ⬇ Descargar plantilla Excel
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Cifra valor={estado.alumnos_en_access} texto="Alumnos en el Access" />
          <Cifra valor={estado.matriculas} texto="Matrículas" />
          <Cifra valor={estado.con_cuenta} texto="Ya han entrado" tono="verde" />
          <Cifra valor={estado.sin_cuenta_total} texto="Aún no han entrado" tono="ambar" />
        </div>
        {estado.sin_cuenta_total > 0 && (
          <div>
            <button onClick={() => setVerPendientes(!verPendientes)} className="text-sm text-gray-500 hover:underline cursor-pointer">
              {verPendientes ? 'Ocultar' : 'Ver'} alumnos que aún no han entrado
            </button>
            {verPendientes && (
              <div className="mt-2 max-h-56 overflow-y-auto border border-gray-100 rounded-xl divide-y divide-gray-50">
                {estado.sin_cuenta.map((p) => (
                  <p key={p.email} className="px-4 py-2 text-sm text-gray-700">{p.nombre || '—'} <span className="text-gray-400">· {p.email}</span></p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Subir y revisar */}
      <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-4">
        <h3 className="font-semibold text-gray-800">Sincronizar con una nueva exportación</h3>
        <ol className="text-sm text-gray-600 list-decimal pl-5 space-y-1">
          <li>Exporta desde el Access un Excel (.xlsx) o CSV con las columnas <strong>Id, DNI, Nombre, Apellidos y Cursos</strong>. El correo de cada alumno se calcula solo, igual que en el Access: nombre en minúsculas, sin espacios ni tildes (ñ → ny) seguido del Id (p. ej. Ana + 6351 → ana6351@academiamega.net). Si el archivo trae una columna <strong>Correo</strong>, se usa esa.</li>
          <li>En <strong>Cursos</strong>, si un alumno tiene varios, sepáralos con punto y coma. Los nombres deben coincidir con los de la plataforma.</li>
          <li>Pulsa <strong>Revisar cambios</strong>: verás qué se va a modificar <em>sin aplicar nada todavía</em>.</li>
          <li>Si todo está bien, pulsa <strong>Aplicar sincronización</strong>.</li>
        </ol>
        <p className="text-xs text-gray-400">
          El Access manda: quien desaparezca de un curso pierde el acceso a ese curso, y quien desaparezca del todo se queda sin cursos
          (conserva su cuenta y su historial). Profesores y administradores no se ven afectados. El DNI no se guarda en la plataforma.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
          <label className="text-sm text-gray-700 cursor-pointer bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-xl text-center">
            {archivo ? `📄 ${archivo.name}` : 'Elegir archivo…'}
            <input ref={fileRef} type="file" accept=".xlsx,.csv" onChange={elegirArchivo} className="hidden" />
          </label>
          <button onClick={() => enviar(false)} disabled={!archivo || !!trabajando}
            className="px-5 py-2 bg-gray-900 hover:bg-black text-white font-medium rounded-xl cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
            Revisar cambios
          </button>
          {trabajando && <span className="text-sm text-gray-500">{trabajando}</span>}
        </div>
        {aviso && <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">{aviso}</p>}
      </div>

      {/* Resultado de la revisión */}
      {revision && (
        <div className={`border rounded-2xl p-5 shadow-sm space-y-4 ${revision.aplicado ? 'bg-green-50/40 border-green-200' : 'bg-white border-gray-100'}`}>
          <h3 className="font-semibold text-gray-800">
            {revision.aplicado ? '✓ Sincronización aplicada' : 'Vista previa: así quedaría tras sincronizar'}
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Cifra valor={revision.alumnos} texto={`Alumnos en el archivo (${revision.sin_cuenta} aún sin entrar)`} />
            <Cifra valor={revision.altas_total} texto="Altas de curso" tono="verde" />
            <Cifra valor={revision.bajas_total} texto="Bajas de curso" tono="rojo" />
            <Cifra valor={revision.errores_total} texto="Filas con avisos" tono="ambar" />
          </div>

          <ListaCambios titulo="Altas" filas={revision.altas} total={revision.altas_total} tono="verde" />
          <ListaCambios titulo="Bajas" filas={revision.bajas} total={revision.bajas_total} tono="rojo" />

          {revision.sin_cursos.length > 0 && (
            <p className="text-sm text-red-700 bg-red-50 rounded-xl px-4 py-3">
              Se quedarán <strong>sin ningún curso</strong> ({revision.sin_cursos.length}): {revision.sin_cursos.slice(0, 8).join(', ')}{revision.sin_cursos.length > 8 ? '…' : ''}
            </p>
          )}

          {revision.errores_total > 0 && (
            <div className="bg-amber-50 rounded-xl px-4 py-3 space-y-1">
              <p className="text-sm font-medium text-amber-800">Avisos ({revision.errores_total}). Estas filas no se aplican; el resto sí:</p>
              <ul className="text-sm text-amber-800 list-disc pl-5 max-h-48 overflow-y-auto">
                {revision.errores.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
              <p className="text-xs text-amber-700">Un alumno con alguna fila errónea conserva sus cursos anteriores además de los válidos.</p>
            </div>
          )}

          {!revision.aplicado && (
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
              <button onClick={() => setRevision(null)} className="px-5 py-2 rounded-xl bg-gray-100 text-gray-600 hover:bg-gray-200 cursor-pointer">Cancelar</button>
              <button onClick={() => enviar(true)} disabled={!!trabajando}
                className="px-5 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-medium cursor-pointer disabled:opacity-50">
                Aplicar sincronización
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
