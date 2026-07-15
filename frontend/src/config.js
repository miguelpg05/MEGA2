// URL base de la API. En producción/local puedes sobreescribirla definiendo
// VITE_API_URL en un archivo .env (ver frontend/.env.example).
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://mega2-mi1o.onrender.com';

// Client ID de Google OAuth para "Iniciar sesión con Google" (ver frontend/.env.example).
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
