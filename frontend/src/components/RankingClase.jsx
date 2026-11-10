import React, { useEffect, useState } from 'react';
import { apiJson } from '../api';
import { Cargando, MensajeError } from './Estado';

// Ranking del curso activo: top 5 y, si el alumno no está entre ellos, su puesto.
// Puntos = suma del mejor % de aciertos de cada test del banco (máx. 100 por test).
export default function RankingClase({ cursoId, onAbrirCuenta }) {
  const valido = cursoId !== null && cursoId !== undefined && cursoId !== '' && Number.isInteger(Number(cursoId));
  // Resultado de la última carga: { clave, datos, error }. "Cargando" = aún no hay
  // resultado para el curso (y nº de intento) actual.
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState({ clave: null, datos: null, error: '' });
  const clave = `${cursoId}#${intento}`;

  useEffect(() => {
    if (!valido) return undefined;
    let vigente = true;
    apiJson(`/api/ranking/clase?curso_id=${cursoId}`)
      .then((d) => { if (vigente) setResultado({ clave, datos: d, error: '' }); })
      .catch((e) => { if (vigente) setResultado({ clave, datos: null, error: e.message || 'No se pudo cargar el ranking.' }); });
    return () => { vigente = false; };
  }, [cursoId, valido, clave]);

  if (!valido) return null;

  const cargando = resultado.clave !== clave;
  const { datos, error } = cargando ? { datos: null, error: '' } : resultado;
  const cargar = () => setIntento((n) => n + 1);

  const yoFuera = datos?.yo && !datos.lideres.some((l) => l.soy_yo);

  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">🏆 Ranking de la clase</h3>
      {datos?.curso && <p className="text-xs text-gray-400 mt-0.5 mb-4">{datos.curso}</p>}

      {cargando && <Cargando texto="Cargando ranking..." className="py-6" />}
      {!cargando && error && <MensajeError texto={error} onReintentar={cargar} />}

      {!cargando && !error && datos && (
        <>
          {datos.lideres.length === 0 ? (
            <p className="text-gray-400 text-sm italic text-center py-4">
              Aún nadie ha hecho tests del banco de este curso. ¡Sé el primero!
            </p>
          ) : (
            <ol className="space-y-2">
              {datos.lideres.map((l) => <Fila key={`${l.posicion}-${l.nombre}`} fila={l} />)}
              {yoFuera && (
                <>
                  <li className="text-center text-gray-300 text-xs leading-none" aria-hidden="true">···</li>
                  <Fila fila={datos.yo} />
                </>
              )}
            </ol>
          )}
          {datos.oculto ? (
            <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 mt-3">
              Estás oculto: tus compañeros no te ven en el ranking.
              {onAbrirCuenta && <button onClick={onAbrirCuenta} className="ml-1 text-orange-600 hover:underline cursor-pointer">Cambiar</button>}
            </p>
          ) : !datos.yo && datos.lideres.length > 0 && (
            <p className="text-xs text-gray-400 mt-3">Haz un test del banco para entrar en el ranking.</p>
          )}
          <p className="text-[11px] text-gray-400 mt-4 leading-snug">
            Puntos: suma del mejor % de aciertos de cada test del banco (máx. 100 por test). Los tests personalizados no cuentan.
            Se actualiza cada minuto. Tus compañeros te ven con tu nombre y la inicial del apellido.
          </p>
        </>
      )}
    </div>
  );
}

function Fila({ fila }) {
  const medalla = fila.posicion === 1 ? 'bg-yellow-400 text-white' : fila.posicion === 2 ? 'bg-gray-300 text-white' : fila.posicion === 3 ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-500';
  return (
    <li className={`flex justify-between items-center gap-3 p-3 rounded-xl ${fila.soy_yo ? 'bg-orange-50 border border-orange-200' : 'bg-gray-50'}`}>
      <div className="flex items-center gap-3 min-w-0">
        <span className={`shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-xs font-bold ${medalla}`}>{fila.posicion}</span>
        <span className="text-gray-700 font-medium truncate">{fila.soy_yo ? `Tú (${fila.nombre})` : fila.nombre}</span>
      </div>
      <div className="text-right shrink-0">
        <div className="text-orange-500 font-bold leading-tight">{fila.puntos} pts</div>
        <div className="text-[11px] text-gray-400">{fila.tests} test{fila.tests === 1 ? '' : 's'}</div>
      </div>
    </li>
  );
}
