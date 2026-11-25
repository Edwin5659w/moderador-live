"""Moderador TikTok LIVE — aplicación de escritorio.

Abre una ventana en el navegador del portátil (http://127.0.0.1:8765) con:
  - el chat del live en tiempo real
  - alertas por nivel (amarillo = silenciar, rojo = bloquear)
  - lista de usuarios para bloquear, ordenada por reincidencia
El programa NO bloquea a nadie: ustedes bloquean a mano desde TikTok.
"""
import asyncio
import csv
import json
import random
import sys
import threading
import time
import webbrowser
from collections import Counter, deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from detector import cargar_reglas, detectar, nivel_maximo

PUERTO = 8765

# Carpeta de datos: junto al .exe si está empaquetado, o junto a este archivo
if getattr(sys, "frozen", False):
    CARPETA = Path(sys.executable).parent
    RECURSOS = Path(getattr(sys, "_MEIPASS", CARPETA))
else:
    CARPETA = RECURSOS = Path(__file__).parent

ARCHIVO_PALABRAS = CARPETA / "palabras.txt"
if not ARCHIVO_PALABRAS.exists():  # primera vez con el .exe: copia la lista por defecto
    ARCHIVO_PALABRAS.write_text((RECURSOS / "palabras.txt").read_text(encoding="utf-8"), encoding="utf-8")
ARCHIVO_REGISTRO = CARPETA / "registro_alertas.csv"
HTML = (RECURSOS / "interfaz.html").read_text(encoding="utf-8")


class Estado:
    def __init__(self):
        self.lock = threading.Lock()
        self.eventos = deque(maxlen=800)
        self.seq = 0
        self.conexion = "desconectado"   # desconectado | conectando | conectado | error | demo
        self.mensaje = "Escribe el @ de la cuenta y dale Conectar (el live debe estar encendido)."
        self.cuenta = ""
        self.reglas = cargar_reglas(ARCHIVO_PALABRAS)
        self.usuarios: dict[str, dict] = {}
        self.totales = Counter()
        self.client = None
        self.loop = None
        self.demo_activo = False

    def set_estado(self, conexion, mensaje):
        with self.lock:
            self.conexion, self.mensaje = conexion, mensaje

    def reiniciar_sesion(self):
        with self.lock:
            self.usuarios.clear()
            self.totales.clear()

    def procesar(self, usuario, apodo, texto):
        hits = detectar(texto, self.reglas)
        nivel = nivel_maximo(hits)
        with self.lock:
            self.seq += 1
            self.totales["comentarios"] += 1
            ev = {"id": self.seq, "hora": datetime.now().strftime("%H:%M:%S"), "usuario": usuario,
                  "apodo": apodo, "texto": texto, "nivel": nivel,
                  "palabras": _sin_repetidas([h.palabra for h in hits]),
                  "categorias": sorted({h.categoria for h in hits})}
            if nivel != "normal":
                self.totales[nivel] += 1
                u = self.usuarios.setdefault(usuario, {"usuario": usuario, "apodo": apodo, "silenciar": 0,
                                                       "bloquear": 0, "ultimo": "", "hecho": False})
                u[nivel] += 1
                u["ultimo"] = texto
                u["apodo"] = apodo or u["apodo"]
                ev["veces"] = u["silenciar"] + u["bloquear"]
            self.eventos.append(ev)
        if nivel != "normal":
            guardar_registro(ev)

    def snapshot(self, desde):
        with self.lock:
            nuevos = [e for e in self.eventos if e["id"] > desde]
            usuarios = sorted(self.usuarios.values(), key=lambda u: (-u["bloquear"], -u["silenciar"]))
            return {"conexion": self.conexion, "mensaje": self.mensaje, "cuenta": self.cuenta,
                    "eventos": nuevos, "usuarios": usuarios, "totales": dict(self.totales),
                    "palabras": len(self.reglas)}


E = Estado()


