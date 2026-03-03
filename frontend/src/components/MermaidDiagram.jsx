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
    // Si no hay código o aún no existe el contenedor, esperamos
    if (!code || !contenedorRef.current) return;

    // 2. Limpiamos cualquier gráfico anterior
    contenedorRef.current.removeAttribute('data-processed');
    // Inyectamos el código crudo de texto en el contenedor
    contenedorRef.current.innerHTML = code;

    // 3. Le decimos a Mermaid: "Ve a ese contenedor y conviértelo en imagen"
    try {
      mermaid.run({
        nodes: [contenedorRef.current]
      }).catch((err) => {
        // Si la IA escribió mal el código, Mermaid lo atrapa aquí de forma segura
        console.warn("Error de sintaxis de Mermaid atrapado con seguridad:", err);
      });
    } catch (error) {
      console.error("Fallo general de Mermaid:", error);
    }

  }, [code]);

  // Si la IA aún no ha devuelto nada, no mostramos nada
  if (!code) return null;

  // 4. El contenedor clave. Usamos la clase 'mermaid' que es la nativa de la librería.
  return (
    <div className="w-full flex justify-center overflow-auto p-4 bg-white rounded-xl">
      <pre className="mermaid font-sans" ref={contenedorRef}>
        {code}
      </pre>
    </div>
  );
}