import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiJson } from '../api';
import { Cargando, MensajeError } from '../components/Estado';
import { useAuth } from '../auth/AuthContext';

// Tarjeta de métrica (a nivel de módulo para no recrearla en cada render)
function MetricaCard({ titulo, valor, sub }) {
  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
      <p className="text-sm text-gray-500">{titulo}</p>
      <p className="text-3xl font-bold text-gray-800 mt-1">{valor}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ==========================================
// Sección: MÉTRICAS
// ==========================================
function MetricasSection() {
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  const cargar = useCallback(() => {
    apiJson('/api/admin/metricas')
      .then((d) => { setDatos(d); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const reintentar = () => { setCargando(true); setError(false); cargar(); };

  if (cargando) return <Cargando texto="Cargando métricas..." className="py-12" />;
  if (error || !datos) return <MensajeError texto="No se pudieron cargar las métricas." onReintentar={reintentar} />;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricaCard titulo="Usuarios totales" valor={datos.usuarios_total} />
        <MetricaCard titulo="Alumnos" valor={datos.alumnos_total} />
        <MetricaCard titulo="Alumnos activos (7d)" valor={datos.alumnos_activos_7d} />
        <MetricaCard titulo="Llamadas IA (total)" valor={datos.ia.total} sub={`Hoy: ${datos.ia.hoy} · 7d: ${datos.ia.ultimos_7d} · ${datos.ia.tokens_totales} tokens`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-3">Progreso medio por tema</h3>
          {datos.progreso_por_tema.length === 0 ? (
            <p className="text-sm text-gray-400">Aún no hay respuestas registradas.</p>
          ) : (
            <div className="space-y-3">
              {datos.progreso_por_tema.map((t) => (
                <div key={t.tema_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700 truncate pr-2">{t.nombre}</span>
                    <span className="font-semibold text-gray-800">{t.porcentaje}%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-orange-500 rounded-full" style={{ width: `${t.porcentaje}%` }} />
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{t.respuestas} respuestas</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-3">Preguntas más falladas</h3>
          {datos.preguntas_mas_falladas.length === 0 ? (
            <p className="text-sm text-gray-400">Todavía no hay fallos registrados.</p>
          ) : (
            <ol className="space-y-2 list-decimal list-inside">
              {datos.preguntas_mas_falladas.map((p) => (
                <li key={p.pregunta_id} className="text-sm text-gray-700">
                  <span className="text-gray-500">({p.veces_fallada})</span> {p.enunciado}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}

// ==========================================
// Sección: TEMAS
// ==========================================
function TemasSection() {
  const [temas, setTemas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [nombre, setNombre] = useState('');
  const [bloque, setBloque] = useState('');
  const [aviso, setAviso] = useState('');

  const cargar = useCallback(() => {
    apiJson('/api/admin/temas')
      .then((d) => { setTemas(d); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const reintentar = () => { setCargando(true); setError(false); cargar(); };

  const crear = async (e) => {
    e.preventDefault();
    setAviso('');
    try {
      await apiJson('/api/admin/temas', { method: 'POST', body: JSON.stringify({ nombre, bloque }) });
      setNombre(''); setBloque('');
      cargar();
    } catch (err) { setAviso(err.message); }
  };

  const borrar = async (id) => {
    if (!window.confirm('¿Eliminar este tema?')) return;
    try { await apiJson(`/api/admin/temas/${id}`, { method: 'DELETE' }); cargar(); }
    catch (err) { setAviso(err.message); }
  };

  if (cargando) return <Cargando texto="Cargando temas..." className="py-12" />;
  if (error) return <MensajeError texto="No se pudieron cargar los temas." onReintentar={reintentar} />;

  return (
    <div className="space-y-6">
      <form onSubmit={crear} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row gap-3">
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} required placeholder="Nombre del tema"
          className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
        <input value={bloque} onChange={(e) => setBloque(e.target.value)} placeholder="Bloque (opcional)"
          className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
        <button className="px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl cursor-pointer">Crear tema</button>
      </form>
      {aviso && <p className="text-sm text-red-600">{aviso}</p>}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm divide-y divide-gray-100">
        {temas.length === 0 ? <p className="p-5 text-sm text-gray-400">No hay temas.</p> :
          temas.map((t) => (
            <div key={t.id} className="p-4 flex justify-between items-center gap-3">
              <div>
                <p className="font-medium text-gray-800">{t.nombre}</p>
                <p className="text-xs text-gray-400">ID {t.id} · {t.bloque || 'Sin bloque'}</p>
              </div>
              <button onClick={() => borrar(t.id)} className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg cursor-pointer">Eliminar</button>
            </div>
          ))}
      </div>
    </div>
  );
}

// ==========================================
// Sección: TESTS
// ==========================================
function TestsSection() {
  const [temas, setTemas] = useState([]);
  const [tests, setTests] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [numero, setNumero] = useState('');
  const [temaId, setTemaId] = useState('');
  const [aviso, setAviso] = useState('');

  const cargar = useCallback(() => {
    Promise.all([apiJson('/api/admin/temas'), apiJson('/api/admin/tests')])
      .then(([ts, tp]) => { setTemas(ts); setTests(tp); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const reintentar = () => { setCargando(true); setError(false); cargar(); };

  const crear = async (e) => {
    e.preventDefault();
    setAviso('');
    try {
      await apiJson('/api/admin/tests', {
        method: 'POST',
        body: JSON.stringify({ numero_test: numero, tema_id: Number(temaId), total_preguntas: 10 }),
      });
      setNumero(''); setTemaId('');
      cargar();
    } catch (err) { setAviso(err.message); }
  };

  const borrar = async (id) => {
    if (!window.confirm('¿Eliminar este test?')) return;
    try { await apiJson(`/api/admin/tests/${id}`, { method: 'DELETE' }); cargar(); }
    catch (err) { setAviso(err.message); }
  };

  if (cargando) return <Cargando texto="Cargando tests..." className="py-12" />;
  if (error) return <MensajeError texto="No se pudieron cargar los tests." onReintentar={reintentar} />;

  const nombreTema = (id) => temas.find((t) => t.id === id)?.nombre || `Tema ${id}`;

  return (
    <div className="space-y-6">
      <form onSubmit={crear} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row gap-3">
        <input value={numero} onChange={(e) => setNumero(e.target.value)} required placeholder="Nº de test (ej. 001)"
          className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
        <select value={temaId} onChange={(e) => setTemaId(e.target.value)} required
          className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500">
          <option value="">Selecciona tema…</option>
          {temas.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
        </select>
        <button className="px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl cursor-pointer">Crear test</button>
      </form>
      {aviso && <p className="text-sm text-red-600">{aviso}</p>}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm divide-y divide-gray-100">
        {tests.length === 0 ? <p className="p-5 text-sm text-gray-400">No hay tests.</p> :
          tests.map((t) => (
            <div key={t.id} className="p-4 flex justify-between items-center gap-3">
              <div>
                <p className="font-medium text-gray-800">Test {t.numero_test}</p>
                <p className="text-xs text-gray-400">ID {t.id} · {nombreTema(t.tema_id)}</p>
              </div>
              <button onClick={() => borrar(t.id)} className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg cursor-pointer">Eliminar</button>
            </div>
          ))}
      </div>
    </div>
  );
}

// ==========================================
// Sección: PREGUNTAS
// ==========================================
const PREGUNTA_VACIA = { enunciado: '', opcion_a: '', opcion_b: '', opcion_c: '', opcion_d: '', respuesta_correcta: 'A', explicacion: '' };

function PreguntasSection() {
  const [tests, setTests] = useState([]);
  const [testId, setTestId] = useState('');
  const [preguntas, setPreguntas] = useState([]);
  const [cargandoTests, setCargandoTests] = useState(true);
  const [error, setError] = useState(false);
  const [form, setForm] = useState(PREGUNTA_VACIA);
  const [aviso, setAviso] = useState('');
  const [importInfo, setImportInfo] = useState('');
  const fileRef = useRef(null);

  const cargarTests = useCallback(() => {
    apiJson('/api/admin/tests')
      .then((d) => { setTests(d); setError(false); setCargandoTests(false); })
      .catch(() => { setError(true); setCargandoTests(false); });
  }, []);
  useEffect(() => { cargarTests(); }, [cargarTests]);

  const cargarPreguntas = useCallback((id) => {
    if (!id) { setPreguntas([]); return; }
    apiJson(`/api/admin/preguntas?test_plantilla_id=${id}`)
      .then((d) => setPreguntas(d))
      .catch(() => setPreguntas([]));
  }, []);

  const seleccionarTest = (id) => { setTestId(id); cargarPreguntas(id); };

  const crear = async (e) => {
    e.preventDefault();
    setAviso('');
    if (!testId) { setAviso('Selecciona primero un test.'); return; }
    const test = tests.find((t) => String(t.id) === String(testId));
    try {
      await apiJson('/api/admin/preguntas', {
        method: 'POST',
        body: JSON.stringify({ ...form, tema_id: test.tema_id, test_plantilla_id: Number(testId) }),
      });
      setForm(PREGUNTA_VACIA);
      cargarPreguntas(testId);
    } catch (err) { setAviso(err.message); }
  };

  const borrar = async (id) => {
    if (!window.confirm('¿Eliminar esta pregunta?')) return;
    try { await apiJson(`/api/admin/preguntas/${id}`, { method: 'DELETE' }); cargarPreguntas(testId); }
    catch (err) { setAviso(err.message); }
  };

  const importar = async (e) => {
    const archivo = e.target.files?.[0];
    if (!archivo) return;
    setImportInfo('Importando…');
    try {
      const fd = new FormData();
      fd.append('archivo', archivo);
      const res = await apiJson('/api/admin/preguntas/importar', { method: 'POST', body: fd });
      setImportInfo(`Importadas ${res.creadas} preguntas.${res.errores.length ? ` ${res.errores.length} filas con error.` : ''}`);
      cargarTests();
      if (testId) cargarPreguntas(testId);
    } catch (err) { setImportInfo(err.message); }
    finally { if (fileRef.current) fileRef.current.value = ''; }
  };

  if (cargandoTests) return <Cargando texto="Cargando..." className="py-12" />;
  if (error) return <MensajeError texto="No se pudieron cargar los tests." onReintentar={() => { setCargandoTests(true); cargarTests(); }} />;

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center gap-3">
        <select value={testId} onChange={(e) => seleccionarTest(e.target.value)}
          className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500">
          <option value="">Selecciona un test…</option>
          {tests.map((t) => <option key={t.id} value={t.id}>Test {t.numero_test} (tema {t.tema_id})</option>)}
        </select>
        <label className="text-sm text-gray-600 cursor-pointer bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-xl">
          Importar CSV/XLSX
          <input ref={fileRef} type="file" accept=".csv,.xlsx" onChange={importar} className="hidden" />
        </label>
      </div>
      {importInfo && <p className="text-sm text-gray-600">{importInfo}</p>}

      {testId && (
        <form onSubmit={crear} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-3">
          <textarea value={form.enunciado} onChange={set('enunciado')} required placeholder="Enunciado"
            className="w-full px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" rows={2} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {['a', 'b', 'c', 'd'].map((l) => (
              <input key={l} value={form[`opcion_${l}`]} onChange={set(`opcion_${l}`)} required placeholder={`Opción ${l.toUpperCase()}`}
                className="px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
            ))}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <select value={form.respuesta_correcta} onChange={set('respuesta_correcta')}
              className="px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500">
              {['A', 'B', 'C', 'D'].map((l) => <option key={l} value={l}>Correcta: {l}</option>)}
            </select>
            <input value={form.explicacion} onChange={set('explicacion')} placeholder="Explicación (opcional)"
              className="flex-1 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200 outline-none focus:ring-2 focus:ring-orange-500" />
            <button className="px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl cursor-pointer">Añadir pregunta</button>
          </div>
          {aviso && <p className="text-sm text-red-600">{aviso}</p>}
        </form>
      )}

      {testId && (
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm divide-y divide-gray-100">
          {preguntas.length === 0 ? <p className="p-5 text-sm text-gray-400">Este test no tiene preguntas.</p> :
            preguntas.map((p) => (
              <div key={p.id} className="p-4 flex justify-between items-start gap-3">
                <div>
                  <p className="text-gray-800">{p.enunciado}</p>
                  <p className="text-xs text-gray-400 mt-1">Correcta: {p.respuesta_correcta} · ID {p.id}</p>
                </div>
                <button onClick={() => borrar(p.id)} className="shrink-0 text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg cursor-pointer">Eliminar</button>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ==========================================
// Sección: USUARIOS (solo admin)
// ==========================================
function UsuariosSection() {
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [aviso, setAviso] = useState('');

  const cargar = useCallback(() => {
    apiJson('/api/admin/usuarios')
      .then((d) => { setUsuarios(d); setError(false); setCargando(false); })
      .catch(() => { setError(true); setCargando(false); });
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const reintentar = () => { setCargando(true); setError(false); cargar(); };

  const cambiarRol = async (id, rol) => {
    setAviso('');
    try {
      await apiJson(`/api/admin/usuarios/${id}/rol`, { method: 'PUT', body: JSON.stringify({ rol }) });
      cargar();
    } catch (err) { setAviso(err.message); }
  };

  if (cargando) return <Cargando texto="Cargando usuarios..." className="py-12" />;
  if (error) return <MensajeError texto="No se pudieron cargar los usuarios." onReintentar={reintentar} />;

  return (
    <div className="space-y-4">
      {aviso && <p className="text-sm text-red-600">{aviso}</p>}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm divide-y divide-gray-100">
        {usuarios.map((u) => (
          <div key={u.id} className="p-4 flex justify-between items-center gap-3">
            <div className="min-w-0">
              <p className="font-medium text-gray-800 truncate">{u.nombre}</p>
              <p className="text-xs text-gray-400 truncate">{u.email}</p>
            </div>
            <select value={u.rol} onChange={(e) => cambiarRol(u.id, e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-orange-500">
              <option value="alumno">Alumno</option>
              <option value="profesor">Profesor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// Sección: RANKING
// ==========================================
function RankingSection({ esAdmin }) {
  const [aviso, setAviso] = useState('');

  const accion = async (path, confirmar) => {
    if (!window.confirm(confirmar)) return;
    setAviso('');
    try { const res = await apiJson(path, { method: 'DELETE' }); setAviso(res.mensaje); }
    catch (err) { setAviso(err.message); }
  };

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4 max-w-xl">
      <p className="text-gray-600 text-sm">Herramientas de mantenimiento del ranking de la clase.</p>
      <button onClick={() => accion('/api/admin/ranking/demo', '¿Eliminar las puntuaciones de demostración?')}
        className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl cursor-pointer">
        Eliminar puntuaciones de demostración
      </button>
      {esAdmin && (
        <button onClick={() => accion('/api/admin/ranking/reset', '¿Reiniciar TODO el ranking? Esto borra todas las puntuaciones.')}
          className="w-full py-2.5 bg-red-50 text-red-600 hover:bg-red-100 font-medium rounded-xl cursor-pointer">
          Reiniciar ranking completo
        </button>
      )}
      {aviso && <p className="text-sm text-gray-700">{aviso}</p>}
    </div>
  );
}

// ==========================================
// PÁGINA PRINCIPAL
// ==========================================
export default function Admin() {
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === 'admin';

  const tabsBase = ['Métricas', 'Temas', 'Tests', 'Preguntas', 'Ranking'];
  const tabs = esAdmin ? ['Métricas', 'Temas', 'Tests', 'Preguntas', 'Usuarios', 'Ranking'] : tabsBase;
  const [tab, setTab] = useState('Métricas');

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-5xl mx-auto">
        <header className="mb-6 flex flex-wrap justify-between items-center gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl font-light text-gray-900">Panel de <span className="font-semibold text-orange-500">administración</span></h1>
            <p className="text-gray-500 text-sm mt-1">Conectado como {usuario?.nombre} · {usuario?.rol}</p>
          </div>
          <button onClick={() => navigate('/')} className="text-sm bg-gray-100 text-gray-600 px-4 py-2 rounded-xl hover:bg-gray-200 cursor-pointer">← Volver</button>
        </header>

        <nav className="flex flex-wrap gap-2 mb-6">
          {tabs.map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-xl text-sm font-medium cursor-pointer transition-colors ${tab === t ? 'bg-orange-500 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:border-orange-300'}`}>
              {t}
            </button>
          ))}
        </nav>

        {tab === 'Métricas' && <MetricasSection />}
        {tab === 'Temas' && <TemasSection />}
        {tab === 'Tests' && <TestsSection />}
        {tab === 'Preguntas' && <PreguntasSection />}
        {tab === 'Usuarios' && esAdmin && <UsuariosSection />}
        {tab === 'Ranking' && <RankingSection esAdmin={esAdmin} />}
      </div>
    </div>
  );
}
