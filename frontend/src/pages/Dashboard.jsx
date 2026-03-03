import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ResumenIA from '../components/ResumenIA';
import RankingClase from '../components/RankingClase';

// Componente inteligente de la tarjeta de temas
const TopicProgressCard = ({ topicName, alumnoId, temaId }) => {
  const navigate = useNavigate();
  
  const [progreso, setProgreso] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    fetch(`https://backend-academia-kxx5.onrender.com/api/progreso/alumno/${alumnoId}/tema/${temaId}`)
      .then((respuesta) => respuesta.json())
      .then((datos) => {
        setProgreso(datos);
        setCargando(false);
      })
      .catch((error) => {
        console.error("Error al obtener el progreso:", error);
        setCargando(false);
      });
  }, [alumnoId, temaId]);

  if (cargando) {
    return (
      <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center justify-center min-h-[220px]">
        <span className="text-orange-500 font-medium animate-pulse">Calculando nivel...</span>
      </div>
    );
  }

  if (!progreso) return null;

  const progressWidth = `${progreso.porcentaje_actual}%`;
  const isTargetMet = progreso.superado;

  return (
    <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-medium text-gray-800">{topicName}</h3>
        {isTargetMet && (
          <span className="px-3 py-1 text-xs font-semibold text-green-700 bg-green-100 rounded-full">
            ¡Nivel Superado!
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Llevas este tema al <strong className="text-gray-800">{progreso.porcentaje_actual}%</strong> · Nivel aprobado: {progreso.nivel_aprobado}%
      </p>
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-1000 ease-out ${isTargetMet ? 'bg-green-500' : 'bg-orange-500'}`} 
          style={{ width: progressWidth }}
        ></div>
      </div>
      <div className="mt-6 flex gap-3">
        <button 
          onClick={() => navigate('/test', { state: { temaId: temaId } })}
          className="flex-1 py-2 px-4 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors cursor-pointer"
        >
          Hacer test rápido
        </button>
        
        {/* NUEVO BOTÓN DE ESQUEMA VISUAL */}
        <button 
          onClick={() => navigate('/esquema', { state: { temaNombre: topicName } })}
          className="flex-1 py-2 px-4 bg-white border border-gray-200 hover:border-orange-500 hover:text-orange-500 text-gray-600 font-medium rounded-lg transition-colors cursor-pointer"
        >
          Ver esquema visual
        </button>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate(); // <-- Añadimos el hook de navegación aquí también
  const nombreGuardado = localStorage.getItem('nombreOpositor');
  const [nombre, setNombre] = useState(nombreGuardado || '');
  
  const [mostrarModal, setMostrarModal] = useState(!nombreGuardado);
  const [inputNombre, setInputNombre] = useState('');

  const guardarNombre = () => {
    if (inputNombre.trim() !== '') {
      localStorage.setItem('nombreOpositor', inputNombre);
      setNombre(inputNombre);
      setMostrarModal(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans relative">
      
      {mostrarModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-sm w-full shadow-2xl text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">¡Bienvenido! 👋</h2>
            <p className="text-gray-500 text-sm mb-6">¿Con qué nombre vas a arrasar en el ranking?</p>
            <input 
              type="text" 
              placeholder="Tu nombre o alias..."
              value={inputNombre}
              onChange={(e) => setInputNombre(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && guardarNombre()}
              className="w-full p-4 border-2 border-gray-100 rounded-xl mb-4 focus:border-orange-500 focus:outline-none transition-colors"
              autoFocus
            />
            <button 
              onClick={guardarNombre}
              className="w-full py-3 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-xl transition-all cursor-pointer"
            >
              Entrar a la academia
            </button>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-light text-gray-900">
            Hola, <span className="font-semibold text-orange-500">{nombre || 'Opositor'}</span>
          </h1>
          <p className="text-gray-500 mt-2">¿Qué vamos a estudiar hoy?</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div className="lg:col-span-2 space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TopicProgressCard topicName="Tema 1: La Constitución Española" alumnoId={1} temaId={1} />
              <TopicProgressCard topicName="Tema 2: El Gobierno y la Administración" alumnoId={1} temaId={2} />
            </div>
            <ResumenIA />
          </div>

          <div className="lg:col-span-1 space-y-6">
            
            {/* NUEVA TARJETA: Acceso al Modo Repaso */}
            <div className="bg-gray-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
              {/* Círculo decorativo de fondo */}
              <div className="absolute -right-8 -top-8 w-32 h-32 bg-orange-500/20 rounded-full blur-2xl"></div>
              
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-3xl">🗂️</span>
                  <h3 className="text-xl font-bold">Mazo de Repaso</h3>
                </div>
                <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                  Enfréntate a tus puntos débiles. La IA guarda tus fallos aquí para que los transformes en aciertos.
                </p>
                <button 
                  onClick={() => navigate('/repaso')}
                  className="w-full py-3 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-xl transition-colors cursor-pointer shadow-lg shadow-orange-500/20"
                >
                  Entrar al repaso ➔
                </button>
              </div>
            </div>

            <RankingClase />
            
            <div className="p-6 bg-orange-500 rounded-3xl text-white shadow-lg shadow-orange-500/20">
              <h4 className="font-bold mb-2">¡Vas por buen camino!</h4>
              <p className="text-sm opacity-90">Has completado varios tests hoy. Superas al 70% de tus compañeros en constancia.</p>
            </div>
            
          </div>

        </div>
      </div>
    </div>
  );
}