"""Prueba la detección sin necesidad de un live:  python test_detector.py"""
from pathlib import Path
from detector import cargar_reglas, detectar, nivel_maximo

R = cargar_reglas(Path(__file__).parent / "palabras.txt")

casos = {
    # silenciar
    "cuánto le apuesto al Cali?": "silenciar",
    "dame la cuota": "silenciar",
    "4PU3ST4 segura": "silenciar",
    "a.p.u.e.s.t.a": "silenciar",
    "a p u e s t a": "silenciar",
    "apuestaaaa": "silenciar",
    "handicap -1 para el Nacional": "silenciar",
    "métanle en BetPlay": "silenciar",
    "pick seguro hoy?": "silenciar",
    "más de 2.5 goles": "silenciar",
    "escríbeme al whatsapp": "silenciar",
    "jugué una combinada": "silenciar",
    "pásenme por nequi": "silenciar",
    # bloquear
    "eso es una ESTAFA": "bloquear",
    "son unos estafadores": "bloquear",
    "esto no sirve pa nada": "bloquear",
    "eso pa qué": "bloquear",
    "vendehumo": "bloquear",
    "pura paja lo que dicen": "bloquear",
    "no le crean nada": "bloquear",
    "reporten el live": "bloquear",
    "REPORTENLO todos": "bloquear",
    "hp ladrones": "bloquear",
    "gonorreas": "bloquear",
    "me robaron la plata": "bloquear",
    "e.s.t.a.f.a": "bloquear",
    "3st4f4d0r3s": "bloquear",
    "apuesta y es una estafa": "bloquear",  # gana el nivel más alto
    # normal (no debe alertar)
    "qué buen análisis": "normal",
    "el Cali llega bien": "normal",
    "fíjate en la defensa": "normal",
    "la estadística dice otra cosa": "normal",
    "saludos desde Pasto": "normal",
    "probando el chat": "normal",
    "la defensa del Cali está regular": "normal",
    "pa que gane el América": "normal",
    "el portero fue clave": "normal",
    "ladrillo": "normal",
    "Betoven": "normal",
    "excelente reporte del partido": "normal",
    "2 a 1 gana el Nacional": "normal",
}

errores = 0
for texto, esperado in casos.items():
    hits = detectar(texto, R)
    obtenido = nivel_maximo(hits)
    if obtenido != esperado:
        errores += 1
        print(f"✗ '{texto}': esperaba {esperado}, salió {obtenido} {[h.palabra for h in hits]}")
print(f"{len(R)} palabras cargadas. " + ("Todo OK ✓" if errores == 0 else f"{errores} errores"))
