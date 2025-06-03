import discord
from discord.ext import commands
import re
from collections import defaultdict
from dotenv import load_dotenv
import os
import csv
import json

CONFIG_FILE = "config.json"
wordle_channel_id = None

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", 0) 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necesario para obtener nombres de usuario

bot = commands.Bot(command_prefix='!', intents=intents)

CSV_FILE = "puntajes.csv"

# Cambiamos la clave del diccionario a str para que acepte tanto user_ids como usernames
puntajes = defaultdict(lambda: {"user_id": None, "username": "", "total": 0, "detalles": defaultdict(int)})

# Regex para líneas tipo: "3/6: <@123> <@456>"
linea_puntaje_regex = re.compile(r"(\d)/6:\s*(.+)")



# Regex para extraer menciones <@123456789012345678>
mencion_regex = re.compile(r"<@!?(\d+)>")

# Detecta jugadores que empiezan con @ o <@ y terminan antes del siguiente
def extraer_jugadores(cadena):
    patron = re.compile(r"(@[^@<]+?|<@!?[\d]+>)(?=\s+@|\s+<@|$)")
    return [m.group(1).strip() for m in patron.finditer(cadena)]

def cargar_config():
    global wordle_channel_id
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            wordle_channel_id = data.get("wordle_channel_id")

def guardar_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"wordle_channel_id": wordle_channel_id}, f)

def cargar_puntajes():
    if not os.path.exists(CSV_FILE):
        return
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row["CLAVE"]
            user_id = row["ID"]
            username = row["USERNAME"]
            total = int(row["TOTAL"])
            detalles = {i: int(row.get(f"{i}/6", 0)) for i in range(1, 7)}

            puntajes[key]["user_id"] = int(user_id) if user_id else None
            puntajes[key]["username"] = username
            puntajes[key]["total"] = total
            puntajes[key]["detalles"].update(detalles)

def guardar_puntajes():
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ["CLAVE", "ID", "USERNAME", "TOTAL"] + [f"{i}/6" for i in range(1, 7)]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, data in puntajes.items():
            fila = {
                "CLAVE": key,
                "ID": data["user_id"] if data["user_id"] else "",
                "USERNAME": data["username"],
                "TOTAL": data["total"],
                **{f"{i}/6": data["detalles"].get(i, 0) for i in range(1, 7)}
            }
            writer.writerow(fila)

async def analizar_mensaje(message):
    nuevas_lineas = linea_puntaje_regex.findall(message.content)
    for intentos_str, jugadores_str in nuevas_lineas:
        intentos = int(intentos_str)
        if not (1 <= intentos <= 6):
            continue

        jugadores = extraer_jugadores(jugadores_str)
        
        for entrada in jugadores:
            if entrada.startswith("<@"):
                match = re.match(r"<@!?(\d+)>", entrada)
                if match:
                    user_id = int(match.group(1))
                    miembro = message.guild.get_member(user_id)
                    if miembro:
                        puntos = 7 - intentos
                        puntajes[miembro.display_name]["user_id"] = user_id
                        puntajes[miembro.display_name]["total"] += puntos
                        puntajes[miembro.display_name]["detalles"][intentos] += 1
                        puntajes[miembro.display_name]["username"] = miembro.display_name
            elif entrada.startswith("@"):
                username = entrada[1:].strip()
                clave = f"{username}"
                puntos = 7 - intentos
                puntajes[clave]["username"] = username
                puntajes[clave]["total"] += puntos
                puntajes[clave]["detalles"][intentos] += 1


