#!/usr/bin/env python3
"""Hook Stop: narra a ultima resposta do assistant.

Recebe o JSON do hook em stdin, acha a ultima mensagem do assistant no
transcript e manda para o speak.py. So age quando o arquivo sentinela
.narrar-respostas existe na raiz do repositorio, para nao gastar creditos
da ElevenLabs em toda resposta sem querer.

Ligar:   narrar.cmd on
Desligar: narrar.cmd off
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEAK = ROOT / "speak.py"
MAX_CHARS = int(os.environ.get("NARRAR_MAX_CHARS", "1200"))

sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import speak  # noqa: E402

SENTINELA = config.SENTINELA


def ultima_resposta(transcript: Path) -> str:
    """Texto da ultima mensagem do assistant no transcript JSONL."""
    if not transcript.is_file():
        return ""
    for line in reversed(transcript.read_text(encoding="utf-8", errors="replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            partes = [b.get("text", "") for b in content
                      if isinstance(b, dict) and b.get("type") == "text"]
            texto = "\n\n".join(p for p in partes if p.strip())
            if texto.strip():
                return texto
    return ""


def truncar(texto: str, limite: int) -> str:
    """Corta no fim da ultima frase que cabe, para nao parar no meio da palavra."""
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "), corte.rfind("\n"))
    return (corte[:fim + 1] if fim > limite // 3 else corte).strip()


def main() -> None:
    if not SENTINELA.exists():
        return

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    # stop_hook_active: o Stop ja disparou e o Claude voltou a trabalhar.
    # Narrar de novo repetiria a mesma resposta.
    if payload.get("stop_hook_active"):
        return

    transcript = payload.get("transcript_path")
    if not transcript:
        return

    bruto = ultima_resposta(Path(transcript))
    texto = truncar(speak.normalize(speak.markdown_to_text(bruto)), MAX_CHARS)
    if len(texto) < 15:  # respostas de uma palavra nao valem uma requisicao
        return

    fd, caminho = tempfile.mkstemp(suffix=".txt", prefix="resposta-", text=True)
    os.close(fd)
    Path(caminho).write_text(texto, encoding="utf-8")
    try:
        done = subprocess.run([sys.executable, str(SPEAK), caminho],
                              capture_output=True, text=True, timeout=600)
        if done.returncode != 0:
            # o hook nunca bloqueia o Claude: so registra o motivo
            print(f"[narrar] speak.py falhou: {done.stderr.strip()[:300]}", file=sys.stderr)
    finally:
        Path(caminho).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
