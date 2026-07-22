import { API_BASE_URL } from './config';

function limpiarSesionLocal() {
  localStorage.removeItem('token');
  localStorage.removeItem('usuario_id');
  localStorage.removeItem('nombre_usuario');
}

// Error de sesión (401): no se debe reintentar, hay que ir al login.
class ErrorSesion extends Error {}

// Esperas entre reintentos ante fallos de red. El backend en Render (plan free)
// se duerme tras un rato y tarda ~50s en despertar; durante ese arranque las
// peticiones fallan con "Failed to fetch". Con estos reintentos la llamada se
// recupera sola en lugar de mostrar un error al usuario.
const ESPERAS_MS = [2000, 4000, 8000, 12000, 20000];

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Wrapper de fetch: añade la cabecera Authorization automáticamente, reintenta
// ante fallos de red y, si el backend responde 401 (token inválido o sesión
// abierta en otro dispositivo), cierra la sesión local y redirige al login.
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

  for (let intento = 0; intento <= ESPERAS_MS.length; intento++) {
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

      if (response.status === 401) {
        limpiarSesionLocal();
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login?motivo=sesion_otro_dispositivo';
        }
        throw new ErrorSesion('Sesión no válida: se ha iniciado sesión en otro dispositivo.');
      }

      return response;
    } catch (err) {
      // Un 401 gestionado no se reintenta.
      if (err instanceof ErrorSesion) throw err;
      // Fallo de red: reintentamos si aún quedan intentos.
      if (intento < ESPERAS_MS.length) {
        await esperar(ESPERAS_MS[intento]);
      }
    }
  }

  throw new Error(
    'No se pudo conectar con el servidor. Puede estar arrancando: espera unos segundos y vuelve a intentarlo.'
  );
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
