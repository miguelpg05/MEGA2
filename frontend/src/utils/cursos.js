// Utilidades para alumnos matriculados en VARIOS cursos.

const CLAVE_CURSO_ACTIVO = 'curso_activo';
export const SIN_CURSO = 'general';

// Agrupa los temas (de /api/temas) por curso, conservando el orden de llegada.
// Los temas sin curso asignado van al final en el grupo "General".
export function agruparPorCurso(temas) {
  const grupos = new Map();
  for (const t of temas || []) {
    const clave = t.curso_id ?? SIN_CURSO;
    if (!grupos.has(clave)) {
      grupos.set(clave, { id: clave, nombre: t.curso || 'General', temas: [] });
    }
    grupos.get(clave).temas.push(t);
  }
  const lista = [...grupos.values()];
  return [...lista.filter((g) => g.id !== SIN_CURSO), ...lista.filter((g) => g.id === SIN_CURSO)];
}

// Curso activo recordado en este navegador (comodidad; puede no estar disponible).
export function leerCursoActivo() {
  try {
    return localStorage.getItem(CLAVE_CURSO_ACTIVO);
  } catch {
    return null;
  }
}

export function guardarCursoActivo(id) {
  try {
    localStorage.setItem(CLAVE_CURSO_ACTIVO, String(id));
  } catch {
    // Sin almacenamiento: simplemente no se recuerda
  }
}

// Devuelve el grupo a mostrar: el pedido si existe, si no el recordado, si no el primero.
export function resolverGrupo(grupos, preferido) {
  if (!grupos.length) return null;
  const buscar = (id) => (id == null ? null : grupos.find((g) => String(g.id) === String(id)));
  return buscar(preferido) || buscar(leerCursoActivo()) || grupos[0];
}
