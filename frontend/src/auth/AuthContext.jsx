import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { apiFetch } from '../api';

const AuthContext = createContext(null);

// Provee el usuario autenticado REAL (validado contra el backend con /api/auth/me),
// en lugar de fiarnos del nombre guardado en localStorage (que puede quedar obsoleto
// si cambió en el servidor o si la sesión se abrió en otro dispositivo).
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  // El estado de carga inicial depende de si ya hay token: así no hacemos setState
  // síncrono dentro del efecto (buenas prácticas de React) cuando no hay sesión.
  const [cargando, setCargando] = useState(() => !!localStorage.getItem('token'));

  const recargar = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      // Sin token no hay nada que validar; el estado inicial ya refleja "sin sesión".
      return Promise.resolve();
    }
    return apiFetch('/api/auth/me')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('sesión no válida'))))
      .then((data) => {
        setUsuario(data);
        // Mantenemos localStorage sincronizado con la verdad del servidor
        localStorage.setItem('nombre_usuario', data.nombre);
        localStorage.setItem('usuario_id', data.usuario_id);
      })
      .catch(() => {
        // apiFetch ya redirige al login ante un 401 (sesión inválida / otro dispositivo)
        setUsuario(null);
      })
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    recargar();
  }, [recargar]);

  return (
    <AuthContext.Provider value={{ usuario, cargando, recargar }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  }
  return ctx;
}
