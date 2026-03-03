import React, { useEffect, useState } from 'react';

export default function RankingClase() {
  const [lideres, setLideres] = useState([]);

  useEffect(() => {
    // Le añadimos la hora actual a la ruta para que el navegador 
    // crea que es una dirección nueva y NUNCA use la caché
    fetch(`https://backend-academia-kxx5.onrender.com/api/ranking/clase?t=${Date.now()}`)
      .then(res => res.json())
      .then(data => setLideres(data))
      .catch(error => console.error("Error al cargar el ranking:", error));
  }, []);

  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
        🏆 Ranking de la Clase
      </h3>
      <div className="space-y-3">
        {lideres.length > 0 ? lideres.map((user, index) => (
          <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
            <div className="flex items-center gap-3">
              <span className={`w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold ${
                index === 0 ? 'bg-yellow-400 text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {index + 1}
              </span>
              <span className="text-gray-700 font-medium">{user.alumno_nombre}</span>
            </div>
            <span className="text-orange-500 font-bold">{user.puntos} pts</span>
          </div>
        )) : (
          <p className="text-gray-400 text-sm italic text-center py-4">Aún no hay puntuaciones esta semana</p>
        )}
      </div>
    </div>
  );
}