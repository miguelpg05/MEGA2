import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../api';
import { GOOGLE_CLIENT_ID } from '../config';
import { useAuth } from '../auth/AuthContext';

export default function Auth() {
  const [error, setError] = useState('');
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
    // Refrescamos el contexto de auth (valida /me y carga el usuario) antes de entrar,
    // para que el vigilante de rutas no nos rebote al login por no tener usuario aún.
    await recargar();
    navigate('/');
  };

  const handleGoogleCredential = async (respuestaGoogle) => {
    setError('');
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

  // Mantenemos siempre la versión más reciente del callback sin tener que
  // reinicializar el botón de Google en cada render.
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
        // Ancho adaptativo: medimos el contenedor y lo limitamos al máximo de
        // Google (400px). Así el botón nunca desborda en móviles estrechos (<360px).
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
            <div className="flex justify-center mb-6">
              <div ref={googleBtnRef}></div>
            </div>
            <p className="text-center text-xs text-gray-400">
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
