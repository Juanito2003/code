# Aviso de cita – Toma de huellas (Ourense)

Script que revisa cada ~7 minutos la cita previa de extranjería
(**POLICÍA-TOMA DE HUELLAS**, oficina **CNP ORENSE EXTRANJEROS**) y te avisa
en cuanto aparece una cita libre.

> ⚠️ Tiene que ejecutarse en **tu ordenador, en España**. La web de cita
> previa bloquea las conexiones desde servidores en la nube y desde el extranjero.

## 1. Instalar (una sola vez)

Necesitas Python 3.9 o superior (https://www.python.org/downloads/).

```bash
pip install playwright
python -m playwright install chromium
```

## 2. Configurar

Copia `config.example.json` como `config.json` y rellena tus datos tal como
los pondrías en la web:

| Campo | Qué poner |
|---|---|
| `nie` | Tu NIE (ej. `X1234567A`) |
| `nombre` | Nombre y apellidos |
| `pais` | País de nacionalidad, como aparece en la lista de la web |
| `anno_nacimiento` | Solo se usa si la web lo pide |
| `intervalo_minutos` | Cada cuánto revisar. No bajes de 5: si se consulta demasiado, la web te bloquea temporalmente |
| `telegram_token` / `telegram_chat_id` | Opcional, para recibir el aviso en el móvil (ver abajo) |

## 3. Ejecutar

```bash
python vigilar_cita.py
```

Se abre una ventana de Chrome que hace el recorrido sola. Si no hay citas lo
apunta y espera. Si encuentra una:

- suena un pitido,
- te manda un Telegram (si lo configuraste),
- guarda una captura en `cita_encontrada.png`,
- **deja la ventana abierta en la página de la cita para que termines tú la reserva.**

Las citas vuelan en minutos, así que reserva en cuanto te avise.

## Aviso al móvil por Telegram (recomendado)

1. En Telegram, habla con **@BotFather**, envía `/newbot` y sigue los pasos.
   Te dará un *token* → ponlo en `telegram_token`.
2. Escribe cualquier mensaje a tu nuevo bot.
3. Abre en el navegador `https://api.telegram.org/bot<TOKEN>/getUpdates` y
   copia el número de `"chat":{"id": ...}` → ponlo en `telegram_chat_id`.

## Si algo falla

- Si la web muestra algo inesperado (bloqueo, cambio de diseño), el script
  guarda `pagina_desconocida.png` y te avisa para que lo revises.
- Si te aparece "The requested URL was rejected", te han bloqueado por exceso
  de consultas: para el script un par de horas y sube `intervalo_minutos`.
