import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Test() {
  const navigate = useNavigate();
  const location = useLocation(); 
  
  // Capturamos el ID del tema y el ID específico del test desde el Banco de Tests
  const temaIdActual = location.state?.temaId || 1;
  const testPlantillaId = location.state?.testPlantillaId; // <-- NUEVO: ID del test (ej. el test nº 12)

  const usuarioId = localStorage.getItem('usuario_id');
  const nombreUsuario = localStorage.getItem('nombre_usuario') || "Opositor";

  // Estados de datos y carga
  const [preguntasTest, setPreguntasTest] = useState([]);
  const [cargando, setCargando] = useState(true);

  // Estados del juego
  const [indicePregunta, setIndicePregunta] = useState(0);
  const [opcionSeleccionada, setOpcionSeleccionada] = useState(null);
  const [estadoRespuesta, setEstadoRespuesta] = useState(null);
  const [tiempoRestante, setTiempoRestante] = useState(120);
  
  // Estados de puntuación y finalización
  const [aciertos, setAciertos] = useState(0);
  const [testFinalizado, setTestFinalizado] = useState(false);

  // Estado para ir acumulando las respuestas que luego enviaremos a la barra de progreso
  const [historialRespuestas, setHistorialRespuestas] = useState([]);

  // Estados de Flashcard
  const [mostrarFlashcard, setMostrarFlashcard] = useState(false);
  const [flashcardVolteada, setFlashcardVolteada] = useState(false);

  useEffect(() => {
    fetch(`https://backend-academia-kxx5.onrender.com/api/test/generar?tema_id=${temaIdActual}`)
      .then(res => res.json())
      .then(datos => {
        setPreguntasTest(datos);
        setCargando(false);
      })
      .catch(error => {
        console.error("Error al cargar las preguntas:", error);
        setCargando(false);
      });
  }, [temaIdActual]); 

  useEffect(() => {
    if (tiempoRestante <= 0 || cargando || testFinalizado || preguntasTest.length === 0) return;
    const temporizador = setInterval(() => {
      setTiempoRestante(t => t - 1);
    }, 1000);
    return () => clearInterval(temporizador);
  }, [tiempoRestante, cargando, testFinalizado, preguntasTest]);

  // --- NUEVA FUNCIÓN: Guarda el intento en el historial de la tabla ---
  const enviarIntentoBancoTests = async (fallosTotales) => {
    // Si entró directo sin pasar por el listado, no hay ID de plantilla, así que no guardamos este dato.
    if (!testPlantillaId) return; 

    try {
      await fetch('https://backend-academia-kxx5.onrender.com/api/test/registrar-intento', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          alumno_id: parseInt(usuarioId),
          test_plantilla_id: testPlantillaId,
          fallos: fallosTotales
        })
      });
      console.log("✅ Intento registrado en el Banco de Tests");
    } catch (error) {
      console.error("Error al guardar intento en la tabla:", error);
    }
  };

  const enviarPuntuacion = async (puntosLogrados) => {
    try {
      await fetch('https://backend-academia-kxx5.onrender.com/api/ranking/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          nombre: nombreUsuario,
          puntos: puntosLogrados 
        })
      });
      console.log("✅ Puntuación enviada al ranking");
    } catch (error) {
      console.error("Error al guardar puntos:", error);
    }
  };

  const enviarResultadosAlBackend = async () => {
    const payload = {
        alumno_id: parseInt(usuarioId), 
        respuestas: historialRespuestas
    };

    try {
        const response = await fetch('https://backend-academia-kxx5.onrender.com/api/progreso/guardar-resultados', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            console.log("✅ Barras de progreso actualizadas");
        }
    } catch (error) {
        console.error("❌ Hubo un error al guardar el progreso:", error);
    }
  };

  const formatearTiempo = (segundosTotales) => {
    const minutos = Math.floor(segundosTotales / 60);
    const segundos = segundosTotales % 60;
    return `${minutos}:${segundos < 10 ? '0' : ''}${segundos}`;
  };

  const manejarSeleccion = (opcion) => {
    if (estadoRespuesta) return; 
    setOpcionSeleccionada(opcion);
  };

  const comprobarRespuesta = async () => {
    if (!opcionSeleccionada) return;
    
    const preguntaActual = preguntasTest[indicePregunta];
    const esCorrecta = opcionSeleccionada === preguntaActual.respuestaCorrecta;
    
    setEstadoRespuesta(esCorrecta ? 'correcta' : 'incorrecta');
    if (esCorrecta) setAciertos(prev => prev + 1);

    setHistorialRespuestas(prev => [...prev, {
      pregunta_id: preguntaActual.id,
      es_correcta: esCorrecta
    }]);

    if (!esCorrecta) {
      try {
        await fetch('https://backend-academia-kxx5.onrender.com/api/test/fallo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            pregunta_id: preguntaActual.id,
            alumno_id: parseInt(usuarioId) 
          })
        });
      } catch (error) {
        console.error("Error al registrar fallo:", error);
      }
    }
  };

  const siguientePregunta = () => {
    if (indicePregunta + 1 < preguntasTest.length) {
      setIndicePregunta(indicePregunta + 1);
      setOpcionSeleccionada(null);
      setEstadoRespuesta(null);
      setMostrarFlashcard(false);
      setFlashcardVolteada(false);
    } else {
      setTestFinalizado(true);
    }
  };

  if (cargando) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans">
        <div className="text-orange-500 font-medium animate-pulse">Preparando test inteligente...</div>
      </div>
    );
  }

  if (preguntasTest.length === 0 && !cargando) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center font-sans gap-4">
        <div className="text-2xl">🚧</div>
        <div className="text-gray-600 font-medium">Aún no hay preguntas para este tema.</div>
        <button onClick={() => navigate('/')} className="px-6 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors">Volver</button>
      </div>
    );
  }

  if (testFinalizado) {
    const porcentajeAciertos = Math.round((aciertos / preguntasTest.length) * 100);
    const superado = porcentajeAciertos >= 80;
    
    // Calculamos los fallos totales del test
    const fallosTotales = preguntasTest.length - aciertos;

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-xl text-center border border-gray-100">
          <div className="text-6xl mb-4">{superado ? '🎉' : '📚'}</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            {superado ? '¡Nivel Superado!' : 'Sigue practicando'}
          </h2>
          
          <div className="my-8">
            <div className="text-5xl font-black text-orange-500 mb-2">{porcentajeAciertos}%</div>
            <p className="text-gray-500">Tu nivel en este test</p>
          </div>

          <div className="bg-gray-50 rounded-2xl p-4 mb-8">
            <p className="text-sm text-gray-600">
              Nivel objetivo: <span className="font-bold">80%</span>
            </p>
            <div className="w-full h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
              <div 
                className={`h-full transition-all duration-1000 ${superado ? 'bg-green-500' : 'bg-orange-400'}`}
                style={{ width: `${porcentajeAciertos}%` }}
              ></div>
            </div>
          </div>

          <button 
            onClick={async () => {
              // --- EL GRAN FINAL: Disparamos las tres actualizaciones a la vez ---
              await enviarIntentoBancoTests(fallosTotales); // 1. Actualiza la tabla
              await enviarResultadosAlBackend();            // 2. Actualiza la barra del tema
              await enviarPuntuacion(aciertos);             // 3. Actualiza el ranking
              
              navigate('/listado-tests', { state: { temaId: temaIdActual } }); // Volvemos al listado
            }}
            className="w-full py-4 bg-gray-900 text-white rounded-2xl font-semibold hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Finalizar y guardar nota
          </button>
        </div>
      </div>
    );
  }

  const preguntaActual = preguntasTest[indicePregunta];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4 font-sans relative">
      <div className="w-full max-w-3xl flex justify-between items-center mb-8">
        <button onClick={() => navigate('/listado-tests', { state: { temaId: temaIdActual } })} className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer font-medium">✕ Salir</button>
        <div className="flex gap-4">
          <div className={`text-sm font-medium px-4 py-1.5 rounded-full shadow-sm border transition-colors ${tiempoRestante < 30 ? 'bg-red-50 text-red-600 border-red-200 animate-pulse' : 'bg-white text-gray-600 border-gray-200'}`}>
            ⏱ {formatearTiempo(tiempoRestante)}
          </div>
          <div className="text-sm font-medium text-gray-500 bg-white px-4 py-1.5 rounded-full shadow-sm border border-gray-100">
            Pregunta {indicePregunta + 1} de {preguntasTest.length}
          </div>
        </div>
      </div>

      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-sm border border-gray-100 p-8 md:p-12">
        <h2 className="text-2xl md:text-3xl font-medium text-gray-800 mb-8 leading-snug">{preguntaActual.pregunta}</h2>

        <div className="flex flex-col gap-3 mb-8">
          {preguntaActual.opciones.map((opcion, index) => {
            let estilosOpcion = "border-gray-200 hover:border-orange-500 hover:bg-orange-50 text-gray-700";
            if (estadoRespuesta) {
              if (opcion === preguntaActual.respuestaCorrecta) estilosOpcion = "border-green-500 bg-green-50 text-green-800 font-medium";
              else if (opcion === opcionSeleccionada && estadoRespuesta === 'incorrecta') estilosOpcion = "border-red-400 bg-red-50 text-red-700";
              else estilosOpcion = "border-gray-100 text-gray-400 opacity-60";
            } else if (opcion === opcionSeleccionada) {
              estilosOpcion = "border-orange-500 bg-orange-50 text-orange-700 font-medium ring-1 ring-orange-500";
            }

            return (
              <button key={index} onClick={() => manejarSeleccion(opcion)} className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 cursor-pointer ${estilosOpcion}`}>
                <span className="inline-block w-8 font-semibold opacity-60">{['A', 'B', 'C', 'D'][index]}.</span>
                {opcion}
              </button>
            );
          })}
        </div>

        <div className="min-h-20">
          {!estadoRespuesta ? (
            <div className="flex justify-end">
              <button onClick={comprobarRespuesta} disabled={!opcionSeleccionada} className={`px-8 py-3 rounded-xl font-medium transition-colors ${opcionSeleccionada ? 'bg-orange-500 hover:bg-orange-600 text-white cursor-pointer shadow-md shadow-orange-500/20' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}>Comprobar</button>
            </div>
          ) : (
            <div className="animate-fade-in flex flex-col gap-4">
              <div className={`p-4 rounded-xl border ${estadoRespuesta === 'correcta' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <p className="text-sm text-gray-700">
                  <strong className={estadoRespuesta === 'correcta' ? 'text-green-700' : 'text-red-700'}>
                    {estadoRespuesta === 'correcta' ? '¡Correcto! ' : 'Has fallado. '}
                  </strong>
                  {preguntaActual.explicacion}
                </p>
              </div>
              <div className="flex justify-between items-center mt-2">
                {estadoRespuesta === 'incorrecta' ? (
                  <button onClick={() => setMostrarFlashcard(true)} className="text-orange-500 hover:text-orange-600 font-medium text-sm flex items-center gap-1 cursor-pointer">✨ Crear Flashcard para repasar</button>
                ) : <div></div>}
                <button onClick={siguientePregunta} className="px-8 py-3 bg-gray-900 hover:bg-black text-white rounded-xl font-medium transition-colors cursor-pointer">
                  {indicePregunta + 1 === preguntasTest.length ? 'Ver Resultados' : 'Siguiente'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {mostrarFlashcard && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl relative">
            <button onClick={() => setMostrarFlashcard(false)} className="absolute top-4 right-4 text-gray-400 hover:text-gray-800 cursor-pointer">✕</button>
            <div className="text-center mb-6">
              <h3 className="text-orange-500 font-semibold text-sm tracking-wide uppercase">Tu Flashcard Inteligente</h3>
              <p className="text-gray-500 text-xs mt-1">Guardada en tu mazo de repaso automático</p>
            </div>
            
            <div onClick={() => setFlashcardVolteada(!flashcardVolteada)} className="w-full min-h-48 bg-orange-50 border border-orange-100 rounded-2xl p-6 flex items-center justify-center cursor-pointer transition-all duration-300 hover:shadow-md">
              {!flashcardVolteada ? (
                
                <div className="text-center">
                  <span className="block text-xs text-orange-400 mb-2 font-medium">Pregunta (Haz clic para girar)</span>
                  <p className="text-lg text-gray-800 font-medium">{preguntaActual.pregunta}</p>
                </div>
                
              ) : (
                
                <div className="text-center animate-fade-in w-full">
                  <span className="block text-xs text-orange-400 mb-2 font-medium">Respuesta Clave</span>
                  <p className="text-xl text-orange-600 font-bold mb-3">{preguntaActual.respuestaCorrecta}</p>
                  
                  <div className="bg-white/60 p-3 rounded-lg text-sm text-gray-600 italic text-left">
                    💡 <span className="font-semibold">Explicación:</span> {preguntaActual.explicacion}
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