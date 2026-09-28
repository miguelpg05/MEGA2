import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiFetch } from '../api';
import { Cargando, MensajeError } from '../components/Estado';

// ------------------------------------------------------------------
// Test del alumno. Todas las preguntas se muestran en una lista con
// scroll vertical continuo y hay dos modalidades:
//   · Modo Práctica: corrige cada pregunta al marcarla (explicación y
//     flashcard al momento), como siempre.
//   · Modo Examen: se responde todo de corrido, sin ver si se acierta;
//     al entregar se muestran la nota y la corrección completa.
//
// Origen de las preguntas (location.state):
//   · Banco de tests: { temaId, temaNombre, testPlantillaId, testNombre }
//   · Personaliza tu test: { personalizado: { tema_ids, num_preguntas,
//       tiempo_min (null = sin límite), modo } }
// ------------------------------------------------------------------

const NIVEL_OBJETIVO = 80;
const TIEMPO_BANCO_SEG = 120; // cronómetro orientativo del banco de tests (comportamiento actual)
const LETRAS = ['A', 'B', 'C', 'D'];

const MODOS = {
  practica: {
    titulo: 'Modo Práctica',
    icono: '🎯',
    descripcion: 'Se corrige cada pregunta en cuanto la respondes, con su explicación y la opción de crear una flashcard.',
  },
  examen: {
    titulo: 'Modo Examen',
    icono: '📝',
    descripcion: 'Responde todas las preguntas de corrido. Verás las correctas, las incorrectas y tu nota solo al entregar.',
  },
};

const formatearTiempo = (segundosTotales) => {
  const s = Math.max(0, segundosTotales);
  const minutos = Math.floor(s / 60);
  const segundos = s % 60;
  return `${minutos}:${segundos < 10 ? '0' : ''}${segundos}`;
};

// Respuestas correctas de una pregunta (siempre como lista)
const correctasDe = (pregunta) =>
  pregunta.respuestasCorrectas && pregunta.respuestasCorrectas.length
    ? pregunta.respuestasCorrectas
    : [pregunta.respuestaCorrecta];

// Correcta solo si el conjunto marcado coincide EXACTAMENTE con el correcto
const esAcierto = (pregunta, seleccion) => {
  const correctas = correctasDe(pregunta);
  return seleccion.length === correctas.length && correctas.every((c) => seleccion.includes(c));
};

