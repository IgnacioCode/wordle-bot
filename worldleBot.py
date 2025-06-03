import discord
from discord.ext import commands
import re
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv()  # Carga las variables del archivo .env

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Intents necesarios para acceder a los mensajes
intents = discord.Intents.default()
intents.message_content = True

# Bot con prefijo "!"
bot = commands.Bot(command_prefix='!', intents=intents)

# Diccionario de puntajes: {usuario: {"total": int, "detalles": {1: x, 2: y, ..., 6: z}}}
puntajes = defaultdict(lambda: {"total": 0, "detalles": defaultdict(int)})

# Regex para identificar mensajes tipo "Your group is on..." y entradas "n/6:JUGADOR"
linea_puntaje_regex = re.compile(r"(\d)/6:([^\n]+)")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("Your group is on"):
        nuevas_lineas = linea_puntaje_regex.findall(message.content)
        for intentos_str, jugador in nuevas_lineas:
            intentos = int(intentos_str)
            if 1 <= intentos <= 6:
                puntos = 7 - intentos  # 6 intentos = 1 punto, 5 = 2, ..., 1 = 6 puntos
                if intentos not in range(1, 7):
                    continue
                jugador = jugador.strip()
                puntajes[jugador]["total"] += puntos
                puntajes[jugador]["detalles"][intentos] += 1

    await bot.process_commands(message)

@bot.command(name='puntajes')
async def mostrar_puntajes(ctx):
    if not puntajes:
        await ctx.send("Todavía no hay puntajes registrados.")
        return

    msg = "**🏆 Tabla de puntajes Wordle:**\n"
    for jugador, data in puntajes.items():
        msg += f"\n**{jugador}** - Total: {data['total']} pts | Partidas:"
        for intentos in range(1, 7):
            cantidad = data["detalles"].get(intentos, 0)
            if cantidad > 0:
                msg += f" {intentos}/6×{cantidad}"
    await ctx.send(msg)

bot.run(DISCORD_TOKEN)
