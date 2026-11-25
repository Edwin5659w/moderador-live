# Moderador LIVE (TikTok)

Aplicación para el portátil que vigila el chat del live, marca los comentarios de riesgo
y les arma la lista de usuarios para bloquear. **No bloquea sola**: ustedes bloquean desde TikTok.

- 🟡 **SILENCIAR** (riesgo bajo): apuestas, cuotas, casas de apuestas, WhatsApp… La gente lo dice sin mala intención.
- 🔴 **BLOQUEAR** (riesgo alto): "estafa", "no sirve", "pa qué", "reporten", insultos, amenazas. Suena una alarma.

## Instalar (una sola vez)
1. Instala Python desde https://www.python.org/downloads/ — **marca "Add Python to PATH"**.
2. Descomprime esta carpeta donde la vayan a dejar fija (ej. `Documentos\moderador`). No la muevan después.
3. Doble clic en **instalar.bat**. Crea el acceso directo **Moderador LIVE** en el Escritorio.

## Usar en cada live
1. Inicien el live desde el teléfono.
2. Abran **Moderador LIVE** desde el Escritorio. Se abre en el navegador.
3. Escriban el @ de la cuenta y den **Conectar**.
4. Cuando salga una alerta roja: **Copiar @** → búsquenlo en TikTok → bloquear → marquen ✓ en la app.

Para probar sin live: botón **Probar demo**.

## Botones
- **Copiar filtro TikTok**: copia todas las palabras amarillas para pegarlas en
  Configuración del LIVE → Filtrar palabras clave. Así TikTok las oculta solo.
- **Editar palabras / Recargar palabras**: abre `palabras.txt` para agregar o quitar palabras.
- **Descargar registro**: Excel con todas las alertas (`registro_alertas.csv`).
- **Cerrar app**: apaga el moderador.

## Si algo falla
- "No está en vivo": el live tiene que estar encendido antes de conectar.
- No conecta aunque esté en vivo: abran `cmd` en la carpeta y corran `pip install -U TikTokLive`.
- Probar la detección: `python test_detector.py`.
