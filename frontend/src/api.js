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
  // No forzamos Content-Type JSON cuando el body es FormData (subida de ficheros):
  // el navegador debe poner el boundary multipart automáticamente.
  const esFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers = {
    ...(options.body && !esFormData ? { 'Content-Type': 'application/json' } : {}),
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

// Helper que devuelve el JSON ya parseado y lanza Error(detail) si la respuesta no es OK.
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'Ha ocurrido un error en la petición.');
  }
  return data;
}
