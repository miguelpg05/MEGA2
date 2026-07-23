import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../api';

// Marco de la ficha (a nivel de módulo para no recrearlo en cada render)
function Marco({ children }) {
  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xl">📈</span>
        <h3 className="text-lg font-semibold text-gray-800">Tu evolución</h3>
      </div>
      {children}
    </div>
  );
}

// Gráfico de líneas SVG hecho a mano: sin librerías, responsive (viewBox) y
// dinámico (se adapta a cualquier número de intentos). Muestra el % de aciertos
// de cada intento en orden cronológico.
export default function GraficoEvolucion() {
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  const cargar = useCallback(() => {
    apiFetch('/api/test/evolucion')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('no OK'))))
      .then((d) => { setDatos(Array.isArray(d) ? d : []); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  if (cargando) {
    return <Marco><p className="text-sm text-gray-400 py-6 text-center animate-pulse">Cargando tu evolución…</p></Marco>;
  }
  if (error) {
    return (
      <Marco>
        <div className="text-center py-4">
          <p className="text-sm text-gray-500">No se pudo cargar la gráfica.</p>
          <button onClick={() => { setCargando(true); setError(false); cargar(); }} className="mt-2 text-sm text-orange-600 hover:underline cursor-pointer">Reintentar</button>
        </div>
      </Marco>
    );
  }
  if (datos.length === 0) {
    return (
      <Marco>
        <div className="text-center py-6">
          <div className="text-3xl mb-2 opacity-60">📊</div>
          <p className="text-sm text-gray-500">Aún no has hecho ningún test.</p>
          <p className="text-xs text-gray-400 mt-1">Haz uno y aquí verás tu evolución intento a intento.</p>
        </div>
      </Marco>
    );
  }

  // --- Geometría del gráfico ---
  const W = 320, H = 170;
  const P = { top: 14, right: 12, bottom: 26, left: 30 };
  const innerW = W - P.left - P.right;
  const innerH = H - P.top - P.bottom;
  const n = datos.length;

  const x = (i) => (n <= 1 ? P.left + innerW / 2 : P.left + (i / (n - 1)) * innerW);
  const y = (pct) => P.top + (1 - Math.max(0, Math.min(100, pct)) / 100) * innerH;

  const puntos = datos.map((d, i) => ({ ...d, cx: x(i), cy: y(d.porcentaje) }));
  const linePath = puntos.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.cx.toFixed(1)} ${p.cy.toFixed(1)}`).join(' ');
  const baseY = P.top + innerH;
  const areaPath = `${linePath} L ${puntos[n - 1].cx.toFixed(1)} ${baseY} L ${puntos[0].cx.toFixed(1)} ${baseY} Z`;

  // Los puntos se dibujan mientras no sean demasiados (dinámico); el último siempre.
  const mostrarPuntos = n <= 24;

  const ultimo = datos[n - 1].porcentaje;
  const media = Math.round(datos.reduce((s, d) => s + d.porcentaje, 0) / n);
  const yAprobado = y(80);

  return (
    <Marco>
      <div className="flex items-end justify-between mb-3">
        <div>
          <p className="text-3xl font-bold text-gray-800 leading-none">{ultimo}%</p>
          <p className="text-xs text-gray-400 mt-1">último intento</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-gray-600">{media}%</p>
          <p className="text-xs text-gray-400">media · {n} test{n !== 1 ? 's' : ''}</p>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Gráfica de evolución de resultados">
        <defs>
          <linearGradient id="areaEvolucion" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f97316" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Rejilla horizontal + etiquetas del eje Y */}
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line x1={P.left} y1={y(v)} x2={W - P.right} y2={y(v)} stroke="#f3f4f6" strokeWidth="1" />
            <text x={P.left - 6} y={y(v) + 3} textAnchor="end" fontSize="9" fill="#9ca3af">{v}</text>
          </g>
        ))}

        {/* Línea de aprobado (80%) */}
        <line x1={P.left} y1={yAprobado} x2={W - P.right} y2={yAprobado} stroke="#22c55e" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
        <text x={W - P.right} y={yAprobado - 3} textAnchor="end" fontSize="8" fill="#22c55e">aprobado 80%</text>

        {/* Área + línea */}
        <path d={areaPath} fill="url(#areaEvolucion)" />
        <path d={linePath} fill="none" stroke="#f97316" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

        {/* Puntos */}
        {puntos.map((p, i) => {
          const esUltimo = i === n - 1;
          if (!mostrarPuntos && !esUltimo) return null;
          return (
            <circle key={i} cx={p.cx} cy={p.cy} r={esUltimo ? 4 : 2.5}
              fill={p.porcentaje >= 80 ? '#22c55e' : '#f97316'} stroke="#fff" strokeWidth="1.5">
              <title>{`Intento ${p.intento}${p.numero_test ? ` · Test ${p.numero_test}` : ''}: ${p.aciertos}/${p.total} (${p.porcentaje}%)`}</title>
            </circle>
          );
        })}
      </svg>
      <p className="text-center text-[11px] text-gray-400 mt-1">Cada punto es un test realizado (pasa el ratón para ver el detalle).</p>
    </Marco>
  );
}