@bot.event
async def on_ready():
    cargar_puntajes()
    cargar_config()
    print(f'Bot conectado como {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("Your group is on"):
        nuevas_lineas = linea_puntaje_regex.findall(message.content)
        for intentos_str, jugadores_str in nuevas_lineas:
            intentos = int(intentos_str)
            if not (1 <= intentos <= 6):
                continue

            jugadores = extraer_jugadores(jugadores_str)

            for entrada in jugadores:
                if entrada.startswith("<@"):
                    match = re.match(r"<@!?(\d+)>", entrada)
                    if match:
                        user_id = int(match.group(1))
                        miembro = message.guild.get_member(user_id)
                        if miembro:
                            puntos = 7 - intentos
                            puntajes[miembro.display_name]["user_id"] = user_id
                            puntajes[miembro.display_name]["total"] += puntos
                            puntajes[miembro.display_name]["detalles"][intentos] += 1
                            puntajes[miembro.display_name]["username"] = miembro.display_name
                elif entrada.startswith("@"):
                    username = entrada[1:].strip()
                    clave = f"{username}"
                    puntos = 7 - intentos
                    puntajes[clave]["username"] = username
                    puntajes[clave]["total"] += puntos
                    puntajes[clave]["detalles"][intentos] += 1

        guardar_puntajes()

    await bot.process_commands(message)

@bot.command(name='puntajes')
async def mostrar_puntajes(ctx):
    if not puntajes:
        await ctx.send("Todavía no hay puntajes registrados.")
        return

    header = f"{'PLAYER':<25}|{'TOTAL':<5}|{'1/6':<4}|{'2/6':<4}|{'3/6':<4}|{'4/6':<4}|{'5/6':<4}|{'6/6':<4}"
    separator = '-' * len(header)
    rows = []

    # Ordenar por puntaje total descendente
    for user_id, data in sorted(puntajes.items(), key=lambda x: x[1]["total"], reverse=True):
        fila = f"{data['username']:<25}|{data['total']:<5}|"
        for intentos in range(1, 7):
            cantidad = data["detalles"].get(intentos, 0)
            fila += f"{cantidad:<4}|"
        rows.append(fila)

    tabla = "```" + header + "\n" + separator + "\n" + "\n".join(rows) + "```"
    await ctx.send(tabla)

@bot.command(name='setWordleChat')
async def set_wordle_chat(ctx, canal_id: int):
    global wordle_channel_id
    canal = bot.get_channel(canal_id)
    if canal is None:
        await ctx.send("❌ Canal no encontrado. Verificá el ID.")
        return
    wordle_channel_id = canal_id
    guardar_config()
    await ctx.send(f"✅ Canal de Wordle configurado: {canal.name}")

@bot.command(name='scanChat')
async def scan_chat(ctx):
    if not wordle_channel_id:
        await ctx.send("❌ No hay canal configurado. Usá `!setWordleChat <canal_id>` primero.")
        return

    canal = bot.get_channel(wordle_channel_id)
    if not canal:
        await ctx.send("❌ No se pudo acceder al canal.")
        return

    await ctx.send(f"🔍 Escaneando mensajes en #{canal.name}... Esto puede demorar.")

    count = 0
    puntajes.clear()  # Limpiar puntajes antes de escanear
    async for message in canal.history(limit=None, oldest_first=True):
        if message.author.name == BOT_NAME:
            if message.content.startswith("**Your group is on") or message.content.startswith("Your group is on"):
                await analizar_mensaje(message)
                count += 1

    guardar_puntajes()
    await ctx.send(f"✅ Escaneo completo. Se procesaron {count} mensajes.")

@bot.command(name='puntos')
async def mostrar_puntajes(ctx):
    if not puntajes:
        await ctx.send("Todavía no hay puntajes registrados.")
        return

    header = f"{'PLAYER':<25}|{'TOTAL':<5}|{'1/6':<4}|{'2/6':<4}|{'3/6':<4}|{'4/6':<4}|{'5/6':<4}|{'6/6':<4}"
    separator = '-' * len(header)
    rows = []

    ordenados = sorted(puntajes.items(), key=lambda x: x[1]["total"], reverse=True)

    # Si hay al menos un jugador real, insertamos a Anibal con +1
    if ordenados:
        primer_jugador_data = ordenados[0][1]
        anibal_total = primer_jugador_data["total"] + 1
        anibal_detalles = {
            intentos: primer_jugador_data["detalles"].get(intentos, 0) + 1
            for intentos in range(1, 7)
        }
        fila_anibal = f"{'Anibal':<25}|{anibal_total:<5}|"
        for intentos in range(1, 7):
            fila_anibal += f"{anibal_detalles[intentos]:<4}|"
        rows.append(fila_anibal)

    # Luego agregamos el resto
    for user_id, data in ordenados:
        fila = f"{data['username']:<25}|{data['total']:<5}|"
        for intentos in range(1, 7):
            cantidad = data["detalles"].get(intentos, 0)
            fila += f"{cantidad:<4}|"
        rows.append(fila)


    tabla = "```" + header + "\n" + separator + "\n" + "\n".join(rows) + "```"
    await ctx.send(tabla)


bot.run(DISCORD_TOKEN)
