import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ResumenIA from '../components/ResumenIA';
import RankingClase from '../components/RankingClase';
import GraficoEvolucion from '../components/GraficoEvolucion';
import { Cargando, MensajeError } from '../components/Estado';
import { useAuth } from '../auth/AuthContext';
import { apiFetch } from '../api';

// Consejos de estudio reales (no inventamos estadísticas de rendimiento).
// Rotan por día para dar algo de variedad sin afirmar datos falsos.
const CONSEJOS_ESTUDIO = [
  'Repasa tus fallos de ayer antes de empezar un test nuevo: consolidar vence al olvido.',
  'Estudia en bloques de 25 minutos con descansos cortos. La constancia pesa más que las maratones.',
  'Explica el tema en voz alta como si se lo enseñaras a alguien: si no puedes, aún no lo dominas.',
  'Haz un test de repaso al final del día. Recordar es más eficaz que releer.',
  'Prioriza los temas con menor porcentaje: ahí está tu mayor margen de mejora.',
];

// Componente inteligente de la tarjeta de temas
const TopicProgressCard = ({ topicName, temaId }) => {
  const navigate = useNavigate();

  const [progreso, setProgreso] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  // Nota: no mutamos estado de forma síncrona aquí (solo en los callbacks async),
  // para no disparar renders en cascada desde el efecto. El reintento manual
  // (evento de usuario) sí puede resetear el estado de carga.
  const cargar = useCallback(() => {
    apiFetch(`/api/progreso/tema/${temaId}`)
      .then((respuesta) => {
        if (!respuesta.ok) throw new Error('respuesta no OK');
        return respuesta.json();
      })
      .then((datos) => {
        setProgreso(datos);
        setError(false);
        setCargando(false);
      })
      .catch((err) => {
        console.error('Error al obtener el progreso:', err);
        setError(true);
        setCargando(false);
      });
  }, [temaId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const reintentar = () => {
    setCargando(true);
    setError(false);
    cargar();
  };

  if (cargando) {
    return (
      <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center justify-center min-h-[220px]">
        <Cargando texto="Calculando nivel..." />
      </div>
    );
  }

  if (error || !progreso) {
    return (
      <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center justify-center min-h-[220px]">
        <MensajeError texto="No se pudo cargar el progreso de este tema." onReintentar={reintentar} />
      </div>
    );
  }

  const progressWidth = `${progreso.porcentaje_actual}%`;
  const isTargetMet = progreso.superado;

  return (
    <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-center mb-4 gap-2">
        <h3 className="text-lg sm:text-xl font-medium text-gray-800">{topicName}</h3>
        {isTargetMet && (
          <span className="shrink-0 px-3 py-1 text-xs font-semibold text-green-700 bg-green-100 rounded-full">
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

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          onClick={() => navigate('/listado-tests', { state: { temaId: temaId } })}
          className="py-2 px-3 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors cursor-pointer"
        >
          Tests
        </button>

        <button
          onClick={() => navigate('/material', { state: { temaId: temaId, temaNombre: topicName } })}
          className="py-2 px-3 bg-white border border-gray-200 hover:border-orange-500 hover:text-orange-500 text-gray-600 font-medium rounded-lg transition-colors cursor-pointer"
        >
          📄 Material
        </button>

        <button
          onClick={() => navigate('/esquema', { state: { temaId: temaId, temaNombre: topicName } })}
          className="py-2 px-3 bg-white border border-gray-200 hover:border-orange-500 hover:text-orange-500 text-gray-600 font-medium rounded-lg transition-colors cursor-pointer"
        >
          Esquema
        </button>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { usuario } = useAuth();

  // Nombre validado por el backend (AuthContext); si aún no llegó, usamos el de localStorage.
  const nombreUsuario = usuario?.nombre || localStorage.getItem('nombre_usuario') || 'Opositor';
  const esStaff = usuario?.rol === 'admin' || usuario?.rol === 'superadmin';

  // Los temas se leen de la base de datos (los que crees en el panel aparecen aquí)
  const [temas, setTemas] = useState([]);
  const [cargandoTemas, setCargandoTemas] = useState(true);
  const [errorTemas, setErrorTemas] = useState(false);

  const cargarTemas = useCallback(() => {
    apiFetch('/api/temas')
      .then((r) => {
        if (!r.ok) throw new Error('respuesta no OK');
        return r.json();
      })
      .then((datos) => { setTemas(datos); setErrorTemas(false); setCargandoTemas(false); })
      .catch((err) => { console.error('Error al cargar los temas:', err); setErrorTemas(true); setCargandoTemas(false); });
  }, []);

  useEffect(() => { cargarTemas(); }, [cargarTemas]);

  const reintentarTemas = () => { setCargandoTemas(true); setErrorTemas(false); cargarTemas(); };

  // Consejo del día (determinista según la fecha, sin datos inventados)
  const consejoDelDia = CONSEJOS_ESTUDIO[new Date().getDate() % CONSEJOS_ESTUDIO.length];

  const cerrarSesion = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Si ya no hay sesión válida no pasa nada, igualmente limpiamos y salimos
    }
    localStorage.removeItem('token');
    localStorage.removeItem('usuario_id');
    localStorage.removeItem('nombre_usuario');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 font-sans relative">
      <div className="max-w-6xl mx-auto">

        {/* CABECERA PERSONALIZADA CON BOTÓN DE SALIR */}
        <header className="mb-8 flex flex-col md:flex-row md:justify-between md:items-center bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
          <div className="mb-4 md:mb-0">
            <h1 className="text-2xl sm:text-3xl font-light text-gray-900">
              Hola, <span className="font-semibold text-orange-500">{nombreUsuario}</span> 👋
            </h1>
            <p className="text-gray-500 mt-2">¿Qué vamos a estudiar hoy?</p>
          </div>
          <div className="flex flex-wrap gap-3 self-start md:self-auto">
            {esStaff && (
              <button
                onClick={() => navigate('/admin')}
                className="text-sm bg-gray-900 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-gray-800 transition-colors shadow-sm cursor-pointer"
              >
                ⚙️ Panel admin
              </button>
            )}
            <button
              onClick={cerrarSesion}
              className="text-sm bg-red-50 text-red-600 px-5 py-2.5 rounded-xl font-medium hover:bg-red-100 transition-colors shadow-sm cursor-pointer"
            >
              Cerrar sesión
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">

          {/* COLUMNA PRINCIPAL (IZQUIERDA Y CENTRO) */}
          <div className="lg:col-span-2 space-y-8">

            {/* TARJETAS DE PROGRESO POR TEMA (leídas de la base de datos) */}
            {cargandoTemas ? (
              <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center justify-center min-h-[220px]">
                <Cargando texto="Cargando tus temas..." />
              </div>
            ) : errorTemas ? (
              <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm">
                <MensajeError texto="No se pudieron cargar los temas." onReintentar={reintentarTemas} />
              </div>
            ) : temas.length === 0 ? (
              <div className="p-8 bg-white border border-gray-200 rounded-2xl shadow-sm text-center">
                <div className="text-4xl mb-3">📚</div>
                <p className="text-gray-600 font-medium">Todavía no hay temas disponibles.</p>
                <p className="text-gray-400 text-sm mt-1">
                  {esStaff
                    ? 'Créalos desde el Panel admin y aparecerán aquí automáticamente.'
                    : 'Tu academia aún no ha publicado temario para tus cursos.'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {temas.map((t) => (
                  <TopicProgressCard key={t.id} topicName={t.nombre} temaId={t.id} />
                ))}
              </div>
            )}

            <ResumenIA />
          </div>

          {/* COLUMNA LATERAL (DERECHA) */}
          <div className="lg:col-span-1 space-y-6">

            <div className="bg-gray-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
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

            {/* Ficha de evolución de resultados (justo debajo del Mazo de Repaso) */}
            <GraficoEvolucion />

            <RankingClase />

            {/* CONSEJO DEL DÍA (real, sin estadísticas inventadas) */}
            <div className="p-6 bg-orange-500 rounded-3xl text-white shadow-lg shadow-orange-500/20">
              <h4 className="font-bold mb-2 flex items-center gap-2">💡 Consejo del día</h4>
              <p className="text-sm opacity-90 leading-relaxed">{consejoDelDia}</p>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
