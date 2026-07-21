import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../api';
import { GOOGLE_CLIENT_ID } from '../config';
import { useAuth } from '../auth/AuthContext';

export default function Auth() {
  const [esLogin, setEsLogin] = useState(true);
  const [formData, setFormData] = useState({ nombre: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
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

  // --- Login con Google (OAuth2 con selector de cuenta forzado) ---
  const enviarTokenAlBackend = async (accessToken) => {
    setError('');
    setMensaje('');
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

  const enviarTokenRef = useRef(enviarTokenAlBackend);
  enviarTokenRef.current = enviarTokenAlBackend;

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
    setMensaje('');
    if (tokenClientRef.current) {
      tokenClientRef.current.requestAccessToken();
    } else {
      setError('Google todavía se está cargando. Espera un momento e inténtalo de nuevo.');
    }
  };

  // --- Login/registro con email + contraseña ---
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    setCargando(true);

    const endpoint = esLogin ? '/api/auth/login' : '/api/auth/registro';
    const body = esLogin
      ? { email: formData.email, password: formData.password }
      : { nombre: formData.nombre, email: formData.email, password: formData.password };

    try {
      const response = await apiFetch(endpoint, { method: 'POST', body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error en la autenticación');

      if (esLogin) {
        await guardarSesionYEntrar(data);
      } else {
        setMensaje('¡Cuenta creada! Ya puedes iniciar sesión.');
        setEsLogin(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-[2rem] shadow-xl p-6 sm:p-8 border border-gray-100">

        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🏛️</div>
          <h2 className="text-2xl font-bold text-gray-800">
            {esLogin ? 'Bienvenido a tu Academia' : 'Comienza tu preparación'}
          </h2>
          <p className="text-gray-500 mt-2">
            {esLogin ? 'Accede con tu cuenta de la academia' : 'Crea tu cuenta con tu correo de la academia'}
          </p>
        </div>

        {error && <div className="bg-red-50 text-red-600 p-3 rounded-xl text-sm mb-4 text-center">{error}</div>}
        {mensaje && <div className="bg-green-50 text-green-600 p-3 rounded-xl text-sm mb-4 text-center">{mensaje}</div>}

        {GOOGLE_CLIENT_ID && (
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

            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-gray-200"></div>
              <span className="text-xs text-gray-400 uppercase tracking-wide">o con tu email</span>
              <div className="flex-1 h-px bg-gray-200"></div>
            </div>
          </>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!esLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre o Alias</label>
              <input
                type="text" name="nombre" required={!esLogin}
                className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                placeholder="Ej: Opositor123"
                value={formData.nombre}
                onChange={handleChange}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
            <input
              type="email" name="email" required
              className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
              placeholder="tu@academiamega.net"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password" name="password" required
              className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
            />
          </div>

          <button
            type="submit"
            disabled={cargando}
            className="w-full bg-orange-600 text-white font-bold py-3 rounded-xl hover:bg-orange-700 transition-colors shadow-lg shadow-orange-200 mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {esLogin ? 'Entrar' : 'Crear mi cuenta'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-6">
          Solo se admiten cuentas <span className="font-medium text-gray-500">@academiamega.net</span>
        </p>

        <div className="mt-4 text-center text-sm text-gray-500">
          {esLogin ? '¿No tienes cuenta? ' : '¿Ya tienes cuenta? '}
          <button
            onClick={() => { setEsLogin(!esLogin); setError(''); setMensaje(''); }}
            className="text-orange-600 font-bold hover:underline"
          >
            {esLogin ? 'Regístrate aquí' : 'Inicia sesión'}
          </button>
        </div>

      </div>
    </div>
  );
}
