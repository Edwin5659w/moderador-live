"""Detección de palabras de riesgo en comentarios, con niveles.

Normaliza el texto (minúsculas, sin tildes, números "leet", letras repetidas,
letras separadas) para pillar trucos como "4PU3ST4", "a.p.u.e.s.t.a" o "apuestaaaa".
"""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

NIVELES = {"silenciar": 1, "bloquear": 2}
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


@dataclass
class Regla:
    palabra: str          # tal como la escribieron (para mostrar)
    categoria: str
    nivel: str            # "silenciar" | "bloquear"
    patron: re.Pattern


def _quitar_tildes(t: str) -> str:
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    t = _quitar_tildes(texto.lower())
    # números "leet" solo dentro de palabras con letras (no toca "2.5" ni "100%")
    t = re.sub(r"\b(?=\w*[a-z])(?=\w*[0-9@$])[\w@$]+\b", lambda m: m.group(0).translate(LEET), t)
    t = re.sub(r"([a-z])\1{2,}", r"\1", t)  # "apuestaaaa" -> "apuesta"
    # letras sueltas separadas: "a p u e s t a" / "a.p.u.e.s.t.a" -> "apuesta"
    t = re.sub(r"\b(?:[a-z][\s._\-*]+){2,}[a-z]\b", lambda m: re.sub(r"[^a-z]", "", m.group(0)), t)
    return t


def _patron(palabra_norm: str) -> re.Pattern:
    partes = [re.escape(p) for p in palabra_norm.split()]
    cuerpo = r"\s+".join(partes)
    corta = " " not in palabra_norm and len(palabra_norm) <= 4
    # palabras cortas y frases: exactas. Palabras largas: también atrapan lo que empieza igual.
    fin = r"(?![a-z0-9])" if (corta or " " in palabra_norm) else ""
    return re.compile(rf"(?<![a-z0-9]){cuerpo}{fin}")


def cargar_reglas(ruta: Path) -> list[Regla]:
    reglas: list[Regla] = []
    vistos = set()
    categoria, nivel = "general", "silenciar"
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("[") and linea.endswith("]"):
            partes = [p.strip() for p in linea[1:-1].split("|")]
            categoria = partes[0] or "general"
            nivel = partes[1].lower() if len(partes) > 1 and partes[1].lower() in NIVELES else "silenciar"
            continue
        norm = normalizar(linea)
        if norm in vistos:
            continue
        vistos.add(norm)
        reglas.append(Regla(linea, categoria, nivel, _patron(norm)))
    return reglas


def detectar(comentario: str, reglas: list[Regla]) -> list[Regla]:
    norm = normalizar(comentario)
    return [r for r in reglas if r.patron.search(norm)]


def nivel_maximo(hits: list[Regla]) -> str:
    if not hits:
        return "normal"
    return max((h.nivel for h in hits), key=lambda n: NIVELES[n])
