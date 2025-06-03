import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import worldleBot

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
    jugadores = worldleBot.extraer_jugadores(text)
    assert jugadores == ["@juan", "@maria", "<@123>", "<@!456>"]


def test_analizar_mensaje_updates_score():
    worldleBot.puntajes.clear()
    guild = DummyGuild([DummyMember(1, "Alice")])
    message = DummyMessage("3/6: <@1> @Bob", guild)
    import asyncio
    asyncio.run(worldleBot.analizar_mensaje(message))

    assert worldleBot.puntajes["Alice"]["total"] == 4
    assert worldleBot.puntajes["Bob"]["total"] == 4
    assert worldleBot.puntajes["Alice"]["detalles"][3] == 1
    assert worldleBot.puntajes["Bob"]["detalles"][3] == 1
