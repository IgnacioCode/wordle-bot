import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import wordleBot

class DummyMember:
    def __init__(self, user_id, display_name):
        self.id = user_id
        self.display_name = display_name

class DummyGuild:
    def __init__(self, members=None):
        self._members = {m.id: m for m in (members or [])}

    def get_member(self, user_id):
        return self._members.get(user_id)

class DummyMessage:
    def __init__(self, content, guild):
        self.content = content
        self.guild = guild


def test_extraer_jugadores_mentions_and_names():
    text = "@juan @maria <@123> <@!456>"
    jugadores = wordleBot.extraer_jugadores(text)
    assert jugadores == ["@juan", "@maria", "<@123>", "<@!456>"]


def test_analizar_mensaje_updates_score():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    message = DummyMessage("3/6: <@1> @Bob", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))

    assert wordleBot.puntajes["Alice"]["total"] == 4
    assert wordleBot.puntajes["Bob"]["total"] == 4
    assert wordleBot.puntajes["Alice"]["detalles"][3] == 1
    assert wordleBot.puntajes["Bob"]["detalles"][3] == 1

# Caso 1: se procesan varias lineas en un mismo mensaje
# Esperado: Alice acumula 9 puntos (4 + 5)
def test_multiple_lines_single_message():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    message = DummyMessage("3/6: <@1>\n2/6: <@1>", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))
    assert wordleBot.puntajes["Alice"]["total"] == 9

# Caso 2: varios jugadores en la misma linea
# Esperado: ambos jugadores reciben 6 puntos
def test_multiple_players_single_line():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice"), DummyMember(2, "Bob")])
    message = DummyMessage("1/6: <@1> <@2>", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))
    assert wordleBot.puntajes["Alice"]["total"] == 6
    assert wordleBot.puntajes["Bob"]["total"] == 6

# Caso 3: intentos fuera de rango se ignoran
# Esperado: no se registran puntajes
def test_invalid_attempts_are_ignored():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    message = DummyMessage("7/6: <@1>", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))
    assert wordleBot.puntajes == {}

# Caso 4: el mismo jugador recibe puntos de mensajes distintos
# Esperado: acumulación correcta (5 + 3 = 8)
def test_repeated_player_accumulates():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    msg1 = DummyMessage("2/6: <@1>", guild)
    msg2 = DummyMessage("4/6: <@1>", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(msg1))
    asyncio.run(wordleBot.analizar_mensaje(msg2))
    assert wordleBot.puntajes["Alice"]["total"] == 8
    assert wordleBot.puntajes["Alice"]["detalles"][2] == 1
    assert wordleBot.puntajes["Alice"]["detalles"][4] == 1

# Caso 5: mezcla de menciones y nombres de usuario
# Esperado: cada jugador suma 6 puntos
def test_mixed_mentions_and_names():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    message = DummyMessage("1/6: <@1> @Bob", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))
    assert wordleBot.puntajes["Alice"]["total"] == 6
    assert wordleBot.puntajes["Bob"]["total"] == 6

# Caso 6: mensajes separados para distintos jugadores
# Esperado: Alice 5 puntos, Bob 3 puntos
def test_multiple_messages_different_users():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice"), DummyMember(2, "Bob")])
    msg1 = DummyMessage("2/6: <@1>", guild)
    msg2 = DummyMessage("4/6: <@2>", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(msg1))
    asyncio.run(wordleBot.analizar_mensaje(msg2))
    assert wordleBot.puntajes["Alice"]["total"] == 5
    assert wordleBot.puntajes["Bob"]["total"] == 3

# Caso 7: se registran intentos diferentes para el mismo jugador
# Esperado: detalles contiene un intento de 1, 2 y 3; total 15
def test_details_tracking_various_attempts():
    wordleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    msgs = [
        DummyMessage("1/6: <@1>", guild),
        DummyMessage("2/6: <@1>", guild),
        DummyMessage("3/6: <@1>", guild),
    ]
    import asyncio
    for m in msgs:
        asyncio.run(wordleBot.analizar_mensaje(m))
    assert wordleBot.puntajes["Alice"]["detalles"][1] == 1
    assert wordleBot.puntajes["Alice"]["detalles"][2] == 1
    assert wordleBot.puntajes["Alice"]["detalles"][3] == 1
    assert wordleBot.puntajes["Alice"]["total"] == 15

# Caso 8: solo nombres de usuario sin menciones
# Esperado: cada nombre suma 2 puntos
def test_text_usernames_only():
    wordleBot.puntajes.clear()
    guild = DummyGuild([])
    message = DummyMessage("5/6: @juan @maria", guild)
    import asyncio
    asyncio.run(wordleBot.analizar_mensaje(message))
    assert wordleBot.puntajes["juan"]["total"] == 2
    assert wordleBot.puntajes["maria"]["total"] == 2

