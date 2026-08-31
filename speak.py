#!/usr/bin/env python3
"""Le um texto em voz alta usando a API de text-to-speech da ElevenLabs.

Aceita arquivo .md, .txt, .html/.htm, texto direto (--text) ou stdin ("-").
Nao depende de pacotes externos: usa apenas a stdlib.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.elevenlabs.io/v1"
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import historico  # noqa: E402
import mp3  # noqa: E402
import tocador  # noqa: E402

OUT_DIR = config.OUT_DIR
CACHE_DIR = config.CACHE_DIR

DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # George, voz do quickstart da ElevenLabs
DEFAULT_MODEL = "eleven_turbo_v2_5"  # unico da familia v2 que aceita language_code
DEFAULT_FORMAT = "mp3_44100_128"
CHUNK_LIMIT = 2500  # caracteres por requisicao
PAUSED_CHUNK_LIMIT = 1200  # com break tags: menos tags por geracao, menos instabilidade
MAX_PAUSE = 3.0     # limite de <break time> aceito pela ElevenLabs
MIN_SPEED = 0.7     # faixa de velocidade que a API aceita
MAX_SPEED = 1.2


# --------------------------------------------------------------------------- #
# configuracao
# --------------------------------------------------------------------------- #
def load_dotenv() -> None:
    config.carregar_env()


def ler_velocidade(valor: str | float | None) -> float:
    """Converte e valida a velocidade, venha ela do .env ou da flag.

    Fora da faixa a API so responde 422 depois de receber o texto inteiro.
    """
    if valor is None or valor == "":
        return 1.0
    try:
        velocidade = float(valor)
    except (TypeError, ValueError):
        sys.exit(f"Velocidade invalida: {valor!r}. Use um numero entre "
                 f"{MIN_SPEED} e {MAX_SPEED} (ELEVENLABS_SPEED ou --speed).")
    if not MIN_SPEED <= velocidade <= MAX_SPEED:
        sys.exit(f"Velocidade fora da faixa: {velocidade}. A API aceita de "
                 f"{MIN_SPEED} a {MAX_SPEED} (ELEVENLABS_SPEED ou --speed).")
    return velocidade


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ELEVENLABS_API_KEY nao definida.\n"
            + config.instrucao_da_chave()
        )
    return key


# --------------------------------------------------------------------------- #
# extracao de texto
# --------------------------------------------------------------------------- #
def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|head|noscript)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<!--.*?-->", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return html.unescape(raw)


def markdown_to_text(raw: str) -> str:
    raw = re.sub(r"(?s)\A---\n.*?\n---\n", "", raw)          # front matter
    raw = re.sub(r"(?s)```.*?```", " ", raw)                  # blocos de codigo
    raw = re.sub(r"(?s)~~~.*?~~~", " ", raw)
    raw = re.sub(r"`([^`]*)`", r"\1", raw)                    # codigo inline
    raw = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", raw)           # imagens
    raw = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", raw)        # links
    raw = re.sub(r"^\s{0,3}>+\s?", "", raw, flags=re.M)       # citacoes
    raw = re.sub(r"^\s{0,3}#{1,6}\s*", "", raw, flags=re.M)   # titulos
    raw = re.sub(r"^\s*[-*_]{3,}\s*$", " ", raw, flags=re.M)  # linhas horizontais
    raw = re.sub(r"^\s*[-*+]\s+", "", raw, flags=re.M)        # bullets
    raw = re.sub(r"(\*\*|__|\*|_|~~)", "", raw)               # enfase
    raw = re.sub(r"^\s*\|.*\|\s*$", " ", raw, flags=re.M)     # tabelas
    return html_to_text(raw)


# ponto final de frase no meio da prosa: precedido de letra/numero/fecha-aspas,
# seguido de espaco e do inicio de uma nova frase. Ignora decimais (3.14) e o
# ponto que encerra o texto, que ja nao precisa de pausa.
SENTENCE_END = re.compile(
    r"(?<=[a-zà-öø-ÿ0-9)\]\"'»])\.(?=\s+[\"'(«\[]?[A-ZÀ-ÖØ-Þ0-9])"
)


def add_pauses(text: str, seconds: float) -> str:
    """Insere break tags da ElevenLabs apos cada ponto final de frase."""
    if seconds <= 0:
        return text
    tag = f'.<break time="{min(seconds, MAX_PAUSE):.1f}s" />'
    return SENTENCE_END.sub(lambda _: tag, text)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract(source: str, kind: str | None = None) -> str:
    """source: caminho de arquivo, texto puro ou '-' para stdin."""
    if source == "-":
        raw, suffix = sys.stdin.read(), ".txt"
    else:
        path = Path(source)
        if len(source) < 260 and path.exists() and path.is_file():
            raw = path.read_text(encoding="utf-8", errors="replace")
            suffix = path.suffix.lower()
        else:
            raw, suffix = source, ".txt"

    fmt = kind or {
        ".md": "md", ".markdown": "md", ".mdx": "md",
        ".html": "html", ".htm": "html", ".xhtml": "html",
    }.get(suffix, "txt")

    if fmt == "md":
        raw = markdown_to_text(raw)
    elif fmt == "html":
        raw = html_to_text(raw)
    return normalize(raw)


def chunks(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    pieces: list[str] = []
    for block in re.split(r"\n\n+", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= limit:
            pieces.append(block)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?:;])\s+", block):
            while len(sentence) > limit:  # frase gigante sem pontuacao
                pieces.append(sentence[:limit])
                sentence = sentence[limit:]
            if len(current) + len(sentence) + 1 > limit:
                if current:
                    pieces.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            pieces.append(current.strip())

    merged: list[str] = []
    for piece in pieces:
        if merged and len(merged[-1]) + len(piece) + 2 <= limit:
            merged[-1] = f"{merged[-1]}\n\n{piece}"
        else:
            merged.append(piece)
    return merged


# --------------------------------------------------------------------------- #
# ElevenLabs
# --------------------------------------------------------------------------- #
def request(url: str, *, data: bytes | None = None, method: str = "GET") -> bytes:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("xi-api-key", api_key())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:800]
        sys.exit(f"ElevenLabs {err.code}: {detail}")
    except urllib.error.URLError as err:
        sys.exit(f"Falha de rede: {err.reason}")


def list_voices() -> None:
    payload = json.loads(request(f"{API_BASE}/voices"))
    for voice in payload.get("voices", []):
        labels = voice.get("labels") or {}
        tags = ", ".join(f"{k}={v}" for k, v in labels.items())
        print(f"{voice['voice_id']}  {voice['name']:<24} {tags}")


def synthesize(text: str, voice: str, model: str, fmt: str, speed: float,
               language: str | None, prev: str | None, nxt: str | None) -> bytes:
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "speed": speed,
        },
    }
    # language_code forca o idioma e a normalizacao do texto; a API rejeita o
    # campo no multilingual_v2, que so detecta o idioma pelo proprio texto
    if language and not model.startswith("eleven_multilingual"):
        body["language_code"] = language
    if prev:
        body["previous_text"] = prev[-500:]
    if nxt:
        body["next_text"] = nxt[:500]
    url = f"{API_BASE}/text-to-speech/{voice}?output_format={fmt}"
    return request(url, data=json.dumps(body).encode("utf-8"), method="POST")


def resumo(texto: str, limite: int = 60) -> str:
    """Como a narracao aparece no historico quando nao veio de um arquivo."""
    uma_linha = " ".join(texto.split())
    if len(uma_linha) <= limite:
        return uma_linha
    return uma_linha[:limite - 1].rstrip() + "…"


def assinatura(text: str, voice: str, model: str, fmt: str, speed: float,
               language: str | None, prev: str | None, nxt: str | None) -> str:
    """Identidade do trecho: tudo que muda o audio entra aqui.

    Os vizinhos entram truncados como a API os recebe, porque sao eles que
    ajustam a prosodia na emenda: mudar o chunk anterior muda o audio deste.
    """
    partes = [text, voice, model, fmt, f"{speed}", language or "",
              (prev or "")[-500:], (nxt or "")[:500]]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:20]


def sintetizar(text: str, voice: str, model: str, fmt: str, speed: float,
               language: str | None, prev: str | None, nxt: str | None,
               usar_cache: bool = True) -> tuple[bytes, bool]:
    """A sintese com cache por conteudo. Devolve o audio e se ele veio do cache.

    Cache que nao pode ser escrito nao interrompe a narracao.
    """
    if not usar_cache:
        return synthesize(text, voice, model, fmt, speed, language, prev, nxt), False

    chave = assinatura(text, voice, model, fmt, speed, language, prev, nxt)
    destino = CACHE_DIR / f"{chave}.{'mp3' if fmt.startswith('mp3') else 'bin'}"
    if destino.is_file():
        try:
            return destino.read_bytes(), True
        except OSError:
            pass

    audio = synthesize(text, voice, model, fmt, speed, language, prev, nxt)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(audio)
    except OSError:
        pass
    return audio, False


def emendar(partes: list[bytes], fmt: str) -> bytes:
    """Junta os trechos num arquivo so, sem os cabecalhos que sobram no meio.

    Cada resposta da API e um MP3 completo, e o player adota o cabecalho do
    primeiro trecho como duracao do arquivo inteiro. Sem eles, a duracao sai do
    tamanho e do bitrate. Trecho unico passa intocado, porque o cabecalho dele ja
    descreve o arquivo certo; formato que nao e MP3 tambem, porque a limpeza le
    frames de MP3.
    """
    if len(partes) == 1 or not fmt.startswith("mp3"):
        return b"".join(partes)
    return b"".join(mp3.limpar(parte) for parte in partes)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # antes do parser: os defaults das flags saem das variaveis do .env
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="speak.py",
        description="Le em voz alta um arquivo md/txt/html (ou texto direto) via ElevenLabs.",
    )
    parser.add_argument("source", nargs="?", help="caminho do arquivo, texto, ou '-' para stdin")
    parser.add_argument("--text", help="texto literal (alternativa ao argumento posicional)")
    parser.add_argument("--as", dest="kind", choices=["md", "html", "txt"],
                        help="forca o formato de entrada")
    parser.add_argument("--voice", default=os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE))
    parser.add_argument("--model", default=os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL))
    parser.add_argument("--format", dest="fmt", default=DEFAULT_FORMAT,
                        help=f"output_format da API (padrao {DEFAULT_FORMAT})")
    parser.add_argument("--speed", type=ler_velocidade,
                        default=ler_velocidade(os.environ.get("ELEVENLABS_SPEED")),
                        help=f"{MIN_SPEED} a {MAX_SPEED}; padrao: ELEVENLABS_SPEED")
    parser.add_argument("--language", default=os.environ.get("ELEVENLABS_LANGUAGE"),
                        help="codigo ISO 639-1 (pt, en, es...) que forca o idioma; "
                             "ignorado pelo eleven_multilingual_v2")
    parser.add_argument("--pause", type=float, default=None,
                        help="segundos de silencio apos cada ponto final "
                             f"(0 desliga, maximo {MAX_PAUSE:.0f}; padrao: "
                             "ELEVENLABS_SENTENCE_PAUSE)")
    parser.add_argument("--out", help="caminho do arquivo de audio gerado")
    parser.add_argument("--no-play", action="store_true", help="apenas gera o arquivo")
    parser.add_argument("--sem-historico", action="store_true",
                        help="toca e apaga, sem deixar o audio no historico")
    parser.add_argument("--historico", nargs="?", type=int, const=20, default=None,
                        metavar="N", help="lista as N ultimas narracoes (padrao 20)")
    parser.add_argument("--abrir", nargs="?", type=int, const=1, default=None,
                        metavar="N", help="abre a narracao N do historico (1 = a "
                                          "ultima) no player do sistema e sai")
    parser.add_argument("--no-cache", action="store_true",
                        help="sintetiza de novo mesmo que o trecho ja esteja em cache")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra o texto extraido e os chunks, sem chamar a API")
    parser.add_argument("--list-voices", action="store_true", help="lista as vozes da conta")
    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        return

    if args.historico is not None:
        print(historico.formatar(historico.recentes(args.historico)))
        return

    if args.abrir is not None:
        anotado = historico.item(args.abrir)
        if not anotado:
            sys.exit("Nao existe narracao com esse numero. "
                     "Veja a lista com: speak.py --historico")
        caminho = Path(anotado["arquivo"])
        if not caminho.is_file():
            sys.exit(f"O audio de {anotado['quando']} ja saiu do disco.")
        aberto = tocador.abrir_no_sistema(caminho)
        print(f"{anotado['quando']}  {anotado['origem']}  ->  {caminho}")
        if not aberto:
            sys.exit("Nao abriu no programa de audio: o aviso acima diz o que falta.")
        return

    source = args.text if args.text is not None else args.source
    if not source:
        parser.error("informe um arquivo, --text, ou '-' para stdin")

    text = extract(source, args.kind)
    if not text:
        sys.exit("Nada para ler: o texto extraido ficou vazio.")

    if args.pause is not None:
        pause = args.pause
    else:
        try:
            pause = float(os.environ.get("ELEVENLABS_SENTENCE_PAUSE", "0"))
        except ValueError:
            sys.exit("ELEVENLABS_SENTENCE_PAUSE precisa ser um numero, em segundos.")
    if pause > MAX_PAUSE:
        print(f"[aviso] pausa limitada a {MAX_PAUSE:.0f}s pela API", file=sys.stderr)

    parts = chunks(text, PAUSED_CHUNK_LIMIT if pause else CHUNK_LIMIT)
    # as break tags entram depois do chunking, para nao serem cortadas ao meio
    # e para nao contarem no limite de caracteres do chunk
    spoken = [add_pauses(part, pause) for part in parts]

    if args.dry_run:
        print(f"{len(text)} caracteres, {len(parts)} chunk(s), pausa {pause}s, "
              f"voz {args.voice}, modelo {args.model}, "
              f"idioma {args.language or 'auto'}, velocidade {args.speed}\n")
        for i, part in enumerate(spoken, 1):
            print(f"--- chunk {i} ({len(part)}) ---\n{part}\n")
        return

    audio: list[bytes] = []
    for i, part in enumerate(spoken):
        trecho, do_cache = sintetizar(
            part, args.voice, args.model, args.fmt, args.speed, args.language,
            parts[i - 1] if i else None,
            parts[i + 1] if i + 1 < len(parts) else None,
            usar_cache=not args.no_cache,
        )
        if len(spoken) > 1:
            origem = "do cache" if do_cache else "sintetizando"
            print(f"[{i + 1}/{len(spoken)}] {origem}, {len(part)} caracteres...",
                  file=sys.stderr)
        audio.append(trecho)

    # o destino so e criado depois que tudo deu certo: erro da API nao
    # deixa arquivo vazio no disco
    src_path = Path(source) if len(source) < 260 else None
    veio_de_arquivo = bool(src_path and src_path.is_file())
    ext = "mp3" if args.fmt.startswith("mp3") else "bin"

    if args.out:
        target = Path(args.out)
    elif args.sem_historico:
        fd, tmp = tempfile.mkstemp(suffix=f".{ext}", prefix="speak-")
        os.close(fd)
        target = Path(tmp)
    else:
        stem = src_path.stem if veio_de_arquivo else "fala"
        target = OUT_DIR / f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}.{ext}"

    dados = emendar(audio, args.fmt)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(dados)

    if not args.sem_historico:
        historico.registrar(
            target,
            src_path.name if veio_de_arquivo else resumo(text),
            len(text),
            mp3.duracao(dados) if ext == "mp3" else 0.0,
            args.voice, args.model, args.speed,
        )

    if args.no_play:
        print(target)
        return

    tocador.tocar(target)
    if args.sem_historico and not args.out:
        target.unlink(missing_ok=True)
    else:
        print(target)


if __name__ == "__main__":
    main()
