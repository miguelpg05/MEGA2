import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api';
import { Cargando, MensajeError } from '../components/Estado';

export default function Repaso() {
  const navigate = useNavigate();

  const [flashcards, setFlashcards] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [indiceActual, setIndiceActual] = useState(0);
  const [estadoRespuesta, setEstadoRespuesta] = useState(null);
  const [opcionSeleccionada, setOpcionSeleccionada] = useState(null);

  // Cargamos los fallos pendientes del usuario autenticado al entrar
  const cargarPendientes = useCallback(() => {
    apiFetch('/api/repaso/pendientes')
      .then(res => {
        if (!res.ok) throw new Error('respuesta no OK');
        return res.json();
      })
      .then(datos => {
        setFlashcards(datos);
        setError(false);
        setCargando(false);
      })
      .catch(err => {
        console.error("Error al cargar repasos:", err);
        setError(true);
        setCargando(false);
      });
  }, []);

  useEffect(() => {
    cargarPendientes();
  }, [cargarPendientes]);

  const reintentar = () => {
    setCargando(true);
    setError(false);
    cargarPendientes();
  };

  // Respuestas correctas de la carta (siempre como lista)
  const correctasDe = (carta) =>
    carta.respuestasCorrectas && carta.respuestasCorrectas.length
      ? carta.respuestasCorrectas
      : [carta.respuestaCorrecta];

  const comprobarRespuesta = async (opcionElegida) => {
    if (estadoRespuesta) return;

    setOpcionSeleccionada(opcionElegida);
    const cartaActual = flashcards[indiceActual];
    // En el repaso (revisión de fallos) basta con identificar una opción correcta.
    const esCorrecta = correctasDe(cartaActual).includes(opcionElegida);

    setEstadoRespuesta(esCorrecta ? 'correcta' : 'incorrecta');

    // Si acierta, avisamos a FastAPI para que borre este fallo de su lista negra
    if (esCorrecta) {
      try {
        await apiFetch('/api/repaso/completar', {
          method: 'POST',
          body: JSON.stringify({ fallo_id: cartaActual.fallo_id })
        });
      } catch (error) {
        console.error("Error al marcar como completado:", error);
      }
    }
  };

  const siguienteCarta = () => {
    setEstadoRespuesta(null);
    setOpcionSeleccionada(null);
    setIndiceActual(prev => prev + 1);
  };

  if (cargando) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
        <Cargando texto="Buscando tus puntos débiles..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
        <MensajeError texto="No se pudo cargar tu mazo de repaso. Revisa tu conexión." onReintentar={reintentar} />
      </div>
    );
  }

  // Si no hay fallos pendientes, mostramos un mensaje de victoria
  if (flashcards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-sm text-center border border-gray-100">
          <div className="text-6xl mb-4">🏆</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">¡Mazo limpio!</h2>
          <p className="text-gray-500 mb-8">No tienes ninguna pregunta pendiente de repaso. Estás al día con tus errores.</p>
          <button 
            onClick={() => navigate('/')}
            className="w-full py-4 bg-orange-500 text-white rounded-2xl font-semibold hover:bg-orange-600 transition-colors cursor-pointer"
          >
            Volver a la Academia
          </button>
        </div>
      </div>
    );
  }

  // Pantalla de fin de repaso
  if (indiceActual >= flashcards.length) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-sm text-center border border-gray-100">
          <div className="text-6xl mb-4">🧠</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Sesión de repaso terminada</h2>
          <p className="text-gray-500 mb-8">Has revisado {flashcards.length} conceptos clave. ¡La constancia es la clave del aprobado!</p>
          <button 
            onClick={() => navigate('/')}
            className="w-full py-4 bg-gray-900 text-white rounded-2xl font-semibold hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Volver al Dashboard
          </button>
        </div>
      </div>
    );
  }

  const cartaActual = flashcards[indiceActual];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4 font-sans relative">
      <div className="w-full max-w-3xl flex justify-between items-center mb-8">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer font-medium">✕ Salir del Repaso</button>
        <div className="text-sm font-medium text-orange-600 bg-orange-50 px-4 py-1.5 rounded-full border border-orange-100">
          Flashcard {indiceActual + 1} de {flashcards.length}
        </div>
      </div>

      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-sm border border-gray-100 p-8 md:p-12">
        <div className="mb-4 text-sm font-bold text-orange-500 tracking-wide uppercase">Repaso Activo</div>
        <h2 className="text-2xl md:text-3xl font-medium text-gray-800 mb-8 leading-snug">{cartaActual.pregunta}</h2>

        <div className="flex flex-col gap-3 mb-8">
          {cartaActual.opciones.map((opcion, index) => {
            let estilosOpcion = "border-gray-200 hover:border-orange-500 hover:bg-orange-50 text-gray-700 cursor-pointer";
            
            if (estadoRespuesta) {
              if (correctasDe(cartaActual).includes(opcion)) estilosOpcion = "border-green-500 bg-green-50 text-green-800 font-medium";
              else if (opcion === opcionSeleccionada && estadoRespuesta === 'incorrecta') estilosOpcion = "border-red-400 bg-red-50 text-red-700";
              else estilosOpcion = "border-gray-100 text-gray-400 opacity-60 cursor-default";
            }

            return (
              <button 
                key={index} 
                onClick={() => comprobarRespuesta(opcion)} 
                disabled={estadoRespuesta !== null}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${estilosOpcion}`}
              >
                {opcion}
              </button>
            );
          })}
        </div>

        {/* Zona de Feedback Explicativo */}
        {estadoRespuesta && (
          <div className="animate-fade-in flex flex-col gap-4">
            <div className={`p-6 rounded-2xl border ${estadoRespuesta === 'correcta' ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
              <h4 className={`font-bold mb-2 ${estadoRespuesta === 'correcta' ? 'text-green-800' : 'text-orange-800'}`}>
                {estadoRespuesta === 'correcta' ? '¡Bien hecho! Superado.' : 'Aún hay que afianzarlo.'}
              </h4>
              <p className="text-gray-700 leading-relaxed text-sm">
                <span className="font-semibold">Explicación: </span> 
                {cartaActual.explicacion}
              </p>
            </div>
            
            <div className="flex justify-end mt-4">
              <button onClick={siguienteCarta} className="px-8 py-4 bg-gray-900 hover:bg-black text-white rounded-xl font-bold transition-colors cursor-pointer w-full md:w-auto">
                {indiceActual + 1 === flashcards.length ? 'Terminar Repaso' : 'Siguiente Flashcard ➔'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}