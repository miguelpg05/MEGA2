import { lazy } from 'react';

const CLAVE = 'recarga_por_version_nueva';

// React.lazy con red de seguridad: tras un despliegue nuevo, los trozos (chunks)
// antiguos dejan de existir y una pestaña abierta desde antes no los encuentra.
// En ese caso recargamos la página UNA vez para obtener la versión nueva.
export function cargaDiferida(importar) {
  return lazy(() =>
    importar()
      .then((modulo) => {
        try { sessionStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ }
        return modulo;
      })
      .catch((error) => {
        let yaRecargada = false;
        try { yaRecargada = sessionStorage.getItem(CLAVE) === '1'; } catch { /* sin almacenamiento */ }
        if (!yaRecargada) {
          try { sessionStorage.setItem(CLAVE, '1'); } catch { /* sin almacenamiento */ }
          window.location.reload();
          return new Promise(() => {}); // la página se está recargando
        }
        throw error; // segundo fallo: lo muestra el ErrorBoundary
      })
  );
}
