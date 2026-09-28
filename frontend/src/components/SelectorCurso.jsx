// Pestañas para elegir el curso activo cuando el alumno está matriculado en
// varios. Con un único curso no se muestra nada.
export default function SelectorCurso({ grupos, activo, onCambiar, className = '' }) {
  if (!grupos || grupos.length < 2) return null;
  return (
    <div className={`bg-white p-2 rounded-2xl shadow-sm border border-gray-100 ${className}`}>
      <p className="px-3 pt-1 pb-2 text-xs font-semibold text-gray-400 uppercase tracking-wide">Tus cursos</p>
      <div role="tablist" aria-label="Tus cursos" className="flex gap-2 overflow-x-auto pb-1">
        {grupos.map((g) => {
          const seleccionado = String(g.id) === String(activo);
          return (
            <button
              key={g.id}
              role="tab"
              aria-selected={seleccionado}
              onClick={() => onCambiar(g.id)}
              className={`shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors cursor-pointer flex items-center gap-2 ${seleccionado ? 'bg-orange-500 text-white shadow-md shadow-orange-500/20' : 'bg-gray-50 text-gray-600 hover:bg-orange-50 hover:text-orange-600'}`}
            >
              <span className="whitespace-nowrap">{g.nombre}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${seleccionado ? 'bg-white/20' : 'bg-white text-gray-400'}`}>
                {g.temas.length} {g.temas.length === 1 ? 'tema' : 'temas'}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
