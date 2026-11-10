import React from 'react';
import { Link } from 'react-router-dom';
import { useTituloPagina } from '../utils/titulo';

// BORRADOR de política de privacidad, redactado a partir de lo que hace la plataforma.
// La academia (responsable del tratamiento) debe revisarlo con su asesor legal y
// completar los datos entre corchetes. Si publica la política en su web, basta con
// definir VITE_URL_PRIVACIDAD y los enlaces irán allí.

const Seccion = ({ titulo, children }) => (
  <section className="mt-8">
    <h2 className="text-lg font-semibold text-gray-800">{titulo}</h2>
    <div className="mt-2 space-y-2 text-gray-600 leading-relaxed text-sm sm:text-base">{children}</div>
  </section>
);

export default function Privacidad() {
  useTituloPagina('Política de privacidad');
  return (
    <div className="min-h-screen bg-gray-50 py-8 sm:py-12 px-4 font-sans">
      <article className="max-w-3xl mx-auto bg-white rounded-3xl border border-gray-100 shadow-sm p-6 sm:p-10">
        <Link to="/" className="text-sm text-gray-400 hover:text-gray-600">← Volver</Link>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mt-4">Política de privacidad de la plataforma</h1>
        <p className="mt-3 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3">
          Borrador pendiente de revisión legal por Academia MEGA. Versión 2026-11.
        </p>

        <Seccion titulo="1. Responsable del tratamiento">
          <p>Academia MEGA — [razón social, NIF y dirección postal]. Contacto para protección de datos: [correo de contacto].</p>
        </Seccion>

        <Seccion titulo="2. Qué datos tratamos">
          <ul className="list-disc pl-5 space-y-1">
            <li>Identificación: nombre y apellidos y correo electrónico de la academia (@academiamega.net).</li>
            <li>Matrícula: cursos en los que estás inscrito (los facilita la secretaría de la academia).</li>
            <li>Actividad de estudio: tests realizados, respuestas, notas, fallos pendientes de repaso y fecha de cada intento.</li>
            <li>Uso del resumen con IA: fecha de cada uso y el texto que decidas pegar para resumir.</li>
            <li>Datos técnicos de sesión necesarios para mantenerte conectado de forma segura.</li>
          </ul>
          <p>No tratamos tu DNI ni datos de categorías especiales.</p>
        </Seccion>

        <Seccion titulo="3. Para qué los usamos y con qué base legal">
          <ul className="list-disc pl-5 space-y-1">
            <li>Prestarte el servicio de formación: tests, correcciones, progreso por tema y mazo de repaso. Base: ejecución del contrato de formación con la academia. [A validar]</li>
            <li>Ranking de tu clase: tus compañeros ven tu nombre e inicial del apellido y tus puntos. Puedes ocultarte cuando quieras desde «Mi cuenta». Base: [interés legítimo / consentimiento — a validar].</li>
            <li>Seguimiento docente por parte del profesorado de tus cursos.</li>
            <li>Seguridad de la plataforma y prevención de abusos.</li>
          </ul>
        </Seccion>

        <Seccion titulo="4. Quién trata los datos por cuenta de la academia">
          <p>Para prestar el servicio se utilizan estos proveedores (encargados del tratamiento):</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Google (inicio de sesión con la cuenta de la academia).</li>
            <li>Vercel (alojamiento de la web) y Render (servidor de la aplicación).</li>
            <li>Neon (base de datos, cifrada en reposo).</li>
            <li>Groq (generación de resúmenes con IA): recibe el texto del temario o el que tú pegues, no tus datos de identificación.</li>
          </ul>
          <p>[Indicar la ubicación de los servidores y, si hay transferencias fuera del Espacio Económico Europeo, las garantías aplicables.]</p>
        </Seccion>

        <Seccion titulo="5. Cuánto tiempo los conservamos">
          <p>Mientras estés matriculado en la academia y, después, [plazo a definir por la academia], salvo que solicites antes su supresión.</p>
        </Seccion>

        <Seccion titulo="6. Tus derechos">
          <p>Puedes ejercer tus derechos de acceso, rectificación, supresión, oposición, limitación y portabilidad:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Acceso y portabilidad:</strong> solicita una copia de tus datos a la secretaría de la academia.</li>
            <li><strong>Supresión:</strong> solicítala a la secretaría de la academia; se borrarán tu cuenta y todo tu historial de forma definitiva.</li>
            <li><strong>Ranking:</strong> puedes dejar de aparecer desde «Mi cuenta».</li>
          </ul>
          <p>También puedes reclamar ante la Agencia Española de Protección de Datos (www.aepd.es).</p>
        </Seccion>

        <Seccion titulo="7. Seguridad">
          <p>Las conexiones van cifradas (HTTPS/TLS), la base de datos se cifra en reposo y el acceso a los datos está limitado a cada alumno y al profesorado de sus cursos.</p>
        </Seccion>
      </article>
    </div>
  );
}
