import IndicadorProgreso from '../components/IndicadorProgreso';

export default function PanelAlumno() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Tus Temas</h1>
      
      <IndicadorProgreso temaId={1} />
      
    </div>
  );
}