"""Capa de IA intercambiable por proveedor (Groq por defecto, Gemini de respaldo).

Se elige con la variable de entorno IA_PROVIDER ('groq' | 'gemini'). Groq expone
una API compatible con OpenAI, así que la llamamos con urllib (sin dependencias
extra). Toda la app usa `generar_texto(prompt)`; cambiar de proveedor es solo
cambiar variables de entorno.
"""
import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class IAError(Exception):
    """Error de IA con un mensaje apto para mostrar al usuario y un status HTTP."""
    def __init__(self, mensaje: str, status: int = 502):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status


def _proveedor() -> str:
    return (os.getenv("IA_PROVIDER") or "groq").strip().lower()


# Modelo de Groq por defecto. Groq retira modelos cada pocos meses
# (llama-3.3-70b-versatile se apagó el 16/08/2026): ver
# https://console.groq.com/docs/deprecations
MODELO_GROQ_POR_DEFECTO = "openai/gpt-oss-120b"
MODELOS_GROQ_RETIRADOS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "moonshotai/kimi-k2-instruct-0905",
}


def modelo_groq() -> str:
    """GROQ_MODEL si está definido y sigue activo; si no, el modelo por defecto."""
    modelo = (os.getenv("GROQ_MODEL") or "").strip()
    if not modelo or modelo in MODELOS_GROQ_RETIRADOS:
        return MODELO_GROQ_POR_DEFECTO
    return modelo


def _generar_groq(prompt: str, json_mode: bool, max_tokens):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise IAError("La IA no está configurada en el servidor (falta GROQ_API_KEY).", status=500)
    modelo = modelo_groq()

    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    razonador = modelo.startswith("openai/gpt-oss")
    if razonador:
        # Modelos que "piensan" antes de responder: razonamiento corto y sin
        # devolverlo (solo queremos el texto final en `content`).
        payload["reasoning_effort"] = "low"
        payload["include_reasoning"] = False
    if max_tokens:
        # El razonamiento consume tokens del mismo cupo: dejamos margen para que
        # no se corte el resumen.
        payload["max_tokens"] = max_tokens + (1024 if razonador else 0)
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Sin un User-Agent "normal", Cloudflare (que protege api.groq.com)
            # bloquea el User-Agent por defecto de urllib con un 403 (error 1010).
            "User-Agent": "Mozilla/5.0 (compatible; AcademiaMEGA/1.0)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        cuerpo = ""
        try:
            cuerpo = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        if e.code == 429:
            if "per day" in cuerpo or "TPD" in cuerpo or "RPD" in cuerpo:
                raise IAError("Se ha alcanzado el límite diario de la IA. Vuelve a intentarlo mañana.", status=429)
            raise IAError("La IA está recibiendo muchas peticiones. Espera un minuto y vuelve a intentarlo.", status=429)
        if e.code == 413:
            raise IAError("El material es demasiado largo para la IA. Prueba con menos temas o con un solo PDF.", status=413)
        raise IAError(f"La IA no respondió ({modelo}): {e.code} {cuerpo}", status=502)
    except URLError as e:
        raise IAError(f"No se pudo contactar con la IA: {e}", status=502)

    try:
        texto = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise IAError("La IA devolvió una respuesta inesperada.", status=502)
    tokens = (data.get("usage") or {}).get("total_tokens")
    return texto, tokens


def _generar_gemini(prompt: str, json_mode: bool, max_tokens):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise IAError("La IA no está configurada en el servidor (falta GEMINI_API_KEY).", status=500)
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=modelo, contents=prompt)
        texto = response.text or ""
    except IAError:
        raise
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise IAError("Se ha alcanzado el límite de la IA por ahora. Inténtalo en unos minutos.", status=429)
        raise IAError(f"La IA no respondió ({modelo}): {msg[:300]}", status=502)

    tokens = None
    meta = getattr(response, "usage_metadata", None)
    if meta is not None:
        tokens = getattr(meta, "total_token_count", None)
    return texto, tokens


def generar_texto(prompt: str, json_mode: bool = False, max_tokens: int = None):
    """Genera texto con el proveedor configurado. Devuelve (texto, tokens_totales).
    `max_tokens` limita la longitud de la respuesta (útil para respuestas extensas).
    Lanza IAError (con .mensaje y .status) si algo falla."""
    if _proveedor() == "gemini":
        return _generar_gemini(prompt, json_mode, max_tokens)
    return _generar_groq(prompt, json_mode, max_tokens)  # Groq por defecto
