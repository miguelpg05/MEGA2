import React from 'react';

// Red de seguridad: si un componente falla al pintarse, en lugar de dejar la
// pantalla en blanco mostramos un aviso con opciones para seguir. `resetKey`
// (la ruta actual) permite recuperarse al navegar a otra pantalla.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Error no controlado en la interfaz:', error, info?.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 font-sans">
        <div role="alert" className="max-w-md w-full bg-white rounded-3xl p-8 shadow-sm border border-gray-100 text-center">
          <div className="text-5xl mb-4" aria-hidden="true">😵</div>
          <h1 className="text-xl font-bold text-gray-800">Algo ha salido mal</h1>
          <p className="text-gray-500 mt-2">
            Ha ocurrido un error inesperado en esta pantalla. Tus resultados ya guardados no se han perdido.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-6">
            <button
              onClick={() => window.location.reload()}
              className="flex-1 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl font-semibold transition-colors cursor-pointer"
            >
              Recargar la página
            </button>
            <a
              href="/"
              className="flex-1 py-3 bg-white border border-gray-200 text-gray-700 rounded-2xl font-semibold hover:border-orange-500 hover:text-orange-600 transition-colors"
            >
              Ir al inicio
            </a>
          </div>
        </div>
      </div>
    );
  }
}