export default function Test() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaIdActual = location.state?.temaId || null;
  const temaNombre = location.state?.temaNombre || '';
  const testPlantillaId = location.state?.testPlantillaId || null;
  const testNombre = location.state?.testNombre || '';
  const config = location.state?.personalizado || null; // test configurado por el alumno
  const esPersonalizado = Boolean(config);

  // Tiempo: los tests personalizados usan el que eligió el alumno (o sin límite)
  // y al agotarse se entregan solos. El banco mantiene su cronómetro orientativo.
  const limiteSeg = esPersonalizado
    ? (config.tiempo_min ? Math.round(config.tiempo_min * 60) : null)
    : TIEMPO_BANCO_SEG;
  const tiempoObligatorio = esPersonalizado && limiteSeg !== null;

  // Datos
  const [preguntas, setPreguntas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  // Flujo: null = eligiendo modo
  const [modo, setModo] = useState(config?.modo || null);
  const [fase, setFase] = useState('jugando'); // 'jugando' | 'resultado'

  // Respuestas por pregunta: { [id]: { seleccion: [], corregida: bool, correcta: bool } }
  const [respuestas, setRespuestas] = useState({});
  const [confirmarEntrega, setConfirmarEntrega] = useState(false);
  const [resultado, setResultado] = useState(null); // { aciertos, fallos, enBlanco, total, porcentaje, nota }
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const guardadoRef = useRef(false);

  // Tiempo
  const [segundos, setSegundos] = useState(limiteSeg ?? 0); // restante (o transcurrido si no hay límite)
  const [tiempoAgotado, setTiempoAgotado] = useState(false);
  const inicioRef = useRef(null);

  // Flashcard (Modo Práctica)
  const [flashcard, setFlashcard] = useState(null); // pregunta mostrada
  const [flashcardVolteada, setFlashcardVolteada] = useState(false);

  const volver = useCallback(() => {
    if (esPersonalizado) navigate('/', { state: { cursoId: location.state?.cursoId } });
    else navigate('/listado-tests', { state: { temaId: temaIdActual, temaNombre } });
  }, [esPersonalizado, navigate, location.state, temaIdActual, temaNombre]);

  // ---------- Carga de preguntas ----------
  const cargarPreguntas = useCallback(() => {
    const peticion = esPersonalizado
      ? apiFetch('/api/test/personalizado', {
          method: 'POST',
          body: JSON.stringify({ tema_ids: config.tema_ids, num_preguntas: config.num_preguntas }),
        })
      : apiFetch(`/api/test/generar?test_plantilla_id=${testPlantillaId}`);

    peticion
      .then(async (res) => {
        const datos = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(datos.detail || 'No se pudieron cargar las preguntas del test.');
        return esPersonalizado ? datos.preguntas : datos;
      })
      .then((lista) => {
        setPreguntas(lista || []);
        setError('');
        setCargando(false);
      })
      .catch((err) => {
        console.error('Error al cargar las preguntas:', err);
        setError(err.message || 'No se pudieron cargar las preguntas del test. Revisa tu conexión.');
        setCargando(false);
      });
  }, [esPersonalizado, config, testPlantillaId]);

  useEffect(() => {
    // Si entran directo a la ruta sin seleccionar un test, los devolvemos al inicio
    if (!testPlantillaId && !esPersonalizado) {
      navigate('/');
      return;
    }
    cargarPreguntas();
  }, [testPlantillaId, esPersonalizado, navigate, cargarPreguntas]);

  const reintentar = () => {
    setCargando(true);
    setError('');
    cargarPreguntas();
  };

  // ---------- Envíos al backend ----------
  const registrarFallo = (preguntaId) =>
    apiFetch('/api/test/fallo', { method: 'POST', body: JSON.stringify({ pregunta_id: preguntaId }) })
      .catch((e) => console.error('Error al registrar fallo:', e));

  const guardarResultados = async (res, historial) => {
    if (guardadoRef.current) return;
    guardadoRef.current = true;
    setGuardando(true);
    try {
      await apiFetch('/api/test/registrar-intento', {
        method: 'POST',
        body: JSON.stringify({
          test_plantilla_id: esPersonalizado ? null : testPlantillaId,
          fallos: res.fallos + res.enBlanco,
          total_preguntas: res.total,
          modo,
          personalizado: esPersonalizado,
        }),
      });
      await apiFetch('/api/progreso/guardar-resultados', {
        method: 'POST',
        body: JSON.stringify({ respuestas: historial }),
      });
      await apiFetch('/api/ranking/guardar', {
        method: 'POST',
        body: JSON.stringify({ puntos: res.aciertos }),
      });
      setGuardado(true);
    } catch (e) {
      console.error('Error al guardar los resultados:', e);
      guardadoRef.current = false; // permite reintentar
    } finally {
      setGuardando(false);
    }
  };

  // ---------- Cálculo del resultado ----------
  const calcularResultado = useCallback((resp) => {
    let aciertos = 0, fallos = 0, enBlanco = 0;
    const historial = [];
    preguntas.forEach((p) => {
      const r = resp[p.id];
      const respondida = r && (modo === 'practica' ? r.corregida : r.seleccion.length > 0);
      if (!respondida) {
        enBlanco += 1;
        historial.push({ pregunta_id: p.id, es_correcta: false });
        return;
      }
      const ok = esAcierto(p, r.seleccion);
      if (ok) aciertos += 1; else fallos += 1;
      historial.push({ pregunta_id: p.id, es_correcta: ok });
    });
    const total = preguntas.length;
    const porcentaje = total ? Math.round((aciertos / total) * 100) : 0;
    const nota = total ? Math.round((aciertos / total) * 100) / 10 : 0; // sobre 10, 1 decimal
    return { res: { aciertos, fallos, enBlanco, total, porcentaje, nota }, historial };
  }, [preguntas, modo]);

  // Entrega (Modo Examen) o fin de tiempo: corrige todo y guarda automáticamente
  const respuestasRef = useRef(respuestas);
  useEffect(() => { respuestasRef.current = respuestas; }, [respuestas]);

  const finalizar = useCallback((motivo = 'entrega') => {
    const resp = respuestasRef.current;
    const { res, historial } = calcularResultado(resp);

    // Fallos pendientes de registrar para el mazo de repaso. En Práctica ya se
    // registraron al corregir; aquí solo faltan las no corregidas.
    preguntas.forEach((p) => {
      const r = resp[p.id];
      const yaRegistrada = modo === 'practica' && r?.corregida;
      const ok = r && r.seleccion.length > 0 && esAcierto(p, r.seleccion) && (modo === 'examen' || r.corregida);
      if (!yaRegistrada && !ok) registrarFallo(p.id);
    });

    if (motivo === 'tiempo') setTiempoAgotado(true);
    setConfirmarEntrega(false);
    setResultado(res);
    setFase('resultado');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // En Examen (o si se agota el tiempo) guardamos ya: así la nota no se pierde
    // aunque el alumno cierre la revisión. En Práctica se guarda con el botón final.
    if (modo === 'examen' || motivo === 'tiempo') guardarResultados(res, historial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calcularResultado, preguntas, modo]);

  const finalizarRef = useRef(finalizar);
  useEffect(() => { finalizarRef.current = finalizar; }, [finalizar]);

  // ---------- Cronómetro ----------
  const jugando = !cargando && !error && modo && fase === 'jugando' && preguntas.length > 0;
  useEffect(() => {
    if (!jugando) return;
    if (inicioRef.current === null) inicioRef.current = Date.now();
    const id = setInterval(() => {
      const transcurridos = Math.floor((Date.now() - inicioRef.current) / 1000);
      if (limiteSeg === null) {
        setSegundos(transcurridos);
        return;
      }
      const restantes = Math.max(0, limiteSeg - transcurridos);
      setSegundos(restantes);
      if (restantes === 0 && tiempoObligatorio) {
        clearInterval(id);
        finalizarRef.current('tiempo');
      }
    }, 1000);
    return () => clearInterval(id);
  }, [jugando, limiteSeg, tiempoObligatorio]);

  // ---------- Interacción con las preguntas ----------
  const corregir = (pregunta, seleccion) => {
    const ok = esAcierto(pregunta, seleccion);
    setRespuestas((prev) => ({ ...prev, [pregunta.id]: { seleccion, corregida: true, correcta: ok } }));
    if (!ok) registrarFallo(pregunta.id);
  };

  const marcarOpcion = (pregunta, opcion) => {
    const actual = respuestas[pregunta.id];
    if (actual?.corregida) return; // en Práctica, una vez corregida no se cambia

    if (!pregunta.multiple) {
      if (modo === 'practica') {
        corregir(pregunta, [opcion]); // corrección al marcar
      } else {
        setRespuestas((prev) => ({ ...prev, [pregunta.id]: { seleccion: [opcion], corregida: false } }));
      }
      return;
    }
    // Varias correctas: alternar la opción (en Práctica se corrige con "Comprobar")
    const previa = actual?.seleccion || [];
    const seleccion = previa.includes(opcion) ? previa.filter((o) => o !== opcion) : [...previa, opcion];
    setRespuestas((prev) => ({ ...prev, [pregunta.id]: { seleccion, corregida: false } }));
  };

  const irAPregunta = (indice) => {
    document.getElementById(`pregunta-${indice}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const reiniciar = () => {
    setRespuestas({});
    setResultado(null);
    setFase('jugando');
    setTiempoAgotado(false);
    setGuardado(false);
    guardadoRef.current = false;
    inicioRef.current = null;
    setSegundos(limiteSeg ?? 0);
    setModo(config?.modo || null);
    setCargando(true);
    cargarPreguntas(); // nuevo orden aleatorio
    window.scrollTo({ top: 0 });
  };

  // ================== PANTALLAS ==================
  const tituloTest = esPersonalizado ? 'Test personalizado' : `Test ${testNombre}`.trim();

  if (cargando) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
        <Cargando texto="Preparando test inteligente..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center font-sans p-4">
        <MensajeError texto={error} onReintentar={reintentar} />
        <button onClick={volver} className="text-sm text-gray-500 hover:underline cursor-pointer">← Volver</button>
      </div>
    );
  }

  if (preguntas.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center font-sans gap-4 p-4">
        <div className="text-2xl">🚧</div>
        <div className="text-gray-600 font-medium">Aún no hay preguntas para este test.</div>
        <button onClick={volver} className="px-6 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors cursor-pointer">Volver</button>
      </div>
    );
  }

  // ---------- Elección de modalidad ----------
  if (!modo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 sm:p-6 font-sans">
        <div className="max-w-2xl w-full">
          <button onClick={volver} className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer font-medium mb-6">← Volver</button>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">{tituloTest}</h1>
          <p className="text-gray-500 mt-1 mb-8">
            {temaNombre && <>{temaNombre} · </>}{preguntas.length} preguntas. ¿Cómo quieres hacerlo?
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(MODOS).map(([clave, m]) => (
              <button
                key={clave}
                onClick={() => setModo(clave)}
                className="text-left bg-white border-2 border-gray-100 hover:border-orange-500 rounded-3xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer group"
              >
                <div className="text-3xl mb-3">{m.icono}</div>
                <h2 className="text-lg font-bold text-gray-800 group-hover:text-orange-600">{m.titulo}</h2>
                <p className="text-sm text-gray-500 mt-2 leading-relaxed">{m.descripcion}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ---------- Resultado: Modo Práctica (igual que siempre) ----------
  if (fase === 'resultado' && modo === 'practica' && !tiempoAgotado) {
    const superado = resultado.porcentaje >= NIVEL_OBJETIVO;
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-xl text-center border border-gray-100">
          <div className="text-6xl mb-4">{superado ? '🎉' : '📚'}</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">{superado ? '¡Nivel Superado!' : 'Sigue practicando'}</h2>
          <div className="my-8">
            <div className="text-5xl font-black text-orange-500 mb-2">{resultado.porcentaje}%</div>
            <p className="text-gray-500">Tu nivel en este test</p>
          </div>
          <div className="bg-gray-50 rounded-2xl p-4 mb-8">
            <p className="text-sm text-gray-600">Nivel objetivo: <span className="font-bold">{NIVEL_OBJETIVO}%</span></p>
            <div className="w-full h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
              <div className={`h-full transition-all duration-1000 ${superado ? 'bg-green-500' : 'bg-orange-400'}`} style={{ width: `${resultado.porcentaje}%` }}></div>
            </div>
          </div>
          <button
            disabled={guardando}
            onClick={async () => {
              const { res, historial } = calcularResultado(respuestasRef.current);
              await guardarResultados(res, historial);
              volver();
            }}
            className="w-full py-4 bg-gray-900 text-white rounded-2xl font-semibold hover:bg-gray-800 transition-colors cursor-pointer disabled:opacity-60"
          >
            {guardando ? 'Guardando…' : 'Finalizar y guardar nota'}
          </button>
        </div>
      </div>
    );
  }

  // ---------- Resultado: Modo Examen (o tiempo agotado) con revisión ----------
  if (fase === 'resultado') {
    const aprobado = resultado.nota >= 5;
    const superado = resultado.porcentaje >= NIVEL_OBJETIVO;
    return (
      <div className="min-h-screen bg-gray-50 py-8 sm:py-12 px-4 font-sans">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100 text-center">
            {tiempoAgotado && (
              <p className="mb-4 inline-block text-sm font-medium bg-red-50 text-red-600 px-4 py-1.5 rounded-full">⏱ Se agotó el tiempo: el test se entregó automáticamente</p>
            )}
            <p className="text-sm text-gray-400 uppercase tracking-wide font-semibold">{tituloTest} · {MODOS[modo].titulo}</p>
            <div className="text-6xl sm:text-7xl font-black mt-4 text-orange-500">
              {resultado.nota.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              <span className="text-2xl sm:text-3xl text-gray-300 font-bold"> / 10</span>
            </div>
            <p className={`mt-2 font-semibold ${aprobado ? 'text-green-600' : 'text-red-600'}`}>
              {superado ? '¡Nivel superado! 🎉' : aprobado ? 'Aprobado' : 'Suspenso'} · {resultado.porcentaje}% de aciertos
            </p>
            <div className="grid grid-cols-3 gap-3 mt-6">
              <div className="bg-green-50 rounded-2xl p-3"><div className="text-2xl font-bold text-green-700">{resultado.aciertos}</div><div className="text-xs text-green-700">Correctas</div></div>
              <div className="bg-red-50 rounded-2xl p-3"><div className="text-2xl font-bold text-red-600">{resultado.fallos}</div><div className="text-xs text-red-600">Incorrectas</div></div>
              <div className="bg-gray-100 rounded-2xl p-3"><div className="text-2xl font-bold text-gray-600">{resultado.enBlanco}</div><div className="text-xs text-gray-500">En blanco</div></div>
            </div>
            <p className="text-xs text-gray-400 mt-4">
              {guardando ? 'Guardando tu nota…' : guardado ? '✓ Nota guardada en tu historial. Los fallos se han añadido a tu mazo de repaso.' : 'No se pudo guardar la nota.'}
              {!guardando && !guardado && (
                <button onClick={() => { const { res, historial } = calcularResultado(respuestasRef.current); guardarResultados(res, historial); }} className="ml-2 text-orange-600 hover:underline cursor-pointer">Reintentar</button>
              )}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mt-6">
              <button onClick={volver} className="flex-1 py-3 bg-gray-900 text-white rounded-2xl font-semibold hover:bg-gray-800 transition-colors cursor-pointer">
                {esPersonalizado ? 'Volver al inicio' : 'Volver al banco de tests'}
              </button>
              <button onClick={reiniciar} className="flex-1 py-3 bg-white border border-gray-200 text-gray-700 rounded-2xl font-semibold hover:border-orange-500 hover:text-orange-600 transition-colors cursor-pointer">
                Repetir test
              </button>
            </div>
          </div>

          <h2 className="text-lg font-bold text-gray-800 px-1">Corrección</h2>
          {preguntas.map((p, i) => {
            const sel = respuestas[p.id]?.seleccion || [];
            const enBlanco = sel.length === 0;
            const ok = !enBlanco && esAcierto(p, sel);
            const correctas = correctasDe(p);
            return (
              <div key={p.id} className={`bg-white rounded-3xl border-2 p-5 sm:p-6 ${ok ? 'border-green-200' : enBlanco ? 'border-gray-200' : 'border-red-200'}`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h3 className="font-medium text-gray-800 leading-snug"><span className="text-gray-400 mr-2">{i + 1}.</span>{p.pregunta}</h3>
                  <span className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${ok ? 'bg-green-100 text-green-700' : enBlanco ? 'bg-gray-100 text-gray-500' : 'bg-red-100 text-red-600'}`}>
                    {ok ? '✓ Correcta' : enBlanco ? 'En blanco' : '✗ Incorrecta'}
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {p.opciones.map((opcion, idx) => {
                    const esCorrecta = correctas.includes(opcion);
                    const marcada = sel.includes(opcion);
                    let estilo = 'border-gray-100 text-gray-400';
                    if (esCorrecta) estilo = 'border-green-500 bg-green-50 text-green-800 font-medium';
                    else if (marcada) estilo = 'border-red-400 bg-red-50 text-red-700';
                    return (
                      <div key={idx} className={`p-3 rounded-xl border-2 flex items-center gap-3 text-sm ${estilo}`}>
                        <span className="w-5 font-semibold opacity-60">{LETRAS[idx]}.</span>
                        <span className="flex-1">{opcion}</span>
                        {marcada && <span className="text-xs font-semibold opacity-80">Tu respuesta</span>}
                      </div>
                    );
                  })}
                </div>
                <p className="text-sm text-gray-600 mt-3 bg-gray-50 rounded-xl p-3">💡 {p.explicacion}</p>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ---------- Test en curso: lista con scroll vertical ----------
  const respondidas = preguntas.filter((p) => {
    const r = respuestas[p.id];
    return r && (modo === 'practica' ? r.corregida : r.seleccion.length > 0);
  }).length;
  const pendientes = preguntas.length - respondidas;
  const tiempoCritico = limiteSeg !== null && segundos < 30;

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Cabecera fija: salir, modo, tiempo, progreso y mapa de preguntas */}
      <div className="sticky top-0 z-30 bg-gray-50/95 backdrop-blur border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <button onClick={volver} className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer font-medium">✕ Salir</button>
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-orange-100 text-orange-700">{MODOS[modo].icono} {MODOS[modo].titulo}</span>
              <span className={`text-sm font-medium px-3 py-1 rounded-full shadow-sm border transition-colors ${tiempoCritico ? 'bg-red-50 text-red-600 border-red-200 animate-pulse' : 'bg-white text-gray-600 border-gray-200'}`}>
                ⏱ {formatearTiempo(segundos)}{limiteSeg === null && <span className="text-gray-400"> · sin límite</span>}
              </span>
              <span className="text-sm font-medium text-gray-500 bg-white px-3 py-1 rounded-full shadow-sm border border-gray-100">
                {respondidas}/{preguntas.length}
              </span>
            </div>
          </div>
          <div className="w-full h-1.5 bg-gray-200 rounded-full mt-3 overflow-hidden">
            <div className="h-full bg-orange-500 transition-all duration-300" style={{ width: `${(respondidas / preguntas.length) * 100}%` }}></div>
          </div>
          <div className="flex gap-1.5 mt-3 overflow-x-auto pb-1" aria-label="Ir a la pregunta">
            {preguntas.map((p, i) => {
              const r = respuestas[p.id];
              let color = 'bg-white text-gray-500 border-gray-200';
              if (modo === 'practica' && r?.corregida) color = r.correcta ? 'bg-green-500 text-white border-green-500' : 'bg-red-500 text-white border-red-500';
              else if (r?.seleccion?.length) color = 'bg-orange-500 text-white border-orange-500';
              return (
                <button key={p.id} onClick={() => irAPregunta(i)} title={`Pregunta ${i + 1}`}
                  className={`shrink-0 w-7 h-7 rounded-lg border text-xs font-semibold cursor-pointer ${color}`}>
                  {i + 1}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6 sm:py-8 space-y-5">
        <div className="px-1">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">{tituloTest}</h1>
          <p className="text-sm text-gray-500 mt-1">{MODOS[modo].descripcion}</p>
        </div>

        {preguntas.map((p, i) => {
          const r = respuestas[p.id];
          const seleccion = r?.seleccion || [];
          const corregida = modo === 'practica' && r?.corregida;
          const correctas = correctasDe(p);
          return (
            <section key={p.id} id={`pregunta-${i}`} className="scroll-mt-40 bg-white rounded-3xl shadow-sm border border-gray-100 p-5 sm:p-8">
              <p className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-2">Pregunta {i + 1} de {preguntas.length}</p>
              <h2 className="text-lg sm:text-xl font-medium text-gray-800 leading-snug">{p.pregunta}</h2>
              {p.multiple && (
                <p className="text-sm text-orange-600 font-medium mt-2">✓ Puede haber más de una respuesta correcta. Selecciona todas.</p>
              )}

              <div className="flex flex-col gap-3 mt-5">
                {p.opciones.map((opcion, index) => {
                  const esCorrecta = correctas.includes(opcion);
                  const estaSeleccionada = seleccion.includes(opcion);
                  let estilos = 'border-gray-200 hover:border-orange-500 hover:bg-orange-50 text-gray-700';
                  if (corregida) {
                    if (esCorrecta) estilos = 'border-green-500 bg-green-50 text-green-800 font-medium';
                    else if (estaSeleccionada) estilos = 'border-red-400 bg-red-50 text-red-700';
                    else estilos = 'border-gray-100 text-gray-400 opacity-60';
                  } else if (estaSeleccionada) {
                    estilos = 'border-orange-500 bg-orange-50 text-orange-700 font-medium ring-1 ring-orange-500';
                  }
                  return (
                    <button key={index} onClick={() => marcarOpcion(p, opcion)} disabled={corregida}
                      className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 flex items-center gap-3 ${corregida ? 'cursor-default' : 'cursor-pointer'} ${estilos}`}>
                      {p.multiple && (
                        <span className={`shrink-0 w-5 h-5 rounded border flex items-center justify-center text-xs ${estaSeleccionada ? 'bg-orange-500 border-orange-500 text-white' : 'border-gray-300'}`}>
                          {estaSeleccionada ? '✓' : ''}
                        </span>
                      )}
                      <span className="inline-block w-6 font-semibold opacity-60">{LETRAS[index]}.</span>
                      <span className="flex-1">{opcion}</span>
                    </button>
                  );
                })}
              </div>

              {/* Práctica + varias correctas: comprobar manualmente */}
              {modo === 'practica' && p.multiple && !corregida && (
                <div className="flex justify-end mt-4">
                  <button onClick={() => corregir(p, seleccion)} disabled={seleccion.length === 0}
                    className={`px-6 py-2.5 rounded-xl font-medium transition-colors ${seleccion.length > 0 ? 'bg-orange-500 hover:bg-orange-600 text-white cursor-pointer shadow-md shadow-orange-500/20' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}>
                    Comprobar
                  </button>
                </div>
              )}

              {/* Práctica: corrección inmediata con explicación y flashcard */}
              {corregida && (
                <div className="animate-fade-in mt-5 flex flex-col gap-3">
                  <div className={`p-4 rounded-xl border ${r.correcta ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <p className="text-sm text-gray-700">
                      <strong className={r.correcta ? 'text-green-700' : 'text-red-700'}>{r.correcta ? '¡Correcto! ' : 'Has fallado. '}</strong>
                      {p.explicacion}
                    </p>
                  </div>
                  {!r.correcta && (
                    <button onClick={() => { setFlashcard(p); setFlashcardVolteada(false); }} className="self-start text-orange-500 hover:text-orange-600 font-medium text-sm flex items-center gap-1 cursor-pointer">
                      ✨ Crear Flashcard para repasar
                    </button>
                  )}
                </div>
              )}
            </section>
          );
        })}

        {/* Pie: ver resultados (Práctica) o entregar (Examen) */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5 sm:p-6">
          {modo === 'practica' ? (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-sm text-gray-500">
                {pendientes > 0 ? `Te quedan ${pendientes} pregunta${pendientes === 1 ? '' : 's'} por responder.` : '¡Has respondido todas las preguntas!'}
              </p>
              <button onClick={() => finalizar('entrega')} disabled={pendientes > 0}
                className={`px-8 py-3 rounded-xl font-medium transition-colors ${pendientes === 0 ? 'bg-gray-900 hover:bg-black text-white cursor-pointer' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}>
                Ver resultados
              </button>
            </div>
          ) : confirmarEntrega ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-gray-700">
                {pendientes > 0
                  ? <>Tienes <strong>{pendientes} pregunta{pendientes === 1 ? '' : 's'} sin responder</strong>, que contarán como fallo. ¿Entregar de todas formas?</>
                  : '¿Seguro que quieres entregar el examen? Ya no podrás cambiar tus respuestas.'}
              </p>
              <div className="flex flex-col sm:flex-row gap-2 sm:justify-end">
                <button onClick={() => setConfirmarEntrega(false)} className="px-6 py-3 rounded-xl font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 cursor-pointer">Seguir respondiendo</button>
                <button onClick={() => finalizar('entrega')} className="px-6 py-3 rounded-xl font-medium bg-orange-500 hover:bg-orange-600 text-white cursor-pointer">Entregar examen</button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-sm text-gray-500">
                {pendientes > 0 ? `Respondidas ${respondidas} de ${preguntas.length}.` : 'Has respondido todas las preguntas.'} Puedes cambiar tus respuestas hasta entregar.
              </p>
              <button onClick={() => setConfirmarEntrega(true)} className="px-8 py-3 bg-gray-900 hover:bg-black text-white rounded-xl font-medium transition-colors cursor-pointer">
                Entregar examen
              </button>
            </div>
          )}
        </div>
      </div>

      {flashcard && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl relative">
            <button onClick={() => setFlashcard(null)} className="absolute top-4 right-4 text-gray-400 hover:text-gray-800 cursor-pointer">✕</button>
            <div className="text-center mb-6">
              <h3 className="text-orange-500 font-semibold text-sm tracking-wide uppercase">Tu Flashcard Inteligente</h3>
              <p className="text-gray-500 text-xs mt-1">Guardada en tu mazo de repaso automático</p>
            </div>
            <div onClick={() => setFlashcardVolteada(!flashcardVolteada)} className="w-full min-h-48 bg-orange-50 border border-orange-100 rounded-2xl p-6 flex items-center justify-center cursor-pointer transition-all duration-300 hover:shadow-md">
              {!flashcardVolteada ? (
                <div className="text-center">
                  <span className="block text-xs text-orange-400 mb-2 font-medium">Pregunta (Haz clic para girar)</span>
                  <p className="text-lg text-gray-800 font-medium">{flashcard.pregunta}</p>
                </div>
              ) : (
                <div className="text-center animate-fade-in w-full">
                  <span className="block text-xs text-orange-400 mb-2 font-medium">Respuesta{correctasDe(flashcard).length > 1 ? 's' : ''} Clave</span>
                  <p className="text-xl text-orange-600 font-bold mb-3">{correctasDe(flashcard).join(' · ')}</p>
                  <div className="bg-white/60 p-3 rounded-lg text-sm text-gray-600 italic text-left">
                    💡 <span className="font-semibold">Explicación:</span> {flashcard.explicacion}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
