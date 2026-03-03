import { useState, useEffect } from 'react';

export default function IndicadorProgreso({ alumnoId, temaId }) {
    const [progreso, setProgreso] = useState(null);
    const [cargando, setCargando] = useState(true);

    useEffect(() => {
        // Llamamos al endpoint que acabamos de crear en FastAPI
        // (Asegúrate de que el puerto 8000 coincida con tu backend)
        fetch(`http://localhost:8000/api/progreso/alumno/${alumnoId}/tema/${temaId}`)
            .then((respuesta) => respuesta.json())
            .then((datos) => {
                setProgreso(datos);
                setCargando(false);
            })
            .catch((error) => {
                console.error("Error al obtener el progreso:", error);
                setCargando(false);
            });
    }, [alumnoId, temaId]);

    if (cargando) return <p>Calculando tu nivel en el tema...</p>;
    if (!progreso) return <p>Error al cargar el progreso.</p>;

    // Colores dinámicos: Verde si supera el 80%, azul si aún está en proceso
    const colorBarra = progreso.superado ? '#10b981' : '#3b82f6';

    return (
        <div style={{
            fontFamily: 'sans-serif',
            backgroundColor: '#f9fafb',
            padding: '20px',
            borderRadius: '12px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
            maxWidth: '400px',
            margin: '20px 0'
        }}>
            {/* El texto exacto que pide el indicador */}
            <p style={{ fontWeight: '600', color: '#374151', margin: '0 0 12px 0' }}>
                {progreso.indicador_texto}
            </p>
            
            {/* Contenedor fondo de la barra */}
            <div style={{ width: '100%', backgroundColor: '#e5e7eb', borderRadius: '999px', height: '16px' }}>
                {/* La barra de progreso real que se llena y se anima */}
                <div style={{
                    width: `${progreso.porcentaje_actual}%`,
                    backgroundColor: colorBarra,
                    height: '100%',
                    borderRadius: '999px',
                    transition: 'width 0.8s ease-in-out'
                }}></div>
            </div>
            
            {/* Mensaje extra motivacional opcional */}
            {progreso.superado && (
                <p style={{ color: '#10b981', fontSize: '0.875rem', marginTop: '12px', marginBottom: '0' }}>
                    ¡Nivel objetivo alcanzado! Sigue así.
                </p>
            )}
        </div>
    );
}