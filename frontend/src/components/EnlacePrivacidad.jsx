import React from 'react';
import { Link } from 'react-router-dom';
import { URL_PRIVACIDAD, PRIVACIDAD_EXTERNA } from '../config';

// Enlace a la política de privacidad (página interna o la web de la academia).
export default function EnlacePrivacidad({ children = 'Política de privacidad', className = '' }) {
  const clases = `text-orange-600 hover:underline ${className}`;
  return PRIVACIDAD_EXTERNA
    ? <a href={URL_PRIVACIDAD} target="_blank" rel="noreferrer" className={clases}>{children}</a>
    : <Link to={URL_PRIVACIDAD} target="_blank" className={clases}>{children}</Link>;
}
