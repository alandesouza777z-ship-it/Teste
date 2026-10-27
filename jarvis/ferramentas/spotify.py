"""Controle do Spotify pela Web API (precisa de conta Premium para controlar a reprodução)."""

import os
import platform
import time
import webbrowser
from urllib.parse import quote

from config import PASTA_USUARIO

from .aplicativos import abrir_programa
from .base import _schema

ESCOPOS = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
_cliente = None


def _sp():
    global _cliente
    if _cliente is None:
        if not os.getenv("SPOTIPY_CLIENT_ID"):
            raise RuntimeError("Spotify não configurado: preencha SPOTIPY_CLIENT_ID e SPOTIPY_CLIENT_SECRET no .env.")
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        _cliente = spotipy.Spotify(auth_manager=SpotifyOAuth(
            scope=ESCOPOS, open_browser=True, cache_path=os.path.join(PASTA_USUARIO, ".cache-spotify")
        ))
    return _cliente


def _dispositivo():
    """Devolve o id de um dispositivo ativo; abre o app do Spotify se não houver nenhum."""
    sp = _sp()
    for tentativa in range(2):
        dispositivos = sp.devices()["devices"]
        if dispositivos:
            ativo = next((d for d in dispositivos if d["is_active"]), dispositivos[0])
            return ativo["id"]
        if tentativa == 0:
            abrir_programa("spotify")
            time.sleep(6)
    raise RuntimeError("Nenhum dispositivo do Spotify encontrado. Abra o Spotify em algum aparelho.")


def _seguro(funcao):
    def envolvida(**kwargs):
        try:
            return funcao(**kwargs)
        except Exception as erro:
            return f"Erro no Spotify: {erro}"

    return envolvida


def _abrir_uri(uri: str) -> None:
    """Abre um link spotify:... direto no aplicativo do Spotify."""
    if platform.system() == "Windows":
        os.startfile(uri)
    else:
        webbrowser.open(uri)


def tocar_spotify(busca: str, tipo: str = "musica") -> str:
    tipos = {"musica": "track", "artista": "artist", "album": "album", "playlist": "playlist"}
    tipo_api = tipos.get(tipo, "track")
    item = None
    if os.getenv("SPOTIPY_CLIENT_ID"):
        try:
            sp = _sp()
            resultado = sp.search(q=busca, type=tipo_api, limit=1, market="BR")
            itens = [i for i in resultado[tipo_api + "s"]["items"] if i]
            if not itens:
                return f"Não encontrei '{busca}' no Spotify."
            item = itens[0]
            dispositivo = _dispositivo()
            if tipo_api == "track":
                sp.start_playback(device_id=dispositivo, uris=[item["uri"]])
                return f"Tocando {item['name']} de {item['artists'][0]['name']}."
            sp.start_playback(device_id=dispositivo, context_uri=item["uri"])
            return f"Tocando {tipo} {item['name']}."
        except Exception as erro:
            print(f"Spotify pela API falhou ({erro}); abrindo no aplicativo.")

    # Sem API (ou sem Premium): abre direto no aplicativo do Spotify.
    if item:
        _abrir_uri(item["uri"])
        aberto = f"a página de '{item['name']}'"
    else:
        _abrir_uri("spotify:search:" + quote(busca))
        aberto = f"a busca por '{busca}'"
    time.sleep(3)
    return (f"Abri {aberto} no aplicativo do Spotify, mas ainda não dei play. Agora use ver_tela, "
            "encontre o resultado certo e clique no botão de play (passe o mouse/clique no primeiro "
            "resultado ou no botão verde). Confira com ver_tela se começou a tocar.")


@_seguro
def controlar_spotify(acao: str, valor: int | None = None) -> str:
    sp = _sp()
    dispositivo = _dispositivo()
    if acao == "pausar":
        sp.pause_playback(device_id=dispositivo)
    elif acao == "continuar":
        sp.start_playback(device_id=dispositivo)
    elif acao == "proxima":
        sp.next_track(device_id=dispositivo)
    elif acao == "anterior":
        sp.previous_track(device_id=dispositivo)
    elif acao == "volume":
        sp.volume(max(0, min(100, valor if valor is not None else 50)), device_id=dispositivo)
    elif acao == "aleatorio":
        sp.shuffle(bool(valor if valor is not None else 1), device_id=dispositivo)
    else:
        return "Ação inválida."
    return f"Spotify: {acao} feito."


@_seguro
def musica_atual() -> str:
    atual = _sp().current_playback()
    if not atual or not atual.get("item"):
        return "Nada tocando no momento."
    item = atual["item"]
    estado = "tocando" if atual["is_playing"] else "pausado"
    return f"{estado}: {item['name']} de {', '.join(a['name'] for a in item['artists'])}."


FERRAMENTAS = [
    (_schema("tocar_spotify", "Procura e toca uma música, artista, álbum ou playlist no Spotify.",
             {"busca": {"type": "string", "description": "O que procurar, ex.: 'Back in Black AC/DC'."},
              "tipo": {"type": "string", "enum": ["musica", "artista", "album", "playlist"]}}, ["busca"]),
     tocar_spotify),
    (_schema("controlar_spotify", "Pausar, continuar, pular, voltar, volume (0-100) ou aleatório (1/0) no Spotify.",
             {"acao": {"type": "string", "enum": ["pausar", "continuar", "proxima", "anterior", "volume", "aleatorio"]},
              "valor": {"type": "integer"}}, ["acao"]), controlar_spotify),
    (_schema("musica_atual", "Diz qual música está tocando no Spotify."), musica_atual),
]
