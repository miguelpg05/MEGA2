import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Presentación "de apuntes" para el Markdown que genera la IA: secciones
// numeradas, tablas, citas de artículos destacadas, índice y una tarjeta final
// con las «Claves para recordar». No usa @tailwindcss/typography: cada elemento
// lleva sus propias clases.

const RE_CLAVES = /^#{1,3}\s*(?:🔑\s*)?claves para recordar.*$/im;

const textoDe = (children) => {
  if (children == null || typeof children === 'boolean') return '';
  if (typeof children === 'string' || typeof children === 'number') return String(children);
  if (Array.isArray(children)) return children.map(textoDe).join('');
  return textoDe(children.props?.children);
};

const limpiarMarkdown = (t) => t.replace(/[*_`]/g, '').trim();

const slug = (t) =>
  limpiarMarkdown(t)
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const Encabezado = ({ children }) => {
  const texto = textoDe(children);
  const m = texto.match(/^(\d+)[.)-]?\s+(.*)$/);
  return (
    <h2 id={`sec-${slug(texto)}`} className="scroll-mt-28 flex items-start gap-3 text-lg sm:text-xl font-bold text-gray-900 mt-10 first:mt-2 mb-4 pb-3 border-b-2 border-orange-100">
      {m ? (
        <>
          <span className="shrink-0 w-8 h-8 rounded-xl bg-orange-500 text-white text-sm font-bold flex items-center justify-center shadow-sm shadow-orange-500/30">{m[1]}</span>
          <span className="pt-0.5">{m[2]}</span>
        </>
      ) : children}
    </h2>
  );
};

const base = {
  h1: Encabezado,
  h2: Encabezado,
  h3: ({ children }) => (
    <h3 className="flex items-center gap-2 text-base font-semibold text-orange-700 mt-6 mb-2">
      <span className="w-1.5 h-5 rounded-full bg-orange-400" aria-hidden="true" />
      {children}
    </h3>
  ),
  h4: ({ children }) => <h4 className="font-semibold text-gray-800 mt-4 mb-1">{children}</h4>,
  p: ({ children }) => <p className="my-3 leading-relaxed text-gray-700">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-gray-900 bg-orange-50 px-1 rounded">{children}</strong>,
  em: ({ children }) => <em className="text-gray-600">{children}</em>,
  ul: ({ children }) => (
    <ul className="my-3 space-y-2 [&>li]:relative [&>li]:pl-6 [&>li]:before:content-[''] [&>li]:before:absolute [&>li]:before:left-1.5 [&>li]:before:top-[0.6em] [&>li]:before:w-2 [&>li]:before:h-2 [&>li]:before:rounded-full [&>li]:before:bg-orange-400">
      {children}
    </ul>
  ),
  ol: ({ children }) => <ol className="my-3 space-y-2 list-decimal pl-6 marker:text-orange-500 marker:font-semibold">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed text-gray-700 [&>p]:my-1">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-5 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-gray-800 [&_p]:my-1 [&_strong]:bg-transparent [&_strong]:text-amber-800 [&_strong]:px-0">
      <span className="text-xl leading-7" aria-hidden="true">📜</span>
      <div className="min-w-0">{children}</div>
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="my-5 overflow-x-auto rounded-2xl border border-gray-200 shadow-sm">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-orange-50 text-orange-800">{children}</thead>,
  tr: ({ children }) => <tr className="even:bg-gray-50/70">{children}</tr>,
  th: ({ children }) => <th className="px-4 py-2.5 text-left font-semibold whitespace-nowrap">{children}</th>,
  td: ({ children }) => <td className="px-4 py-2.5 align-top border-t border-gray-100 text-gray-700 [&_strong]:bg-transparent [&_strong]:px-0">{children}</td>,
  code: ({ children }) => <code className="px-1.5 py-0.5 rounded bg-gray-100 text-[0.9em] text-gray-800">{children}</code>,
  hr: () => <hr className="my-8 border-gray-100" />,
  a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-orange-600 underline">{children}</a>,
};

const componentesClaves = {
  ...base,
  h1: () => null,
  h2: () => null,
  h3: () => null,
  ul: ({ children }) => <ul className="grid gap-2.5 sm:grid-cols-2">{children}</ul>,
  ol: ({ children }) => <ol className="grid gap-2.5 sm:grid-cols-2">{children}</ol>,
  li: ({ children }) => (
    <li className="flex gap-2.5 items-start rounded-xl bg-white/80 border border-orange-100 px-3 py-2.5 text-gray-800 leading-snug [&>p]:my-0">
      <span className="shrink-0 w-5 h-5 mt-0.5 rounded-full bg-orange-500 text-white text-xs font-bold flex items-center justify-center" aria-hidden="true">✓</span>
      <div className="min-w-0">{children}</div>
    </li>
  ),
  p: ({ children }) => <p className="my-2 text-gray-700">{children}</p>,
};

export default function ApuntesMarkdown({ markdown }) {
  const texto = markdown || '';
  const corte = texto.search(RE_CLAVES);
  const cuerpo = corte >= 0 ? texto.slice(0, corte) : texto;
  const claves = corte >= 0 ? texto.slice(corte).replace(RE_CLAVES, '').trim() : '';

  const indice = [...cuerpo.matchAll(/^#{1,2}\s+(.+)$/gm)].map((m) => limpiarMarkdown(m[1]));

  const irA = (titulo) => {
    document.getElementById(`sec-${slug(titulo)}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div>
      {indice.length > 1 && (
        <nav className="mb-6 rounded-2xl bg-gray-50 border border-gray-100 p-4" aria-label="Índice del resumen">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Índice</p>
          <div className="flex flex-wrap gap-2">
            {indice.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => irA(t)}
                className="text-sm px-3 py-1.5 rounded-full bg-white border border-gray-200 text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-colors cursor-pointer"
              >
                {t}
              </button>
            ))}
          </div>
        </nav>
      )}

      <ReactMarkdown remarkPlugins={[remarkGfm]} components={base}>{cuerpo}</ReactMarkdown>

      {claves && (
        <section className="mt-10 rounded-3xl border border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50 p-5 sm:p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-orange-800 mb-4">
            <span aria-hidden="true">🔑</span> Claves para recordar
          </h2>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={componentesClaves}>{claves}</ReactMarkdown>
        </section>
      )}
    </div>
  );
}
