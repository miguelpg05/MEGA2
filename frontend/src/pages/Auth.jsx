import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Auth() {
  const [esLogin, setEsLogin] = useState(true);
  const [formData, setFormData] = useState({ nombre: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const navigate = useNavigate();

  // ATENCIÓN: Si vas a subir esto a Vercel, recuerda cambiar esta URL por la de tu Render
  const BASE_URL = 'https://web-mega-flax.vercel.app/';

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
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Error en la autenticación");
      }

      if (esLogin) {
        // ¡LOGIN EXITOSO! Guardamos la "pulsera" y los datos en el navegador
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('usuario_id', data.usuario_id);
        localStorage.setItem('nombre_usuario', data.nombre);
        
        // Lo mandamos directo a su panel personal
        navigate('/');
      } else {
        // ¡REGISTRO EXITOSO!
        setMensaje("¡Cuenta creada! Ya puedes iniciar sesión.");
        setEsLogin(true); // Lo pasamos a la pantalla de login
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-[2rem] shadow-xl p-8 border border-gray-100">
        
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🏛️</div>
          <h2 className="text-2xl font-bold text-gray-800">
            {esLogin ? 'Bienvenido a tu Academia' : 'Comienza tu preparación'}
          </h2>
          <p className="text-gray-500 mt-2">
            {esLogin ? 'Inicia sesión para continuar tu progreso' : 'Crea tu cuenta y personaliza tu estudio'}
          </p>
        </div>

        {error && <div className="bg-red-50 text-red-600 p-3 rounded-xl text-sm mb-4 text-center">{error}</div>}
        {mensaje && <div className="bg-green-50 text-green-600 p-3 rounded-xl text-sm mb-4 text-center">{mensaje}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!esLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre o Alias</label>
              <input 
                type="text" name="nombre" required={!esLogin}
                className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                placeholder="Ej: Opositor123"
                onChange={handleChange}
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
            <input 
              type="email" name="email" required
              className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
              placeholder="tu@email.com"
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input 
              type="password" name="password" required
              className="w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:ring-2 focus:ring-orange-500 outline-none transition-all"
              placeholder="••••••••"
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

        <div className="mt-8 text-center text-sm text-gray-500">
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