import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function TestListado() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // 1. Rescatamos qué tema ha pulsado el usuario y su ID real
  const temaIdSeleccionado = location.state?.temaId || 1;
  const usuarioId = localStorage.getItem('usuario_id');

  const [listadoTests, setListadoTests] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    // 2. Pedimos a FastAPI solo los tests de este tema y de este usuario
    fetch(`https://backend-academia-kxx5.onrender.com/api/test/listado-progreso?alumno_id=${usuarioId}&tema_id=${temaIdSeleccionado}`)
      .then(res => res.json())
      .then(datos => {
        setListadoTests(datos);
        setCargando(false);
      })
      .catch(error => {
        console.error("Error al cargar listado:", error);
        setCargando(false);
      });
  }, [usuarioId, temaIdSeleccionado]);

  const obtenerColorIndicador = (fallos) => {
    if (fallos === null) return "bg-gray-100"; // Nunca realizado
    if (fallos <= 2) return "bg-[#bef264]"; // Aprobado
    return "bg-[#f87171]"; // Suspendido
  };

  const formatearFecha = (fechaRaw) => {
    if (!fechaRaw) return '-';
    return new Date(fechaRaw).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  if (cargando) {
    return <div className="p-8 text-center text-orange-500 font-medium animate-pulse">Cargando tu historial de tests...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 overflow-x-auto">
        
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">
              Banco de Tests {temaIdSeleccionado === 1 ? '(Tema 1)' : '(Tema 2)'}
            </h1>
            <p className="text-gray-500 mt-1">Tests de 10 preguntas. Controla tu progreso.</p>
          </div>
          <button 
            onClick={() => navigate('/')}
            className="text-sm bg-gray-100 text-gray-600 px-5 py-2.5 rounded-xl hover:bg-gray-200 transition-colors cursor-pointer"
          >
            ← Volver al Dashboard
          </button>
        </header>

        <table className="w-full text-sm text-left border-collapse">
          <thead className="text-white uppercase text-xs font-bold tracking-wider bg-[#3081ba]">
            <tr>
              <th scope="col" className="px-6 py-4 rounded-l-2xl text-center">Test</th>
              <th scope="col" className="px-6 py-4 text-center">Fallos</th>
              <th scope="col" className="px-6 py-4 text-center">Realizado</th>
              <th scope="col" className="px-6 py-4 text-center">Último</th>
              <th scope="col" className="px-6 py-4 rounded-r-2xl"></th>
            </tr>
          </thead>
          <tbody>
            {listadoTests.map((test, index) => (
              <tr 
                key={test.test_id} 
                className={`border-b border-gray-100 ${index % 2 === 0 ? 'bg-[#515254] text-white' : 'bg-white'}`}
              >
                <td className="px-6 py-4 font-bold text-xl text-center">{test.numero_test}</td>
                
                <td className="px-6 py-4 flex items-center justify-center gap-4">
                  <div className={`w-8 h-8 rounded ${obtenerColorIndicador(test.fallos_ultimo)}`}></div>
                  <span className="font-bold text-xl">{test.fallos_ultimo === null ? '-' : test.fallos_ultimo}</span>
                </td>
                
                <td className="px-6 py-4 font-medium text-lg text-center">{test.realizado_veces} veces</td>
                <td className="px-6 py-4 text-lg text-center">{formatearFecha(test.ultimo_fecha)}</td>
                
                <td className="px-6 py-4 text-center">
                  {/* 3. El botón flecha ahora redirige al test */}
                  <button 
                    onClick={() => navigate('/test', { state: { temaId: temaIdSeleccionado, testPlantillaId: test.test_id } })}
                    className="text-3xl font-bold cursor-pointer hover:text-orange-500 transition-colors"
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