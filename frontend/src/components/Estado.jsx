// Componentes de estado reutilizables para mantener consistentes las pantallas
// de carga y de error en toda la plataforma.

export function Cargando({ texto = 'Cargando...', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-3 text-orange-500 font-medium ${className}`}>
      <span
        className="inline-block w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"
        aria-hidden="true"
      />
      <span>{texto}</span>
    </div>
  );
}

export function PantallaCarga({ texto = 'Cargando...' }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
      <Cargando texto={texto} />
    </div>
  );
}

export function MensajeError({ texto = 'Algo ha salido mal. Inténtalo de nuevo.', onReintentar, className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-4 text-center py-8 px-4 ${className}`}>
      <span className="text-4xl" aria-hidden="true">⚠️</span>
      <p className="text-gray-600 font-medium max-w-sm">{texto}</p>
      {onReintentar && (
        <button
          onClick={onReintentar}
          className="px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-medium transition-colors cursor-pointer"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
