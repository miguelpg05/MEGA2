import IndicadorProgreso from '../components/IndicadorProgreso';

export default function PanelAlumno() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Tus Temas</h1>
      
      {/* Pasamos los IDs reales de prueba que tengas en tu base de datos */}
      <IndicadorProgreso alumnoId={1} temaId={1} />
      
    </div>
  );
}