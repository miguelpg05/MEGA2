// URL base de la API. En producción/local puedes sobreescribirla definiendo
// VITE_API_URL en un archivo .env (ver frontend/.env.example).
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://mega2-mi1o.onrender.com';

// Client ID de Google OAuth para "Iniciar sesión con Google" (ver frontend/.env.example).
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

// Política de privacidad. Por defecto, la página interna /privacidad (borrador a
// validar por la academia). Si la academia la publica en su web, basta con definir
// VITE_URL_PRIVACIDAD con esa dirección en Vercel.
export const URL_PRIVACIDAD = import.meta.env.VITE_URL_PRIVACIDAD || '/privacidad';
export const PRIVACIDAD_EXTERNA = /^https?:\/\//.test(URL_PRIVACIDAD);