def _sin_repetidas(palabras):
    """Si salen 'estafa' y 'estafador', deja solo la más específica."""
    unicas = sorted(set(palabras), key=len, reverse=True)
    return [p for i, p in enumerate(unicas) if not any(p in q for q in unicas[:i])]


def guardar_registro(ev):
    nuevo = not ARCHIVO_REGISTRO.exists()
    try:
        with ARCHIVO_REGISTRO.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if nuevo:
                w.writerow(["fecha", "hora", "usuario", "apodo", "comentario", "nivel", "palabras",
                            "categorias", "veces_en_este_live"])
            w.writerow([datetime.now().strftime("%Y-%m-%d"), ev["hora"], "@" + ev["usuario"], ev["apodo"],
                        ev["texto"], ev["nivel"].upper(), ", ".join(ev["palabras"]),
                        ", ".join(ev["categorias"]), ev.get("veces", "")])
    except PermissionError:
        pass  # el CSV está abierto en Excel; no tumbar la app por eso


# ------------------------------ Conexión a TikTok ------------------------------

def _datos_usuario(event):
    u = getattr(event, "user", None)
    usuario = (getattr(u, "unique_id", None) or getattr(u, "display_id", None) or "desconocido") if u else "desconocido"
    apodo = (getattr(u, "nick_name", None) or getattr(u, "nickname", None) or "") if u else ""
    return usuario, apodo


def hilo_tiktok(cuenta):
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, LiveEndEvent

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TikTokLiveClient(unique_id=cuenta)
    E.client, E.loop = client, loop

    @client.on(ConnectEvent)
    async def _con(_):
        E.set_estado("conectado", f"Conectado al live de {cuenta}. Vigilando el chat.")

    @client.on(CommentEvent)
    async def _com(event):
        texto = getattr(event, "comment", None) or getattr(event, "content", "") or ""
        usuario, apodo = _datos_usuario(event)
        E.procesar(usuario, apodo, texto)

    @client.on(LiveEndEvent)
    async def _fin(_):
        E.set_estado("desconectado", "El live terminó.")

    @client.on(DisconnectEvent)
    async def _desc(_):
        if E.conexion == "conectado":
            E.set_estado("desconectado", "Se desconectó del live.")

    try:
        loop.run_until_complete(client.connect())
        if E.conexion in ("conectando", "conectado"):
            E.set_estado("desconectado", "Conexión cerrada.")
    except Exception as ex:
        nombre = type(ex).__name__
        if "Offline" in nombre:
            msg = f"{cuenta} no está en vivo ahora. Inicien el live y vuelvan a conectar."
        elif "NotFound" in nombre:
            msg = f"No encontré la cuenta {cuenta}. Revisen el @."
        else:
            msg = f"No se pudo conectar ({nombre}). Prueben de nuevo o actualicen: pip install -U TikTokLive"
        E.set_estado("error", msg)
    finally:
        E.client = E.loop = None
        try:
            loop.close()
        except Exception:
            pass


def conectar(cuenta):
    cuenta = cuenta.strip()
    if not cuenta:
        return False, "Escribe el @ de la cuenta."
    cuenta = cuenta if cuenta.startswith("@") else "@" + cuenta
    if E.conexion in ("conectando", "conectado", "demo"):
        return False, "Ya hay una conexión activa."
    E.cuenta = cuenta
    E.reiniciar_sesion()
    E.set_estado("conectando", f"Conectando a {cuenta}...")
    threading.Thread(target=hilo_tiktok, args=(cuenta,), daemon=True).start()
    return True, ""


def desconectar():
    E.demo_activo = False
    if E.client and E.loop:
        try:
            asyncio.run_coroutine_threadsafe(E.client.disconnect(), E.loop)
        except Exception:
            pass
    E.set_estado("desconectado", "Desconectado.")


# ------------------------------ Modo demo ------------------------------

