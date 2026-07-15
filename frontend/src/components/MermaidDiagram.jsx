import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

// 1. Inicialización básica y segura
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
});

export default function MermaidDiagram({ code }) {
  const contenedorRef = useRef(null);

  useEffect(() => {
    if (!code || !contenedorRef.current) return;

    // Limpiamos cualquier gráfico anterior e inyectamos el código crudo
    contenedorRef.current.removeAttribute('data-processed');
    contenedorRef.current.innerHTML = code;

    try {
      mermaid.run({ nodes: [contenedorRef.current] })
        .then(() => {
          // Dejamos que el SVG conserve su tamaño natural para que, en móvil,
          // el contenedor haga scroll horizontal en lugar de comprimir el diagrama
          // hasta hacerlo ilegible.
          const svg = contenedorRef.current?.querySelector('svg');
          if (svg) {
            svg.style.maxWidth = 'none';
            svg.style.height = 'auto';
          }
        })
        .catch((err) => {
          console.warn('Error de sintaxis de Mermaid atrapado con seguridad:', err);
        });
    } catch (error) {
      console.error('Fallo general de Mermaid:', error);
    }
  }, [code]);

  if (!code) return null;

  // Contenedor con scroll horizontal/vertical. El <pre> queda como inline-block
  // para adoptar el ancho real del diagrama y permitir el desplazamiento.
  return (
    <div className="w-full max-w-full overflow-auto p-2 sm:p-4 bg-white rounded-xl">
      <pre className="mermaid font-sans inline-block min-w-full text-center" ref={contenedorRef}>
        {code}
      </pre>
    </div>
  );
}
