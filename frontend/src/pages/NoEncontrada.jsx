import React from 'react';
import { Link } from 'react-router-dom';

// Página 404: cualquier dirección que no existe en la plataforma.
export default function NoEncontrada() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 font-sans">
      <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-sm border border-gray-100 text-center">
        <div className="text-6xl font-black text-orange-500">404</div>
        <h1 className="text-xl font-bold text-gray-800 mt-3">Esta página no existe</h1>
        <p className="text-gray-500 mt-2">Puede que el enlace esté mal escrito o que la página se haya movido.</p>
        <Link
          to="/"
          className="inline-block mt-6 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl font-semibold transition-colors"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
