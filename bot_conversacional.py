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


# ============================================================
# CONFIGURACIÓN DE DISCORD
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# ============================================================
# MEMORIA
# ============================================================

MAX_HISTORY = 20

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
Eres un asistente de Discord con personalidad de pirata.

Debes responder SIEMPRE como un pirata, pero de forma natural.
Tu prioridad es ser útil, claro y correcto.

Puedes responder cualquier pregunta que haga el usuario.

Utiliza ocasionalmente expresiones como:
- Arrr
- Ahoy
- marinero
- capitán
- tripulación
- navegar
- barco
- tesoro

No exageres las expresiones piratas hasta hacer que la respuesta
sea difícil de entender.

Si el usuario hace una pregunta técnica, proporciona una respuesta
técnica correcta pero manteniendo ligeramente la personalidad pirata.

Si el usuario habla de un tema serio, responde con respeto y sin
hacer bromas inapropiadas.

Recuerda el contexto de la conversación y utiliza los mensajes
anteriores para responder de forma coherente.
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

    print(f"🏴‍☠️ Bot conectado como {client.user}")
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
            "🏴‍☠️ ¡Arrr! He borrado la memoria de esta conversación, "
            "capitán. ¡Podemos comenzar una nueva aventura!"
        )

        return

    # ========================================================
    # HELLO
    # ========================================================

    if content.lower() == "$hello":

        await message.channel.send(
            "🏴‍☠️ ¡Ahoy, marinero! ¡El capitán está a bordo!"
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

        await message.channel.send(
            "🏴‍☠️ Arrr... ¡el cofre de monedas del barco está vacío! 💰\n"
            "No puedo consultar al oráculo en este momento. "
            "El capitán tendrá que revisar la cuenta de OpenAI."
        )

    # ========================================================
    # API KEY INCORRECTA
    # ========================================================

    except AuthenticationError as error:

        print(f"🔑 Error de autenticación de OpenAI: {error}")

        await message.channel.send(
            "🏴‍☠️ Arrr... ¡mi mapa hacia el oráculo no funciona! 🗺️\n"
            "Parece haber un problema con la configuración de la "
            "clave de OpenAI."
        )

    # ========================================================
    # OTROS ERRORES DE LA API
    # ========================================================

    except APIStatusError as error:

        print(
            f"⚠️ Error de OpenAI "
            f"(status {error.status_code}): {error}"
        )

        await message.channel.send(
            "🏴‍☠️ Arrr... el oráculo no está respondiendo correctamente. "
            "¡Intentemos de nuevo más tarde!"
        )

    # ========================================================
    # ERROR GENERAL
    # ========================================================

    except Exception as error:

        print(f"❌ Error inesperado: {error}")

        await message.channel.send(
            "🏴‍☠️ Arrr... algo salió mal a bordo. ⚓\n"
            "No pude procesar esa pregunta. ¡Inténtalo nuevamente!"
        )


# ============================================================
# INICIAR
# ============================================================

client.run(DISCORD_TOKEN)
