#!/usr/bin/env python3
"""Gera uma video-aula: slides HTML sincronizados com a narracao da ElevenLabs.

Le um roteiro .md e usa o endpoint with-timestamps, que devolve o tempo de cada
caractere falado. Com isso cada topico do slide acende no instante exato em que
e narrado, sem chutar duracao.

Formato do roteiro:

    # Titulo da aula
    Uma linha de subtitulo, opcional.

    ## Titulo do slide
    figura: figuras/pipeline.svg    (svg inline, ou png/jpg embutido)
    - Topico curto :: Frase completa que sera narrada.
    - Outro topico            (sem ::, narra o proprio topico)

Numa figura svg, elementos com class="passo" e data-passo="0" acendem quando o
topico daquele indice esta sendo falado.

Saida: out/<nome>.html, com o audio embutido, pronto para publicar.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html as html_mod
import json
import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import mp3  # noqa: E402
import speak  # noqa: E402

TEMPLATE = ROOT / "aula_template.html"
OUT_DIR = config.OUT_DIR
CACHE_DIR = config.CACHE_DIR
DEFAULT_FORMAT = "mp3_44100_64"  # metade do peso do 128, sobra para o data URI
BYTES_POR_SEGUNDO = {
    "mp3_22050_32": 4000, "mp3_44100_32": 4000, "mp3_44100_64": 8000,
    "mp3_44100_96": 12000, "mp3_44100_128": 16000, "mp3_44100_192": 24000,
}


# --------------------------------------------------------------------------- #
# figuras
# --------------------------------------------------------------------------- #
def carregar_figura(base: Path, referencia: str) -> str:
    """SVG entra inline (herda as cores do tema); imagem vira data URI."""
    if not referencia:
        return ""
    arquivo = (base / referencia) if not Path(referencia).is_absolute() else Path(referencia)
    if not arquivo.is_file():
        arquivo = ROOT / referencia
    if not arquivo.is_file():
        sys.exit(f"Figura nao encontrada: {referencia}")

    if arquivo.suffix.lower() == ".svg":
        return arquivo.read_text(encoding="utf-8").strip()

    tipo = mimetypes.guess_type(arquivo.name)[0] or "image/png"
    dados = base64.b64encode(arquivo.read_bytes()).decode("ascii")
    return f'<img src="data:{tipo};base64,{dados}" alt="">'


# --------------------------------------------------------------------------- #
# roteiro
# --------------------------------------------------------------------------- #
def parse_roteiro(caminho: Path) -> tuple[str, str, list[dict]]:
    titulo, subtitulo = caminho.stem, ""
    slides: list[dict] = []
    atual: dict | None = None

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.rstrip()
        if linha.startswith("# "):
            titulo = linha[2:].strip()
        elif linha.startswith("## "):
            atual = {"titulo": linha[3:].strip(), "topicos": [], "figura": ""}
            slides.append(atual)
        elif linha.strip().lower().startswith("figura:") and atual is not None:
            atual["figura"] = carregar_figura(caminho.parent, linha.split(":", 1)[1].strip())
        elif linha.lstrip().startswith(("- ", "* ")) and atual is not None:
            texto = linha.lstrip()[2:].strip()
            rotulo, _, narracao = texto.partition("::")
            atual["topicos"].append({
                "rotulo": rotulo.strip(),
                "narracao": (narracao.strip() or rotulo.strip()),
            })
        elif linha.strip() and atual is None and not subtitulo and titulo:
            subtitulo = linha.strip()

    slides = [s for s in slides if s["topicos"]]
    if not slides:
        sys.exit("Roteiro vazio: use '## titulo' para cada slide e '- topico' para os itens.")
    return titulo, subtitulo, slides


def pontuar(frase: str) -> str:
    """Garante ponto final: sem ele o modelo emenda os topicos numa frase so."""
    return frase if frase.endswith((".", "!", "?", ":")) else frase + "."


# --------------------------------------------------------------------------- #
# sintese
# --------------------------------------------------------------------------- #
def sintetizar(texto: str, voice: str, model: str, fmt: str, speed: float,
               language: str | None) -> tuple[bytes, list[float]]:
    """Devolve o audio do trecho e o tempo inicial de cada caractere.

    O resultado fica em cache por conteudo: reescrever uma figura ou o layout
    e regerar a aula nao gasta creditos de novo.
    """
    assinatura = hashlib.sha256(
        "|".join([texto, voice, model, fmt, str(speed), language or ""]).encode("utf-8")
    ).hexdigest()[:20]
    cache = CACHE_DIR / f"{assinatura}.json"
    if cache.is_file():
        guardado = json.loads(cache.read_text(encoding="utf-8"))
        return base64.b64decode(guardado["audio"]), guardado["inicios"]

    audio, inicios = pedir_a_api(texto, voice, model, fmt, speed, language)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "audio": base64.b64encode(audio).decode("ascii"), "inicios": inicios,
    }), encoding="utf-8")
    return audio, inicios


def pedir_a_api(texto: str, voice: str, model: str, fmt: str, speed: float,
                language: str | None) -> tuple[bytes, list[float]]:
    body = {
        "text": texto,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": speed},
    }
    if language and not model.startswith("eleven_multilingual"):
        body["language_code"] = language

    url = f"{speak.API_BASE}/text-to-speech/{voice}/with-timestamps?output_format={fmt}"
    payload = json.loads(speak.request(url, data=json.dumps(body).encode("utf-8"),
                                       method="POST"))
    audio = base64.b64decode(payload["audio_base64"])
    alinhamento = payload.get("alignment") or {}
    caracteres = alinhamento.get("characters") or []
    inicios = alinhamento.get("character_start_times_seconds") or []

    # o alinhamento deve espelhar o texto enviado; se a API normalizar algo,
    # o mapa por indice deixa de valer e caimos para a divisao proporcional
    if "".join(caracteres) != texto or len(inicios) != len(texto):
        return audio, []
    return audio, inicios


def tempo_do_indice(inicios: list[float], indice: int, texto: str,
                    duracao: float) -> float:
    if inicios:
        return round(inicios[min(indice, len(inicios) - 1)], 3)
    proporcao = indice / max(len(texto), 1)  # fallback: reparte pela extensao
    return round(proporcao * duracao, 3)


# --------------------------------------------------------------------------- #
# montagem
# --------------------------------------------------------------------------- #
def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="aula.py",
        description="Gera uma pagina de video-aula com slides sincronizados com a narracao.",
    )
    parser.add_argument("roteiro", help="arquivo .md no formato descrito no cabecalho")
    parser.add_argument("--out", help="caminho do .html gerado")
    parser.add_argument("--format", dest="fmt", default=DEFAULT_FORMAT,
                        choices=sorted(BYTES_POR_SEGUNDO),
                        help=f"qualidade do audio (padrao {DEFAULT_FORMAT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra os slides e o texto narrado, sem chamar a API")
    args = parser.parse_args()

    speak.load_dotenv()
    voice = os.environ.get("ELEVENLABS_VOICE_ID", speak.DEFAULT_VOICE)
    model = os.environ.get("ELEVENLABS_MODEL_ID", speak.DEFAULT_MODEL)
    language = os.environ.get("ELEVENLABS_LANGUAGE")
    speed = float(os.environ.get("ELEVENLABS_SPEED", "1.0"))

    caminho = Path(args.roteiro)
    titulo, subtitulo, slides = parse_roteiro(caminho)
    total_chars = sum(len(pontuar(t["narracao"])) + 1
                      for s in slides for t in s["topicos"])

    if args.dry_run:
        print(f"{titulo} | {len(slides)} slides | {total_chars} caracteres\n")
        for i, slide in enumerate(slides, 1):
            print(f"--- {i}. {slide['titulo']}")
            for topico in slide["topicos"]:
                print(f"    - {topico['rotulo']}\n      {pontuar(topico['narracao'])}")
        return

    audio_total = bytearray()
    decorrido = 0.0

    for i, slide in enumerate(slides, 1):
        narracoes = [pontuar(t["narracao"]) for t in slide["topicos"]]
        texto = " ".join(narracoes)
        print(f"[{i}/{len(slides)}] {slide['titulo']} ({len(texto)} caracteres)...",
              file=sys.stderr)

        audio, inicios = sintetizar(texto, voice, model, args.fmt, speed, language)
        audio = mp3.limpar(audio)      # sem ID3 nem Xing: a emenda vira um arquivo so
        duracao = mp3.duracao(audio)   # contada frame a frame, nao estimada

        slide["t"] = round(decorrido, 3)
        indice = 0
        for topico, narracao in zip(slide["topicos"], narracoes):
            topico["t"] = round(decorrido + tempo_do_indice(inicios, indice, texto, duracao), 3)
            indice += len(narracao) + 1
        slide["fim"] = round(decorrido + duracao, 3)

        audio_total += audio
        decorrido += duracao

    # a linha do tempo dos slides so vale se a emenda durar o que a soma diz;
    # divergencia aqui e o sintoma de trecho com cabecalho proprio sobrando
    medida = mp3.duracao(bytes(audio_total))
    if abs(medida - decorrido) > 0.1:
        print(f"[aviso] emenda mede {medida:.2f}s mas a soma dos trechos da "
              f"{decorrido:.2f}s: os slides vao dessincronizar", file=sys.stderr)

    dados = {
        "titulo": titulo,
        "subtitulo": subtitulo,
        "duracao": round(decorrido, 3),
        "slides": [
            {
                "titulo": s["titulo"],
                "figura": s["figura"],
                "t": s["t"],
                "fim": s["fim"],
                "topicos": [{"texto": t["rotulo"], "t": t["t"]} for t in s["topicos"]],
            }
            for s in slides
        ],
    }

    destino = Path(args.out) if args.out else OUT_DIR / f"{caminho.stem}.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    pagina = (TEMPLATE.read_text(encoding="utf-8")
              .replace("{{TITULO}}", html_mod.escape(titulo))
              .replace("{{DADOS}}", json.dumps(dados, ensure_ascii=False))
              .replace("{{AUDIO}}", "data:audio/mpeg;base64,"
                       + base64.b64encode(bytes(audio_total)).decode("ascii")))
    destino.write_text(pagina, encoding="utf-8")

    minutos, segundos = divmod(int(decorrido + 0.5), 60)
    print(f"{destino}  ({len(pagina) / 1_048_576:.1f} MB, {minutos}:{segundos:02d} de audio)")


if __name__ == "__main__":
    main()
