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
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const googleBtnRef = useRef(null);
  const { recargar } = useAuth();

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
    // Refrescamos el contexto de auth (valida /me y carga el usuario) antes de entrar.
    await recargar();
    navigate('/');
  };

  const handleGoogleCredential = async (respuestaGoogle) => {
    setError('');
    setMensaje('');
    try {
      const response = await apiFetch('/api/auth/google', {
        method: 'POST',
        body: JSON.stringify({ credential: respuestaGoogle.credential })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'No se pudo iniciar sesión con Google');
      }
      await guardarSesionYEntrar(data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Mantenemos siempre la versión más reciente del callback sin reinicializar el botón.
  const handleGoogleCredentialRef = useRef(handleGoogleCredential);
  handleGoogleCredentialRef.current = handleGoogleCredential;

  // Carga el botón oficial de Google (el script se incluye en index.html)
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelado = false;

    const intentarInicializar = () => {
      if (cancelado) return;
      if (window.google?.accounts?.id && googleBtnRef.current) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (respuesta) => handleGoogleCredentialRef.current(respuesta),
          hd: 'academiamega.net',
        });
        // Ancho adaptativo: nunca desborda en móviles estrechos (<360px).
        const contenedor = googleBtnRef.current.parentElement;
        const anchoDisponible = contenedor ? contenedor.offsetWidth : 320;
        const anchoBoton = Math.min(400, Math.max(200, Math.floor(anchoDisponible)));
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          width: anchoBoton,
          text: 'continue_with',
          locale: 'es',
        });
      } else {
        setTimeout(intentarInicializar, 150);
      }
    };
    intentarInicializar();

    return () => { cancelado = true; };
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');

    const endpoint = esLogin ? '/api/auth/login' : '/api/auth/registro';
    const body = esLogin
      ? { email: formData.email, password: formData.password }
      : { nombre: formData.nombre, email: formData.email, password: formData.password };

    try {
      const response = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Error en la autenticación');
      }

      if (esLogin) {
        await guardarSesionYEntrar(data);
      } else {
        setMensaje('¡Cuenta creada! Ya puedes iniciar sesión.');
        setEsLogin(true);
      }
    } catch (err) {
      setError(err.message);
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
            <div className="flex justify-center mb-6">
              <div ref={googleBtnRef}></div>
            </div>
            <div className="flex items-center gap-3 mb-6">
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
            className="w-full bg-orange-600 text-white font-bold py-3 rounded-xl hover:bg-orange-700 transition-colors shadow-lg shadow-orange-200 mt-2"
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
