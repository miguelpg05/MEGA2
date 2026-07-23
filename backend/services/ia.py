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


def _generar_groq(prompt: str, json_mode: bool, max_tokens):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise IAError("La IA no está configurada en el servidor (falta GROQ_API_KEY).", status=500)
    modelo = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
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
            raise IAError("Se ha alcanzado el límite de la IA por ahora. Inténtalo en unos minutos.", status=429)
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
