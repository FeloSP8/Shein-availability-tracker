# SheIn Availability Tracker

Backend (sin interfaz web) que comprueba periódicamente si una talla concreta
de uno o varios productos de SheIn está disponible, y avisa por correo
electrónico en cuanto pasa de "agotada" a "disponible".

## Cómo funciona

SheIn no ofrece una API pública de stock por talla, y su API interna cambia
de forma con frecuencia. Para no depender de un contrato no documentado, este
proyecto abre la página del producto en un navegador real (Chromium headless
vía [Playwright](https://playwright.dev/python/)) y lee lo mismo que vería
una persona: si el selector de la talla aparece marcado como agotado o no.

Flujo de cada comprobación:

1. Abre la URL del producto (puede ser el enlace para compartir, tipo
   `.../h5/sharejump/appjump?...`, o la URL directa `.../-p-<id>.html`).
2. Localiza los botones/etiquetas de talla en la página.
3. Comprueba si la talla configurada (p. ej. `S`) está disponible.
4. Si pasó de agotada a disponible, envía un correo y lo recuerda en
   `state.json` para no enviar el mismo aviso otra vez (si vuelve a agotarse,
   se reiniciará y avisará de nuevo la próxima vez que esté disponible).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps
```

Copia las plantillas de configuración:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

Edita `config.yaml` con tus productos. En `.env` solo hacen falta 3 datos
(el envío usa Gmail, con host/puerto ya fijados en el código):

- `GMAIL_USER`: tu correo de Gmail (también se usa como remitente).
- `GMAIL_APP_PASSWORD`: una "contraseña de aplicación" (actívala en
  https://myaccount.google.com/apppasswords; necesitas la verificación en
  dos pasos activada y no puedes usar tu contraseña normal de Gmail).
- `EMAIL_TO`: el correo que recibirá los avisos de disponibilidad.

## Uso

Comprobación única (ideal para cron / systemd timer):

```bash
python main.py check-once
```

Bucle continuo, comprobando cada `check_interval_hours` (definido en
`config.yaml`):

```bash
python main.py run
```

## Ejecutar cada X horas

### Opción A: proceso en bucle (Docker)

```bash
docker compose up -d --build
```

El contenedor queda corriendo y comprueba cada `check_interval_hours` horas
según `config.yaml`. `state.json` se persiste como volumen para no perder el
historial de avisos entre reinicios.

### Opción B: cron / systemd timer + `check-once`

Más ligero si ya tienes un servidor con Python. Ejemplo de crontab para
comprobar cada 3 horas:

```cron
0 */3 * * * cd /ruta/al/proyecto && .venv/bin/python main.py check-once >> tracker.log 2>&1
```

### Opción C: GitHub Actions (sin servidor propio)

El repo incluye `.github/workflows/shein-tracker.yml`, que ejecuta
`python main.py check-once` cada 3 horas (`cron: "0 */3 * * *"`, ajústalo si
quieres otra cadencia) usando un runner gratuito de GitHub, sin necesidad de
tener ningún servidor encendido.

Cómo activarlo:

1. En el repo de GitHub, ve a **Settings → Secrets and variables → Actions →
   New repository secret** y crea estos 3 secrets (mismos valores que
   pondrías en `.env`):
   - `GMAIL_USER`
   - `GMAIL_APP_PASSWORD`
   - `EMAIL_TO`
2. En **Settings → Actions → General → Workflow permissions**, marca
   **"Read and write permissions"**. Es necesario para que el workflow pueda
   guardar `state.json` (así no reenvía el mismo aviso en la siguiente
   ejecución).
3. `config.yaml` y `state.json` ya están versionados en el repo (no
   contienen secretos, solo la URL/talla a vigilar y el historial de
   avisos), así que no hace falta configurar nada más. Edita `config.yaml`
   directamente en el repo si quieres cambiar de producto/talla.
4. Puedes lanzarlo manualmente desde la pestaña **Actions → SheIn
   availability check → Run workflow** para probarlo sin esperar al cron.

Limitaciones a tener en cuenta:

- Los `schedule` de GitHub Actions no son exactos (pueden retrasarse en
  horas de mucha carga) y se deshabilitan automáticamente si el repositorio
  lleva 60 días sin actividad; en ese caso hay que reactivarlos a mano desde
  la pestaña Actions.
- **Confirmado en pruebas: SheIn bloquea con un CAPTCHA el tráfico desde los
  runners de GitHub Actions.** Tanto con el enlace para compartir como con la
  URL directa del producto, la navegación termina en
  `https://us.shein.com/risk/challenge?captcha_type=909&...` en vez de
  llegar a la página del producto, así que `check-once` no puede leer la
  talla (no es un problema de selectores CSS, es un bloqueo por IP de
  datacenter). Esto no es exclusivo de este repo: los rangos de IP de los
  runners de GitHub son de sobra conocidos por los sistemas anti-bot. Si te
  pasa lo mismo, la Opción C no es viable para este sitio tal cual está
  configurada; usa la Opción A (Docker) o B (cron/systemd) en tu propia
  máquina o servidor, donde es más probable (aunque no seguro al 100%) que
  la IP no esté marcada como IP de datacenter/bot. Antes de montar nada,
  prueba `python main.py debug --url "<url>"` en tu propia red para
  confirmar que ahí sí se llega a la página real del producto.

## Ajustar los selectores si SheIn cambia su HTML

El proyecto no se pudo probar en vivo contra shein.com desde este entorno de
desarrollo (el acceso a Internet estaba restringido a un listado de dominios
de paquetes). Los selectores CSS por defecto en `src/config.py` están
basados en la estructura habitual de las páginas de producto de SheIn, pero
puede que necesites ajustarlos la primera vez que lo ejecutes en un entorno
con acceso real a SheIn.

Para calibrarlos en local:

```bash
python main.py debug --url "https://tu-url-de-producto"
```

O sin instalar nada, desde GitHub: pestaña **Actions → SheIn debug snapshot
→ Run workflow**, pega la URL del producto, y al terminar descarga el
artifact `shein-debug-snapshot` (contiene `snapshot.png` y `snapshot.html`).

Cualquiera de las dos vías genera `debug/snapshot.png` (captura de la página
tal y como la vio el navegador) y `debug/snapshot.html` (HTML final). Ábrelos,
inspecciona con las herramientas de desarrollador del navegador el elemento
de la talla que buscas, y anota:

- El selector CSS que agrupa cada talla (p. ej. `.sku-item`).
- Qué clase o atributo distingue una talla agotada de una disponible (p. ej.
  `class="sku-item soldout"` o `aria-disabled="true"`).

Después edita la sección `selectors` en `config.yaml` (ver el ejemplo
comentado en `config.example.yaml`) con esos valores.

## Notas

- El enlace de "compartir" de SheIn (`h5/sharejump/appjump?...`) puede
  caducar o requerir una app instalada. Si `check-once`/`run` fallan con un
  error de "la navegación no llegó a shein.com", abre el enlace una vez en un
  navegador de escritorio, copia la URL final del producto
  (`https://.../-p-<id>.html`) y úsala directamente en `config.yaml`: es más
  estable a largo plazo que el enlace para compartir.
- Cada producto puede tener varias tallas en `sizes: [...]`; se avisa de
  forma independiente por cada una.
- Puedes seguir varios productos añadiendo más entradas en `products`.

## Tests

Las pruebas cubren la lógica que no depende de red ni de navegador
(parseo de tallas, persistencia de estado, carga de configuración):

```bash
pip install -r requirements-dev.txt
pytest
```
