import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiFetch } from '../api';

export default function TestListado() {
  const navigate = useNavigate();
  const location = useLocation();

  const temaIdSeleccionado = location.state?.temaId || 1;

  const [listadoTests, setListadoTests] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    apiFetch(`/api/test/listado-progreso?tema_id=${temaIdSeleccionado}`)
      .then(res => res.json())
      .then(datos => {
        setListadoTests(datos);
        setCargando(false);
      })
      .catch(error => {
        console.error("Error al cargar listado:", error);
        setCargando(false);
      });
  }, [temaIdSeleccionado]);

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
    return <div className="p-8 text-center text-orange-500 font-medium animate-pulse">Cargando tu historial de tests...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans">
      {/* AQUÍ ESTÁ EL CAMBIO: max-w-3xl en lugar de max-w-4xl para estrecharlo más */}
      <div className="max-w-3xl mx-auto bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 overflow-x-auto">
        
        <header className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              Banco de Tests {temaIdSeleccionado === 1 ? '(Tema 1)' : '(Tema 2)'}
            </h1>
            <p className="text-gray-500 text-sm mt-1">Tests de 10 preguntas. Controla tu progreso.</p>
          </div>
          <button 
            onClick={() => navigate('/')}
            className="text-sm bg-gray-100 text-gray-600 px-4 py-2 rounded-xl hover:bg-gray-200 transition-colors cursor-pointer"
          >
            ← Volver
          </button>
        </header>

        <table className="w-full text-left border-collapse">
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
                {/* Tamaños mantenidos tal y como pediste */}
                <td className="px-4 py-3 font-bold text-lg text-center">{test.numero_test}</td>
                
                <td className="px-4 py-3 flex items-center justify-center gap-3">
                  <div className={`w-6 h-6 rounded ${obtenerColorIndicador(test.fallos_ultimo)}`}></div>
                  <span className="font-bold text-lg">{test.fallos_ultimo === null ? '-' : test.fallos_ultimo}</span>
                </td>
                
                <td className="px-4 py-3 font-medium text-sm text-center">{test.realizado_veces} veces</td>
                <td className="px-4 py-3 text-sm text-center">{formatearFecha(test.ultimo_fecha)}</td>
                
                <td className="px-4 py-3 text-center">
                  <button 
                    onClick={() => navigate('/test', { state: { temaId: temaIdSeleccionado, testPlantillaId: test.test_id } })}
                    className="text-2xl font-bold cursor-pointer hover:text-orange-500 transition-colors"
                  >
                    ›
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}