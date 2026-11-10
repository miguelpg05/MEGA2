import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { cargaDiferida } from '../utils/cargaDiferida';
import RankingClase from '../components/RankingClase';
import GraficoEvolucion from '../components/GraficoEvolucion';
import { Cargando, MensajeError } from '../components/Estado';
import { useAuth } from '../auth/AuthContext';
import { apiFetch } from '../api';
import SelectorCurso from '../components/SelectorCurso';
import MiCuenta from '../components/MiCuenta';
import { agruparPorCurso, resolverGrupo, guardarCursoActivo } from '../utils/cursos';
import { useTituloPagina } from '../utils/titulo';

// El resumen con IA (y su librería de Markdown) se descarga solo cuando hace falta
const ResumenIA = cargaDiferida(() => import('../components/ResumenIA'));

// Consejos de estudio reales (no inventamos estadísticas de rendimiento).
// Rotan por día para dar algo de variedad sin afirmar datos falsos.
const CONSEJOS_ESTUDIO = [
  'Repasa tus fallos de ayer antes de empezar un test nuevo: consolidar vence al olvido.',
  'Estudia en bloques de 25 minutos con descansos cortos. La constancia pesa más que las maratones.',
  'Explica el tema en voz alta como si se lo enseñaras a alguien: si no puedes, aún no lo dominas.',
  'Haz un test de repaso al final del día. Recordar es más eficaz que releer.',
  'Prioriza los temas con menor porcentaje: ahí está tu mayor margen de mejora.',
];

