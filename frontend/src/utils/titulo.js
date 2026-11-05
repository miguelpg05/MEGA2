import { useEffect } from 'react';

const BASE = 'Academia MEGA';

// Título de la pestaña del navegador: «Pantalla · Academia MEGA».
export function useTituloPagina(titulo) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · ${BASE}` : `${BASE} · Plataforma`;
  }, [titulo]);
}
