import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../api';
import { GOOGLE_CLIENT_ID } from '../config';
import { useAuth } from '../auth/AuthContext';

export default function Auth() {
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { recargar } = useAuth();
  const tokenClientRef = useRef(null);

  // Si nos han redirigido aquí porque la sesión se abrió en otro dispositivo, avisamos
  useEffect(() => {
    if (searchParams.get('motivo') === 'sesion_otro_dispositivo') {
      setError('Se ha cerrado tu sesión porque se ha iniciado sesión con esta cuenta en otro dispositivo.');
    }
  }, [searchParams]);

  const guardarSesionYEntrar = async (data) => {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('usuario_id', data.usuario_id);
    localStorage.setItem('nombre_usuario', data.nombre);
    await recargar();
    navigate('/');
  };

  const enviarTokenAlBackend = async (accessToken) => {
    setError('');
    setCargando(true);
    try {
      const response = await apiFetch('/api/auth/google', {
        method: 'POST',
        body: JSON.stringify({ access_token: accessToken })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo iniciar sesión con Google');
      await guardarSesionYEntrar(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  // Mantenemos la versión más reciente del callback sin reinicializar el cliente.
  const enviarTokenRef = useRef(enviarTokenAlBackend);
  enviarTokenRef.current = enviarTokenAlBackend;

  // Inicializa el cliente OAuth2 de Google con SELECTOR DE CUENTA FORZADO.
  // Así, al pulsar el botón, Google siempre muestra la pantalla para elegir/añadir
  // cuenta (metiendo email+contraseña en Google), en vez de entrar automáticamente
  // con la sesión que hubiera abierta.
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelado = false;

    const init = () => {
      if (cancelado) return;
      if (window.google?.accounts?.oauth2) {
        tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: 'openid email profile',
          prompt: 'select_account',          // siempre muestra el selector, sin auto-login
          hosted_domain: 'academiamega.net', // filtra a cuentas del dominio de la academia
          callback: (resp) => {
            if (resp && resp.access_token) {
              enviarTokenRef.current(resp.access_token);
            } else {
              setError('No se completó el inicio de sesión con Google.');
            }
          },
          error_callback: () => setError('Se canceló o falló el inicio de sesión con Google.'),
        });
      } else {
        setTimeout(init, 150);
      }
    };
    init();

    return () => { cancelado = true; };
  }, []);

  const iniciarGoogle = () => {
    setError('');
    if (tokenClientRef.current) {
      tokenClientRef.current.requestAccessToken();
    } else {
      setError('Google todavía se está cargando. Espera un momento e inténtalo de nuevo.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-[2rem] shadow-xl p-6 sm:p-8 border border-gray-100">

        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🏛️</div>
          <h2 className="text-2xl font-bold text-gray-800">Bienvenido a tu Academia</h2>
          <p className="text-gray-500 mt-2">Accede con tu cuenta de la academia para continuar</p>
        </div>

        {error && <div className="bg-red-50 text-red-600 p-3 rounded-xl text-sm mb-6 text-center">{error}</div>}

        {GOOGLE_CLIENT_ID ? (
          <>
            <button
              onClick={iniciarGoogle}
              disabled={cargando}
              className="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-3 rounded-xl transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
              </svg>
              {cargando ? 'Entrando…' : 'Continuar con Google'}
            </button>
            <p className="text-center text-xs text-gray-400 mt-6">
              Solo se admiten cuentas <span className="font-medium text-gray-500">@academiamega.net</span>
            </p>
          </>
        ) : (
          <div className="bg-amber-50 text-amber-700 p-4 rounded-xl text-sm text-center">
            El inicio de sesión con Google no está configurado. Define <code>VITE_GOOGLE_CLIENT_ID</code> en el entorno del frontend.
          </div>
        )}

      </div>
    </div>
  );
}