// Tarjeta de un tema (diseño original). El progreso llega ya calculado del
// Dashboard: una sola petición para todos los temas en lugar de una por tarjeta.
const TopicProgressCard = ({ tema, progreso }) => {
  const navigate = useNavigate();
  const porcentaje = progreso?.porcentaje_actual ?? 0;
  const isTargetMet = progreso?.superado ?? false;
  const nivelAprobado = progreso?.nivel_aprobado ?? 80;
  const estado = { temaId: tema.id, temaNombre: tema.nombre };

  return (
    <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-center mb-4 gap-2">
        <h3 className="text-lg sm:text-xl font-medium text-gray-800">{tema.nombre}</h3>
        {isTargetMet && (
          <span className="shrink-0 px-3 py-1 text-xs font-semibold text-green-700 bg-green-100 rounded-full">
            ¡Nivel Superado!
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Llevas este tema al <strong className="text-gray-800">{porcentaje}%</strong> · Nivel aprobado: {nivelAprobado}%
      </p>
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${isTargetMet ? 'bg-green-500' : 'bg-orange-500'}`}
          style={{ width: `${porcentaje}%` }}
        ></div>
      </div>

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          onClick={() => navigate('/listado-tests', { state: estado })}
          className="py-2 px-3 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors cursor-pointer"
        >
          Tests
        </button>
        <button
          onClick={() => navigate('/material', { state: estado })}
          className="py-2 px-3 bg-white border border-gray-200 hover:border-orange-500 hover:text-orange-500 text-gray-600 font-medium rounded-lg transition-colors cursor-pointer"
        >
          📄 Material
        </button>
      </div>
    </div>
  );
};

// Secciones de la pantalla de inicio. En el móvil se ve una cada vez (barra
// inferior); en el ordenador se ven todas a la vez.
const SECCIONES = [
  { id: 'estudiar', icono: '📚', texto: 'Estudiar' },
  { id: 'repaso', icono: '🗂️', texto: 'Repaso' },
  { id: 'clase', icono: '🏆', texto: 'Clase' },
];

// Tarjeta de acceso a "Personaliza tu test"
const PersonalizaTestCard = ({ onAbrir, nombreCurso }) => (
  <div className="p-5 sm:p-6 bg-white border-2 border-orange-100 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center gap-4">
    <div className="hidden sm:block text-4xl" aria-hidden="true">🧩</div>
    <div className="flex-1">
      <h3 className="text-lg font-semibold text-gray-800">Personaliza tu test</h3>
      <p className="text-sm text-gray-500 mt-1">
        Elige los temas{nombreCurso ? ` de ${nombreCurso}` : ''}, cuántas preguntas quieres y tu tiempo disponible (o sin límite).
      </p>
    </div>
    <button
      onClick={onAbrir}
      className="shrink-0 py-2.5 px-5 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl transition-colors cursor-pointer shadow-md shadow-orange-500/20"
    >
      Crear mi test ➔
    </button>
  </div>
);

export default function Dashboard() {
  useTituloPagina('Inicio');
  const navigate = useNavigate();
  const location = useLocation();
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

  // Progreso de todos los temas en UNA petición (antes era una por tarjeta)
  const [progresos, setProgresos] = useState({});
  const [errorProgreso, setErrorProgreso] = useState(false);
  const cargarProgreso = useCallback(() => {
    apiFetch('/api/progreso/temas')
      .then((r) => {
        if (!r.ok) throw new Error('respuesta no OK');
        return r.json();
      })
      .then((datos) => { setProgresos(datos || {}); setErrorProgreso(false); })
      .catch((err) => { console.error('Error al cargar el progreso:', err); setErrorProgreso(true); });
  }, []);
  useEffect(() => { cargarProgreso(); }, [cargarProgreso]);

  const [seccion, setSeccion] = useState('estudiar');
  const [cuentaAbierta, setCuentaAbierta] = useState(false);
  const cambiarSeccion = (id) => { setSeccion(id); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  // En el móvil solo se ve la sección activa; desde lg se ven todas
  const visible = (id) => (seccion === id ? 'block' : 'hidden lg:block');

  // Varios cursos: se agrupan los temas por curso y se muestra uno cada vez.
  const grupos = agruparPorCurso(temas);
  const [cursoElegido, setCursoElegido] = useState(location.state?.cursoId ?? null);
  const grupoActivo = resolverGrupo(grupos, cursoElegido);
  const temasVisibles = grupoActivo ? grupoActivo.temas : [];
  const variosCursos = grupos.length > 1;

  const cambiarCurso = (id) => {
    setCursoElegido(id);
    guardarCursoActivo(id);
  };

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
    <div className="min-h-screen bg-gray-50 p-4 pb-28 sm:p-6 sm:pb-28 lg:p-8 lg:pb-8 font-sans relative">
      <div className="max-w-6xl mx-auto">

        {/* CABECERA */}
        <header className="mb-6 lg:mb-8 flex flex-col md:flex-row md:justify-between md:items-center bg-white p-5 sm:p-6 rounded-3xl shadow-sm border border-gray-100">
          <div className="mb-4 md:mb-0">
            <h1 className="text-xl sm:text-3xl font-light text-gray-900">
              Hola, <span className="font-semibold text-orange-500">{nombreUsuario}</span> 👋
            </h1>
            <p className="text-gray-500 mt-2">
              ¿Qué vamos a estudiar hoy?
              {variosCursos && grupoActivo && (
                <> Estás en <strong className="text-gray-700">{grupoActivo.nombre}</strong>.</>
              )}
            </p>
          </div>
          <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 sm:gap-3 md:self-auto">
            {esStaff && (
              <button
                onClick={() => navigate('/admin')}
                className="col-span-2 sm:col-span-1 text-sm bg-gray-900 text-white px-4 sm:px-5 py-2.5 rounded-xl font-medium hover:bg-gray-800 transition-colors shadow-sm cursor-pointer"
              >
                ⚙️ Panel admin
              </button>
            )}
            <button
              onClick={() => setCuentaAbierta(true)}
              className="whitespace-nowrap text-sm bg-gray-100 text-gray-700 px-3 sm:px-5 py-2.5 rounded-xl font-medium hover:bg-gray-200 transition-colors shadow-sm cursor-pointer"
            >
              👤 Mi cuenta
            </button>
            <button
              onClick={cerrarSesion}
              className="whitespace-nowrap text-sm bg-red-50 text-red-600 px-3 sm:px-5 py-2.5 rounded-xl font-medium hover:bg-red-100 transition-colors shadow-sm cursor-pointer"
            >
              Cerrar sesión
            </button>
          </div>
        </header>

        {/* SELECTOR DE CURSO (solo si está matriculado en varios) */}
        {!cargandoTemas && !errorTemas && (
          <SelectorCurso grupos={grupos} activo={grupoActivo?.id} onCambiar={cambiarCurso} className="mb-6 lg:mb-8" />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">

          {/* ESTUDIAR */}
          <section aria-labelledby="titulo-estudiar" className={`lg:col-span-2 space-y-6 ${visible('estudiar')}`}>
            <h2 id="titulo-estudiar" className="sr-only">Estudiar</h2>
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
                <p className="text-gray-600 font-medium">
                  {!esStaff && (usuario?.cursos || []).length === 0
                    ? 'Tu cuenta aún no tiene cursos asignados.'
                    : 'Todavía no hay temas disponibles.'}
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  {esStaff
                    ? 'Créalos desde el Panel admin y aparecerán aquí automáticamente.'
                    : (usuario?.cursos || []).length === 0
                      ? 'Si estás matriculado en la academia, contacta con secretaría para que revisen tu matrícula.'
                      : 'Tu academia aún no ha publicado temario para tus cursos.'}
                </p>
              </div>
            ) : (
              <>
                <PersonalizaTestCard
                  nombreCurso={variosCursos ? grupoActivo?.nombre : null}
                  onAbrir={() => navigate('/personalizar', { state: { cursoId: grupoActivo?.id } })}
                />
                {errorProgreso && (
                  <div className="px-5 py-3 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-2xl flex items-center justify-between gap-3">
                    <span>No se pudo cargar tu progreso.</span>
                    <button onClick={cargarProgreso} className="font-medium underline cursor-pointer">Reintentar</button>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {temasVisibles.map((t) => (
                    <TopicProgressCard key={t.id} tema={t} progreso={progresos[String(t.id)]} />
                  ))}
                </div>
              </>
            )}

            <Suspense fallback={<div className="bg-white border border-gray-100 rounded-3xl p-8 shadow-sm"><Cargando texto="Cargando el resumen inteligente..." /></div>}>
              <ResumenIA />
            </Suspense>
          </section>

          {/* COLUMNA LATERAL: REPASO Y CLASE */}
          <div className="lg:col-span-1 space-y-6">

            <section aria-labelledby="titulo-repaso" className={`space-y-6 ${visible('repaso')}`}>
              <h2 id="titulo-repaso" className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-1">Tu progreso personal · solo lo ves tú</h2>
              <div className="bg-gray-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
                <div className="absolute -right-8 -top-8 w-32 h-32 bg-orange-500/20 rounded-full blur-2xl"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-3xl">🗂️</span>
                    <h3 className="text-xl font-bold">Mazo de Repaso</h3>
                  </div>
                  <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                    Enfréntate a tus puntos débiles. Tus fallos se guardan aquí para que los transformes en aciertos.
                  </p>
                  <button
                    onClick={() => navigate('/repaso')}
                    className="w-full py-3 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-xl transition-colors cursor-pointer shadow-lg shadow-orange-500/20"
                  >
                    Entrar al repaso ➔
                  </button>
                </div>
              </div>
              <GraficoEvolucion />
            </section>

            <section aria-labelledby="titulo-clase" className={`space-y-6 ${visible('clase')}`}>
              <h2 id="titulo-clase" className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-1">Competición de la clase</h2>
              <RankingClase cursoId={grupoActivo?.id} onAbrirCuenta={() => setCuentaAbierta(true)} />
              <div className="p-6 bg-orange-500 rounded-3xl text-white shadow-lg shadow-orange-500/20">
                <h4 className="font-bold mb-2 flex items-center gap-2">💡 Consejo del día</h4>
                <p className="text-sm opacity-90 leading-relaxed">{consejoDelDia}</p>
              </div>
            </section>

          </div>
        </div>
      </div>

      {/* BARRA DE NAVEGACIÓN INFERIOR (móvil y tablet) */}
      <nav
        aria-label="Secciones"
        className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur border-t border-gray-200"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div role="tablist" className="max-w-md mx-auto grid grid-cols-3">
          {SECCIONES.map((s) => {
            const activa = seccion === s.id;
            return (
              <button
                key={s.id}
                role="tab"
                aria-selected={activa}
                onClick={() => cambiarSeccion(s.id)}
                className={`py-2.5 flex flex-col items-center gap-0.5 text-xs font-medium cursor-pointer transition-colors ${activa ? 'text-orange-600' : 'text-gray-500 hover:text-gray-800'}`}
              >
                <span className={`text-xl leading-none ${activa ? '' : 'grayscale opacity-70'}`} aria-hidden="true">{s.icono}</span>
                {s.texto}
              </button>
            );
          })}
        </div>
      </nav>

      {cuentaAbierta && <MiCuenta onCerrar={() => setCuentaAbierta(false)} />}
    </div>
  );
}