DEMO = [
    ("juancho_10", "Juancho", "qué buen análisis parce"), ("mafe.fut", "Mafe", "el Cali llega muy bien"),
    ("pipe23", "Pipe", "cuánto le apuesto al Nacional?"), ("odiador99", "Anti", "esto es una ESTAFA no le crean"),
    ("sofi_g", "Sofi", "saludos desde Pasto 🙌"), ("tipster_x", "Tips", "escríbanme al whatsapp para la fija"),
    ("odiador99", "Anti", "reporten el live gente"), ("carlos.m", "Carlos", "handicap -1?"),
    ("nadia_r", "Nadia", "la defensa del América está floja"), ("trol_01", "Trol", "eso pa qué, pura paja"),
    ("ana_belen", "Ana", "me gusta la perspectiva que dan"), ("odiador99", "Anti", "3st4f4d0r3s hp"),
    ("kevin_fc", "Kevin", "métanle en BetPlay"), ("lu_cia", "Lucía", "¿y las lesiones del Junior?"),
]


def hilo_demo():
    i = 0
    while E.demo_activo:
        u, a, t = DEMO[i % len(DEMO)]
        E.procesar(u, a, t)
        i += 1
        time.sleep(random.uniform(0.8, 1.8))


def iniciar_demo():
    if E.conexion in ("conectando", "conectado", "demo"):
        return False, "Ya hay una conexión activa."
    E.reiniciar_sesion()
    E.cuenta = "@demo"
    E.demo_activo = True
    E.set_estado("demo", "Modo demo: comentarios de prueba para ver cómo funciona.")
    threading.Thread(target=hilo_demo, daemon=True).start()
    return True, ""


# ------------------------------ Servidor web local ------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif url.path == "/api/estado":
            desde = int(parse_qs(url.query).get("desde", ["0"])[0])
            self._json(E.snapshot(desde))
        elif url.path == "/api/filtro":
            palabras = [r.palabra for r in E.reglas if r.nivel == "silenciar"]
            self._json({"palabras": palabras})
        elif url.path == "/api/registro":
            if not ARCHIVO_REGISTRO.exists():
                return self._json({"error": "Todavía no hay alertas registradas."}, 404)
            data = ARCHIVO_REGISTRO.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="registro_alertas.csv"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/conectar":
            ok, err = conectar(self._body().get("cuenta", ""))
            self._json({"ok": ok, "error": err})
        elif path == "/api/desconectar":
            desconectar()
            self._json({"ok": True})
        elif path == "/api/demo":
            ok, err = iniciar_demo()
            self._json({"ok": ok, "error": err})
        elif path == "/api/recargar":
            try:
                E.reglas = cargar_reglas(ARCHIVO_PALABRAS)
                self._json({"ok": True, "palabras": len(E.reglas)})
            except Exception as ex:
                self._json({"ok": False, "error": str(ex)})
        elif path == "/api/hecho":
            usuario = self._body().get("usuario")
            with E.lock:
                if usuario in E.usuarios:
                    E.usuarios[usuario]["hecho"] = not E.usuarios[usuario]["hecho"]
            self._json({"ok": True})
        elif path == "/api/salir":
            self._json({"ok": True})
            desconectar()
            import os
            threading.Timer(0.3, lambda: os._exit(0)).start()
        elif path == "/api/abrir-palabras":
            try:
                import os
                os.startfile(str(ARCHIVO_PALABRAS))  # Windows: abre en el Bloc de notas
                self._json({"ok": True})
            except Exception:
                self._json({"ok": False, "error": f"Abre a mano: {ARCHIVO_PALABRAS}"})
        else:
            self.send_error(404)


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PUERTO), Handler)
    except OSError:  # ya está abierto: solo abrir el navegador
        webbrowser.open(f"http://127.0.0.1:{PUERTO}")
        return
    url = f"http://127.0.0.1:{PUERTO}"
    print(f"Moderador abierto en {url}  (cierra esta ventana para salir)")
    if "--sin-navegador" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
