#!/usr/bin/env python3
"""Le um texto em voz alta usando a API de text-to-speech da ElevenLabs.

Aceita arquivo .md, .txt, .html/.htm, texto direto (--text) ou stdin ("-").
Nao depende de pacotes externos: usa apenas a stdlib.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
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

OUT_DIR = config.OUT_DIR

DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # George, voz do quickstart da ElevenLabs
DEFAULT_MODEL = "eleven_turbo_v2_5"  # unico da familia v2 que aceita language_code
DEFAULT_FORMAT = "mp3_44100_128"
CHUNK_LIMIT = 2500  # caracteres por requisicao
PAUSED_CHUNK_LIMIT = 1200  # com break tags: menos tags por geracao, menos instabilidade
MAX_PAUSE = 3.0     # limite de <break time> aceito pela ElevenLabs


# --------------------------------------------------------------------------- #
# configuracao
# --------------------------------------------------------------------------- #
def load_dotenv() -> None:
    config.carregar_env()


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


# --------------------------------------------------------------------------- #
# reproducao
# --------------------------------------------------------------------------- #
PLAY_PS = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([uri]'{uri}')
$deadline = (Get-Date).AddSeconds(15)
while (-not $player.NaturalDuration.HasTimeSpan -and (Get-Date) -lt $deadline) {{
    Start-Sleep -Milliseconds 100
}}
$player.Play()
if ($player.NaturalDuration.HasTimeSpan) {{
    Start-Sleep -Seconds ($player.NaturalDuration.TimeSpan.TotalSeconds + 0.6)
}} else {{
    Start-Sleep -Seconds 5
}}
$player.Stop()
$player.Close()
"""


def play(path: Path) -> None:
    if sys.platform == "win32":
        script = PLAY_PS.format(uri=path.resolve().as_uri())
        done = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True,
        )
        if done.returncode == 0:
            return
        print(f"[aviso] player embutido falhou: {done.stderr.strip()[:200]}", file=sys.stderr)
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    for player in (["afplay"], ["mpv", "--no-video"], ["ffplay", "-nodisp", "-autoexit"]):
        try:
            subprocess.run(player + [str(path)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    print(f"[aviso] nenhum player encontrado; audio salvo em {path}", file=sys.stderr)


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
    parser.add_argument("--speed", type=float,
                        default=float(os.environ.get("ELEVENLABS_SPEED", "1.0")),
                        help="0.7 a 1.2; padrao: ELEVENLABS_SPEED")
    parser.add_argument("--language", default=os.environ.get("ELEVENLABS_LANGUAGE"),
                        help="codigo ISO 639-1 (pt, en, es...) que forca o idioma; "
                             "ignorado pelo eleven_multilingual_v2")
    parser.add_argument("--pause", type=float, default=None,
                        help="segundos de silencio apos cada ponto final "
                             f"(0 desliga, maximo {MAX_PAUSE:.0f}; padrao: "
                             "ELEVENLABS_SENTENCE_PAUSE)")
    parser.add_argument("--out", help="caminho do arquivo de audio gerado")
    parser.add_argument("--no-play", action="store_true", help="apenas gera o arquivo")
    parser.add_argument("--keep", action="store_true", help="mantem o audio em out/ ao tocar")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra o texto extraido e os chunks, sem chamar a API")
    parser.add_argument("--list-voices", action="store_true", help="lista as vozes da conta")
    args = parser.parse_args()

    if args.list_voices:
        list_voices()
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
        if len(spoken) > 1:
            print(f"[{i + 1}/{len(spoken)}] sintetizando {len(part)} caracteres...",
                  file=sys.stderr)
        audio.append(synthesize(
            part, args.voice, args.model, args.fmt, args.speed, args.language,
            parts[i - 1] if i else None,
            parts[i + 1] if i + 1 < len(parts) else None,
        ))

    # o destino so e criado depois que tudo deu certo: erro da API nao
    # deixa arquivo vazio no disco
    src_path = Path(source) if len(source) < 260 else None
    if args.out:
        target = Path(args.out)
    elif args.no_play or args.keep:
        stem = src_path.stem if src_path and src_path.is_file() else "fala"
        ext = "mp3" if args.fmt.startswith("mp3") else "bin"
        target = OUT_DIR / f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
    else:
        fd, tmp = tempfile.mkstemp(suffix=".mp3", prefix="speak-")
        os.close(fd)
        target = Path(tmp)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"".join(audio))

    if args.no_play:
        print(target)
        return

    play(target)
    if args.out or args.keep:
        print(target)
    else:
        target.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
