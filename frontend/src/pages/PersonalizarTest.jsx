import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiFetch } from '../api';
import { PantallaCarga, MensajeError } from '../components/Estado';
import SelectorCurso from '../components/SelectorCurso';
import { agruparPorCurso, resolverGrupo, guardarCursoActivo } from '../utils/cursos';

// "Personaliza tu test": el alumno elige temas, nº de preguntas, tiempo y modo.
const MAX_PREGUNTAS = 200;
const OPCIONES_PREGUNTAS = [10, 20, 30, 50, 100];
const OPCIONES_TIEMPO = [null, 10, 20, 30, 60]; // minutos (null = sin límite)

const MODOS = [
  { id: 'practica', titulo: 'Modo Práctica', icono: '🎯', texto: 'Corrección al momento en cada pregunta.' },
  { id: 'examen', titulo: 'Modo Examen', icono: '📝', texto: 'Sin correcciones hasta entregar; nota al final.' },
];

const chip = (activo) =>
  `px-4 py-2 rounded-xl border-2 text-sm font-medium transition-all cursor-pointer ${activo ? 'border-orange-500 bg-orange-50 text-orange-600' : 'border-gray-100 text-gray-500 hover:border-orange-200'}`;

export default function PersonalizarTest() {
  const navigate = useNavigate();
  const location = useLocation();

  const [temas, setTemas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  const [cursoElegido, setCursoElegido] = useState(location.state?.cursoId ?? null);
  const [seleccion, setSeleccion] = useState([]);           // ids de temas
  const [numPreguntas, setNumPreguntas] = useState(20);
  const [tiempo, setTiempo] = useState(null);              // minutos; null = sin límite
  const [tiempoOtro, setTiempoOtro] = useState('');        // valor libre en minutos
  const [modo, setModo] = useState('practica');
  const [aviso, setAviso] = useState('');

  const cargar = useCallback(() => {
    apiFetch('/api/temas')
      .then((r) => { if (!r.ok) throw new Error('respuesta no OK'); return r.json(); })
      .then((d) => { setTemas(d); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  if (cargando) return <PantallaCarga texto="Cargando tus temas..." />;
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <MensajeError texto="No se pudieron cargar tus temas." onReintentar={() => { setCargando(true); cargar(); }} />
      </div>
    );
  }

  const grupos = agruparPorCurso(temas);
  const grupo = resolverGrupo(grupos, cursoElegido);
  const temasCurso = grupo ? grupo.temas : [];
  const seleccionValida = seleccion.filter((id) => temasCurso.some((t) => t.id === id));
  const disponibles = temasCurso
    .filter((t) => seleccionValida.includes(t.id))
    .reduce((acc, t) => acc + (t.num_preguntas || 0), 0);
  const tope = Math.min(MAX_PREGUNTAS, disponibles || MAX_PREGUNTAS);
  const minutos = tiempo === 'otro' ? Number(tiempoOtro) : tiempo;

  const cambiarCurso = (id) => {
    setCursoElegido(id);
    guardarCursoActivo(id);
    setSeleccion([]); // cada test se hace con temas de un mismo curso
  };

  const alternarTema = (id) =>
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const todosMarcados = temasCurso.length > 0 && temasCurso.every((t) => seleccionValida.includes(t.id));
  const alternarTodos = () => setSeleccion(todosMarcados ? [] : temasCurso.map((t) => t.id));

  const empezar = () => {
    setAviso('');
    if (seleccionValida.length === 0) { setAviso('Elige al menos un tema.'); return; }
    if (disponibles === 0) { setAviso('Los temas elegidos todavía no tienen preguntas.'); return; }
    const n = Number(numPreguntas);
    if (!Number.isInteger(n) || n < 1) { setAviso('Indica un número de preguntas válido.'); return; }
    if (tiempo === 'otro' && (!Number.isFinite(minutos) || minutos <= 0 || minutos > 600)) {
      setAviso('Indica un tiempo entre 1 y 600 minutos, o elige "Sin límite".');
      return;
    }
    navigate('/test', {
      state: {
        cursoId: grupo?.id,
        personalizado: {
          tema_ids: seleccionValida,
          num_preguntas: Math.min(n, tope),
          tiempo_min: minutos || null,
          modo,
        },
      },
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-3xl mx-auto space-y-6">
        <header className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl font-light text-gray-900">
              Personaliza <span className="font-semibold text-orange-500">tu test</span>
            </h1>
            <p className="text-gray-500 text-sm mt-1">Configura un test a tu medida con preguntas al azar de los temas que elijas.</p>
          </div>
          <button onClick={() => navigate('/', { state: { cursoId: grupo?.id } })}
            className="text-sm bg-gray-100 text-gray-600 px-4 py-2 rounded-xl hover:bg-gray-200 transition-colors cursor-pointer">
            ← Volver
          </button>
        </header>

        <SelectorCurso grupos={grupos} activo={grupo?.id} onCambiar={cambiarCurso} />

        {/* 1. TEMAS */}
        <section className="bg-white rounded-3xl p-5 sm:p-6 shadow-sm border border-gray-100">
          <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
            <h2 className="font-semibold text-gray-800"><span className="text-orange-500 mr-1">1.</span> Temas que aparecerán</h2>
            {temasCurso.length > 1 && (
              <button onClick={alternarTodos} className="text-sm text-orange-600 hover:underline cursor-pointer">
                {todosMarcados ? 'Quitar todos' : 'Seleccionar todos'}
              </button>
            )}
          </div>
          {temasCurso.length === 0 ? (
            <p className="text-sm text-gray-400">Todavía no hay temas disponibles en tus cursos.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {temasCurso.map((t) => {
                const marcado = seleccionValida.includes(t.id);
                const vacio = !t.num_preguntas;
                return (
                  <button key={t.id} onClick={() => alternarTema(t.id)}
                    className={`flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all cursor-pointer ${marcado ? 'border-orange-500 bg-orange-50' : 'border-gray-100 hover:border-orange-200'}`}>
                    <span className={`shrink-0 w-5 h-5 rounded border flex items-center justify-center text-xs ${marcado ? 'bg-orange-500 border-orange-500 text-white' : 'border-gray-300'}`}>
                      {marcado ? '✓' : ''}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className={`block text-sm font-medium ${marcado ? 'text-orange-700' : 'text-gray-700'}`}>{t.nombre}</span>
                      <span className={`block text-xs mt-0.5 ${vacio ? 'text-gray-300' : 'text-gray-400'}`}>
                        {vacio ? 'Sin preguntas todavía' : `${t.num_preguntas} preguntas`}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        {/* 2. Nº DE PREGUNTAS */}
        <section className="bg-white rounded-3xl p-5 sm:p-6 shadow-sm border border-gray-100">
          <h2 className="font-semibold text-gray-800 mb-4"><span className="text-orange-500 mr-1">2.</span> Número de preguntas</h2>
          <div className="flex flex-wrap items-center gap-2">
            {OPCIONES_PREGUNTAS.map((n) => (
              <button key={n} onClick={() => setNumPreguntas(n)} className={chip(Number(numPreguntas) === n)}>{n}</button>
            ))}
            <label className="flex items-center gap-2 text-sm text-gray-500 ml-1">
              Otro:
              <input type="number" min={1} max={MAX_PREGUNTAS} value={numPreguntas}
                onChange={(e) => setNumPreguntas(e.target.value === '' ? '' : Math.max(1, Math.min(MAX_PREGUNTAS, Math.floor(Number(e.target.value)))))}
                className="w-24 px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
            </label>
          </div>
          {seleccionValida.length > 0 && (
            <p className="text-xs text-gray-400 mt-3">
              Hay <strong className="text-gray-600">{disponibles}</strong> preguntas en los temas elegidos.
              {Number(numPreguntas) > disponibles && disponibles > 0 && ` Tu test tendrá ${Math.min(disponibles, MAX_PREGUNTAS)}.`}
            </p>
          )}
        </section>

        {/* 3. TIEMPO */}
        <section className="bg-white rounded-3xl p-5 sm:p-6 shadow-sm border border-gray-100">
          <h2 className="font-semibold text-gray-800 mb-4"><span className="text-orange-500 mr-1">3.</span> Tiempo disponible</h2>
          <div className="flex flex-wrap items-center gap-2">
            {OPCIONES_TIEMPO.map((m) => (
              <button key={m ?? 'sin'} onClick={() => setTiempo(m)} className={chip(tiempo === m)}>
                {m === null ? '∞ Sin límite' : `${m} min`}
              </button>
            ))}
            <button onClick={() => setTiempo('otro')} className={chip(tiempo === 'otro')}>Otro</button>
            {tiempo === 'otro' && (
              <label className="flex items-center gap-2 text-sm text-gray-500">
                <input type="number" min={1} max={600} value={tiempoOtro} autoFocus placeholder="45"
                  onChange={(e) => setTiempoOtro(e.target.value)}
                  className="w-24 px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
                minutos
              </label>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-3">
            {tiempo === null ? 'Sin cuenta atrás: verás el tiempo que llevas.' : 'Al agotarse el tiempo, el test se entrega automáticamente.'}
          </p>
        </section>

        {/* 4. MODO */}
        <section className="bg-white rounded-3xl p-5 sm:p-6 shadow-sm border border-gray-100">
          <h2 className="font-semibold text-gray-800 mb-4"><span className="text-orange-500 mr-1">4.</span> Modalidad</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {MODOS.map((m) => (
              <button key={m.id} onClick={() => setModo(m.id)}
                className={`text-left p-4 rounded-xl border-2 transition-all cursor-pointer ${modo === m.id ? 'border-orange-500 bg-orange-50' : 'border-gray-100 hover:border-orange-200'}`}>
                <span className="text-xl mr-2">{m.icono}</span>
                <span className={`font-semibold ${modo === m.id ? 'text-orange-700' : 'text-gray-700'}`}>{m.titulo}</span>
                <span className="block text-xs text-gray-500 mt-1">{m.texto}</span>
              </button>
            ))}
          </div>
        </section>

        {aviso && <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">{aviso}</p>}

        <button onClick={empezar}
          className="w-full py-4 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl font-bold shadow-lg shadow-orange-500/20 transition-all cursor-pointer">
          Empezar test ➔
        </button>
      </div>
    </div>
  );
}
