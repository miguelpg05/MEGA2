import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiFetch } from '../api';
import { PantallaCarga, MensajeError } from '../components/Estado';

export default function TestListado() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaIdSeleccionado = location.state?.temaId || null;
  const temaNombre = location.state?.temaNombre || '';

  const [listadoTests, setListadoTests] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  const cargarListado = useCallback(() => {
    apiFetch(`/api/test/listado-progreso?tema_id=${temaIdSeleccionado}`)
      .then(res => {
        if (!res.ok) throw new Error('respuesta no OK');
        return res.json();
      })
      .then(datos => {
        setListadoTests(datos);
        setError(false);
        setCargando(false);
      })
      .catch(err => {
        console.error("Error al cargar listado:", err);
        setError(true);
        setCargando(false);
      });
  }, [temaIdSeleccionado]);

  useEffect(() => {
    // Sin tema elegido (acceso directo a la URL) volvemos al inicio
    if (!temaIdSeleccionado) {
      navigate('/');
      return;
    }
    cargarListado();
  }, [temaIdSeleccionado, navigate, cargarListado]);

  const reintentar = () => {
    setCargando(true);
    setError(false);
    cargarListado();
  };

  const obtenerColorIndicador = (fallos) => {
    if (fallos === null) return "bg-gray-100"; 
    if (fallos <= 2) return "bg-[#bef264]"; 
    return "bg-[#f87171]"; 
  };

  const formatearFecha = (fechaRaw) => {
    if (!fechaRaw) return '-';
    return new Date(fechaRaw).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  if (cargando) {
    return <PantallaCarga texto="Cargando tu historial de tests..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
        <MensajeError texto="No se pudo cargar el listado de tests. Revisa tu conexión." onReintentar={reintentar} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 font-sans">
      <div className="max-w-3xl mx-auto bg-white rounded-3xl p-4 sm:p-6 md:p-8 shadow-sm border border-gray-100 overflow-x-auto">

        <header className="mb-6 flex flex-wrap justify-between items-center gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Banco de Tests</h1>
            <p className="text-gray-500 text-sm mt-1">
              {temaNombre ? <><strong className="text-gray-700">{temaNombre}</strong> · </> : null}
              Elige un test y hazlo en Modo Práctica o Modo Examen.
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm bg-gray-100 text-gray-600 px-4 py-2 rounded-xl hover:bg-gray-200 transition-colors cursor-pointer"
          >
            ← Volver
          </button>
        </header>

        {listadoTests.length === 0 && (
          <p className="text-center text-gray-400 py-10">Todavía no hay tests en este tema.</p>
        )}

        {listadoTests.length > 0 && <table className="w-full text-left border-collapse min-w-[420px]">
          {/* Cabecera Naranja */}
          <thead className="text-white uppercase text-xs font-bold tracking-wider bg-orange-500">
            <tr>
              <th scope="col" className="px-4 py-3 rounded-l-xl text-center">Test</th>
              <th scope="col" className="px-4 py-3 text-center">Fallos</th>
              <th scope="col" className="px-4 py-3 text-center">Realizado</th>
              <th scope="col" className="px-4 py-3 text-center">Último</th>
              <th scope="col" className="px-4 py-3 rounded-r-xl"></th>
            </tr>
          </thead>
          <tbody>
            {listadoTests.map((test, index) => (
              <tr 
                key={test.test_id} 
                className={`border-b border-gray-100 ${index % 2 === 0 ? 'bg-[#515254] text-white' : 'bg-white'}`}
              >
                {/* Nombre del test: admite cualquier texto (puede ser largo) */}
                <td className={`px-4 py-3 font-bold text-center break-words ${String(test.numero_test).length > 6 ? 'text-sm max-w-[180px]' : 'text-lg'}`}>
                  {test.numero_test}
                  {typeof test.num_preguntas === 'number' && (
                    <span className="block text-[11px] font-normal opacity-60">{test.num_preguntas} preguntas</span>
                  )}
                </td>
                
                <td className="px-4 py-3 flex items-center justify-center gap-3">
                  <div className={`w-6 h-6 rounded ${obtenerColorIndicador(test.fallos_ultimo)}`}></div>
                  <span className="font-bold text-lg">{test.fallos_ultimo === null ? '-' : test.fallos_ultimo}</span>
                </td>
                
                <td className="px-4 py-3 font-medium text-sm text-center">{test.realizado_veces} veces</td>
                <td className="px-4 py-3 text-sm text-center">{formatearFecha(test.ultimo_fecha)}</td>
                
                <td className="px-4 py-3 text-center">
                  <button 
                    onClick={() => navigate('/test', { state: { temaId: temaIdSeleccionado, temaNombre, testPlantillaId: test.test_id, testNombre: test.numero_test } })}
                    aria-label={`Hacer el test ${test.numero_test}`}
                    className="text-2xl font-bold cursor-pointer hover:text-orange-500 transition-colors"
                  >
                    ›
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>}
      </div>
    </div>
  );
}