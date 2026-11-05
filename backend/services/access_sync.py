"""Lectura del archivo exportado del Access y cálculo de la sincronización.

Funciones puras (sin base de datos) para poder probarlas a fondo:

- `leer_archivo(nombre, contenido)`  -> filas (lista de dict) desde .xlsx o .csv.
- `interpretar_filas(filas, ...)`    -> alumnos por correo + errores por fila.
- `planificar(...)`                   -> qué matrículas se dan de alta y de baja.

Formato esperado (los nombres de columna se reconocen con flexibilidad):
    Id | DNI | Nombre | Apellidos | [Correo] | Cursos
- Correo (opcional): la cuenta @academiamega.net del alumno. Si no viene, se calcula
  igual que el Access: nombre en minúsculas sin espacios ni tildes (ñ -> ny) + Id.
  Ej.: Nombre «Ana», Id 6351 -> ana6351@academiamega.net.
- Cursos: uno o varios en la misma celda, separados por «;», «,», «|» o saltos de línea.
El DNI se ignora a propósito: la plataforma no lo necesita (minimización de datos).
"""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

SEPARADORES_CURSOS = re.compile(r"[;,|\n\r]+")

# Encabezados reconocidos (ya normalizados: minúsculas, sin tildes ni signos)
COLUMNAS = {
    "access_id": {"id", "n", "no", "num", "numero", "codigo", "id alumno", "n alumno", "numero alumno", "codigo alumno"},
    "dni": {"dni", "nif", "nie", "documento", "dni nie"},
    "nombre": {"nombre", "nombre completo", "alumno", "nombre alumno", "nombre y apellidos", "apellidos y nombre"},
    "apellidos": {"apellidos", "apellido"},
    "email": {"correo", "email", "e mail", "mail", "correo electronico", "correo academia", "email academia"},
    "cursos": {"curso", "cursos", "matricula", "matriculas", "curso matriculado", "cursos matriculados"},
}


def normalizar(texto) -> str:
    """Minúsculas, sin tildes, guiones unificados y espacios simples."""
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace("–", "-").replace("—", "-")
    t = re.sub(r"\s*-\s*", " - ", t)
    return re.sub(r"\s+", " ", t).strip()


def _normalizar_encabezado(texto) -> str:
    t = normalizar(texto)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)   # «Nº» -> «n», «E-mail» -> «e mail»
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- lectura

def _filas_csv(contenido: bytes):
    texto = None
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t")
    except csv.Error:
        # (Sin modificar csv.excel, que es global: subclase con el separador elegido)
        class dialecto(csv.excel):
            delimiter = ";" if texto.count(";") > texto.count(",") else ","
    return [dict(f) for f in csv.DictReader(io.StringIO(texto), dialect=dialecto)]


def _filas_xlsx(contenido: bytes):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    filas = [f for f in wb.active.iter_rows(values_only=True)]
    filas = [f for f in filas if f and any(c not in (None, "") for c in f)]
    if not filas:
        return []
    cab = ["" if c is None else str(c) for c in filas[0]]
    return [{cab[i]: (f[i] if i < len(f) else None) for i in range(len(cab))} for f in filas[1:]]


def leer_archivo(nombre: str, contenido: bytes):
    """Devuelve las filas como lista de dict {encabezado original: valor}."""
    n = (nombre or "").lower()
    if n.endswith(".xlsx"):
        return _filas_xlsx(contenido)
    if n.endswith(".csv") or n.endswith(".txt"):
        return _filas_csv(contenido)
    raise ValueError("Formato no soportado. Exporta el Access a Excel (.xlsx) o CSV.")


# ---------------------------------------------------------- interpretación

@dataclass
class AlumnoAccess:
    email: str
    nombre: str = ""
    access_id: str = ""
    cursos: set = field(default_factory=set)        # ids de curso válidos
    con_errores: bool = False                       # alguna fila suya no se pudo interpretar


def detectar_columnas(encabezados):
    mapa = {}
    for original in encabezados:
        clave = _normalizar_encabezado(original)
        for campo, alias in COLUMNAS.items():
            if clave in alias and campo not in mapa:
                mapa[campo] = original
    return mapa


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


# Misma transformación que el control calculado del formulario del Access:
#   =Reemplazar(...Reemplazar(Minús([Nombre]);" ";"");"á";"a")...;"ñ";"ny") & [Id] & "@academiamega.net"
_REEMPLAZOS_ACCESS = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "ny"))
_LOCAL_VALIDO = re.compile(r"[a-z0-9._-]+")


def correo_desde_access(nombre, id_alumno, dominio: str = "academiamega.net") -> str:
    """Replica exactamente la fórmula del Access: nombre en minúsculas, sin espacios,
    sin tildes (á é í ó ú), ñ -> ny, seguido del Id. Ej.: («Ana», 6351) -> ana6351@academiamega.net"""
    t = _texto(nombre).lower().replace(" ", "")
    for a, b in _REEMPLAZOS_ACCESS:
        t = t.replace(a, b)
    return f"{t}{_texto(id_alumno)}@{dominio.lower()}"


