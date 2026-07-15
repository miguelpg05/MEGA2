import { API_BASE_URL } from './config';

function limpiarSesionLocal() {
  localStorage.removeItem('token');
  localStorage.removeItem('usuario_id');
  localStorage.removeItem('nombre_usuario');
}

// Wrapper de fetch: añade la cabecera Authorization automáticamente y,
// si el backend responde 401 (token inválido o sesión abierta en otro dispositivo),
// cierra la sesión local y redirige al login.
export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    limpiarSesionLocal();
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login?motivo=sesion_otro_dispositivo';
    }
    throw new Error('Sesión no válida: se ha iniciado sesión en otro dispositivo.');
  }

  return response;
}
