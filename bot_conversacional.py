import os

import discord
from dotenv import load_dotenv
from openai import OpenAI, APIStatusError, RateLimitError, AuthenticationError


# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not DISCORD_TOKEN:
    raise RuntimeError("Falta TOKEN en el archivo .env")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_KEY en el archivo .env")


openai_client = OpenAI(api_key=OPENAI_KEY)
ERROR_MESSAGE = (
    "Lo siento, en este momento tuve un problema para procesar tu consulta. "
    "Por favor, inténtalo nuevamente en unos minutos."
)


# ============================================================
# CONFIGURACIÓN DE DISCORD
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# ============================================================
# MEMORIA
# ============================================================

MAX_HISTORY = 50

# Memoria separada por canal
conversations = {}


def get_history(channel_id):
    """Devuelve el historial de conversación de un canal."""

    if channel_id not in conversations:
        conversations[channel_id] = []

    return conversations[channel_id]


def add_to_history(channel_id, role, content):
    """Añade un mensaje al historial."""

    history = get_history(channel_id)

    history.append({
        "role": role,
        "content": content
    })

    # Mantener solamente los últimos mensajes
    if len(history) > MAX_HISTORY:
        conversations[channel_id] = history[-MAX_HISTORY:]


def reset_history(channel_id):
    """Borra la memoria del canal."""

    conversations[channel_id] = []


# ============================================================
# PERSONALIDAD
# ============================================================

SYSTEM_PROMPT = """
Eres PropiA, un asistente especializado en inversión inmobiliaria en Chile.

Tu objetivo es ayudar a personas interesadas en inversión inmobiliaria a:
- Entender conceptos básicos de inversión inmobiliaria en Chile.
- Resolver dudas generales sobre este tipo de inversión.
- Entender conceptos como pie, crédito hipotecario, rentabilidad,
  plusvalía, flujo mensual, vacancia, UF y otros conceptos relacionados.
- Construir progresivamente su perfil de inversión mediante una
  conversación natural.
- Orientar la conversación de acuerdo con los objetivos y situación
  que el usuario vaya compartiendo.

PERSONALIDAD Y TONO

Habla como un asesor inmobiliario profesional, cercano y claro.

Debes:
- Ser cordial y natural.
- Mantener un tono profesional sin ser excesivamente formal.
- Explicar conceptos de manera sencilla.
- Hacer preguntas cuando necesites información adicional.
- Evitar respuestas innecesariamente largas.
- No sonar como un vendedor.
- No presionar al usuario para invertir.
- No inventar información que no conoces.

DOMINIO

Tu especialidad es la inversión inmobiliaria en Chile.

Puedes responder preguntas relacionadas directamente con:
- Inversión inmobiliaria.
- Compra de propiedades como inversión.
- Rentabilidad.
- Plusvalía.
- Flujo mensual.
- Vacancia.
- Pie.
- Crédito hipotecario.
- UF.
- Evaluación general de oportunidades inmobiliarias.
- Riesgos asociados a una inversión inmobiliaria.
- Construcción del perfil de un inversionista.

También puedes responder preguntas estrechamente relacionadas cuando
sean necesarias para entender una decisión de inversión inmobiliaria.

FUERA DE DOMINIO

Si el usuario pregunta sobre un tema que no está relacionado con
inversión inmobiliaria, no respondas la pregunta como un asistente general.

Explícale brevemente y de manera natural que tu especialidad es la
inversión inmobiliaria en Chile y ofrece continuar con algún aspecto
relacionado.

No utilices siempre exactamente la misma frase para rechazar consultas
fuera del dominio.

PERFIL DE INVERSIÓN

Durante una conversación puedes intentar conocer progresivamente:

1. Capital disponible para invertir.
2. Capacidad de pago mensual.
3. Objetivo principal:
   - plusvalía
   - flujo mensual
   - mixto
4. Horizonte de inversión:
   - corto plazo
   - mediano plazo
   - largo plazo
5. Tolerancia al riesgo:
   - conservador
   - moderado
   - agresivo

No conviertas la conversación en un formulario.

Si el usuario entrega espontáneamente varios datos, reconócelos y evita
preguntarlos nuevamente.

Haz preguntas solamente cuando sean naturales y útiles para continuar
la conversación.

IMPORTANTE

Todavía no debes afirmar que encontraste propiedades reales ni inventar
proyectos, precios, tasas de interés u oportunidades actuales.

Si no tienes información suficiente para responder algo con seguridad,
indícalo claramente.

Recuerda el contexto de la conversación y utiliza los mensajes
anteriores para responder de manera coherente.
"""


# ============================================================
# OPENAI
# ============================================================

def ask_openai(channel_id, user_message):
    """
    Envía el mensaje a OpenAI utilizando el historial
    de conversación de ese canal.
    """

    history = get_history(channel_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Agregar conversación anterior
    messages.extend(history)

    # Agregar mensaje actual
    messages.append({
        "role": "user",
        "content": user_message
    })

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("OpenAI devolvió una respuesta vacía.")

    # Guardar conversación solamente si OpenAI respondió correctamente
    add_to_history(channel_id, "user", user_message)
    add_to_history(channel_id, "assistant", answer)

    return answer


# ============================================================
# BOT CONECTADO
# ============================================================

@client.event
async def on_ready():
    print(f"🏠 PropiA conectado como {client.user}")
    print(f"🤖 Modelo OpenAI: {OPENAI_MODEL}")


# ============================================================
# MENSAJES
# ============================================================

@client.event
async def on_message(message):

    # No responderse a sí mismo
    if message.author == client.user:
        return

    content = message.content.strip()

    if not content:
        return

    channel_id = message.channel.id

# ========================================================
# RESET
# ========================================================

if content.lower() == "$reset":
    reset_history(channel_id)

    await message.channel.send(
        "Listo. He reiniciado el contexto de esta conversación. "
        "Podemos comenzar nuevamente."
    )
    return

# ========================================================
# HELLO
# ========================================================

if content.lower() == "$hello":
    await message.channel.send(
        "¡Hola! 👋 Soy PropiA, tu asistente de inversión inmobiliaria "
        "en Chile. ¿En qué te puedo ayudar?"
    )
    return

# ========================================================
# CONVERSACIÓN
# ========================================================

try:
    async with message.channel.typing():
        response = ask_openai(
            channel_id,
            content
        )

    await message.channel.send(response)

# ========================================================
# CUOTA / RATE LIMIT
# ========================================================

except RateLimitError as error:
    print(f"⚠️ Rate limit / cuota de OpenAI: {error}")
    await message.channel.send(ERROR_MESSAGE)

# ========================================================
# API KEY INCORRECTA
# ========================================================

except AuthenticationError as error:
    print(f"🔑 Error de autenticación de OpenAI: {error}")
    await message.channel.send(ERROR_MESSAGE)

# ========================================================
# OTROS ERRORES DE LA API
# ========================================================

except APIStatusError as error:
    print(
        f"⚠️ Error de OpenAI "
        f"(status {error.status_code}): {error}"
    )
    await message.channel.send(ERROR_MESSAGE)

# ========================================================
# ERROR GENERAL
# ========================================================

except Exception as error:
    print(f"❌ Error inesperado: {error}")
    await message.channel.send(ERROR_MESSAGE)


# ============================================================
# INICIAR
# ============================================================

client.run(DISCORD_TOKEN)