def interpretar_filas(filas, cursos_por_nombre: dict, dominio: str = "academiamega.net"):
    """Agrupa las filas por correo.

    El correo se toma de la columna «Correo» si existe y tiene valor; si no, se
    calcula a partir de «Nombre» (solo el nombre, sin apellidos) e «Id», igual
    que hace el formulario del Access (ver `correo_desde_access`).

    `cursos_por_nombre`: {nombre normalizado -> id de curso} de la plataforma.
    Devuelve (alumnos: dict email -> AlumnoAccess, errores: list[str], columnas: dict).
    Una fila con un curso desconocido NO borra nada: se marca el alumno como
    `con_errores` para que la sincronización no le quite cursos por error.
    """
    if not filas:
        raise ValueError("El archivo está vacío.")
    columnas = detectar_columnas(filas[0].keys())
    puede_calcular = "nombre" in columnas and "access_id" in columnas
    faltan = []
    if "email" not in columnas and not puede_calcular:
        faltan.append("«Correo» (o las columnas «Nombre» e «Id» para calcularlo)")
    if "cursos" not in columnas:
        faltan.append("«Cursos»")
    if faltan:
        raise ValueError(
            "No encuentro la columna " + " ni la columna ".join(faltan)
            + ". Columnas del archivo: " + ", ".join(str(k) for k in filas[0].keys())
        )

    alumnos, errores = {}, []
    sufijo = "@" + dominio.lower()
    for i, fila in enumerate(filas, start=2):  # fila 1 = encabezados
        email = _texto(fila.get(columnas["email"])).lower() if "email" in columnas else ""
        cursos_txt = _texto(fila.get(columnas["cursos"]))
        nombre_pila = _texto(fila.get(columnas.get("nombre"))) if "nombre" in columnas else ""
        nombre = nombre_pila
        if "apellidos" in columnas:
            nombre = f"{nombre} {_texto(fila.get(columnas['apellidos']))}".strip()
        access_id = _texto(fila.get(columnas.get("access_id"))) if "access_id" in columnas else ""
        etiqueta = nombre or access_id or f"fila {i}"

        if not email and not cursos_txt and not nombre_pila and not access_id:
            continue  # fila vacía
        if not email and puede_calcular:
            if not nombre_pila or not access_id:
                errores.append(f"Fila {i} ({etiqueta}): faltan el Nombre o el Id para calcular el correo.")
                continue
            email = correo_desde_access(nombre_pila, access_id, dominio)
            local = email.split("@")[0]
            if not _LOCAL_VALIDO.fullmatch(local):
                errores.append(
                    f"Fila {i} ({etiqueta}): el correo calculado «{email}» tiene caracteres no válidos "
                    "(p. ej. ü, apóstrofos o tildes graves). Revisa el correo real del alumno y "
                    "añádelo en una columna «Correo»."
                )
                continue
        if not email:
            errores.append(f"Fila {i} ({etiqueta}): falta el correo.")
            continue
        if not re.fullmatch(r"[^@\s]+@[^@\s]+", email) or not email.endswith(sufijo):
            errores.append(f"Fila {i} ({etiqueta}): el correo «{email}» no es una cuenta {sufijo}.")
            continue

        alumno = alumnos.setdefault(email, AlumnoAccess(email=email))
        alumno.nombre = alumno.nombre or nombre
        alumno.access_id = alumno.access_id or access_id

        nombres_curso = [c.strip() for c in SEPARADORES_CURSOS.split(cursos_txt) if c.strip()]
        if not nombres_curso:
            errores.append(f"Fila {i} ({etiqueta}): no tiene ningún curso.")
            alumno.con_errores = True
            continue
        for nc in nombres_curso:
            curso_id = cursos_por_nombre.get(normalizar(nc))
            if curso_id is None:
                errores.append(f"Fila {i} ({etiqueta}): el curso «{nc}» no existe en la plataforma.")
                alumno.con_errores = True
            else:
                alumno.cursos.add(curso_id)
    return alumnos, errores, columnas


# -------------------------------------------------------------- planificación

def planificar(alumnos: dict, matriculas_actuales: dict, emails_gestionados: set):
    """Calcula las matrículas resultantes y los cambios.

    `matriculas_actuales`: {email -> set(curso_id)} según la última sincronización.
    `emails_gestionados`: correos de alumnos cuyos cursos ya controla el Access.
    Devuelve (deseadas: {email -> set(curso_id)}, altas: [(email, curso_id)], bajas: [(email, curso_id)]).

    Reglas:
    - El Access manda: lo que no esté en el archivo se da de baja.
    - Un alumno con alguna fila errónea conserva además sus cursos anteriores
      (no se le quita nada por un error de escritura).
    """
    deseadas = {}
    for email, al in alumnos.items():
        cursos = set(al.cursos)
        if al.con_errores:
            cursos |= matriculas_actuales.get(email, set())
        deseadas[email] = cursos

    altas, bajas = [], []
    for email in sorted(set(deseadas) | set(matriculas_actuales) | set(emails_gestionados)):
        antes = matriculas_actuales.get(email, set())
        despues = deseadas.get(email, set())
        altas += [(email, c) for c in sorted(despues - antes)]
        bajas += [(email, c) for c in sorted(antes - despues)]
    return deseadas, altas, bajas
