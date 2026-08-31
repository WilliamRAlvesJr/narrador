#!/usr/bin/env python3
"""Reproducao do audio.

O player e o mais simples que existe: abre, toca ate o fim, fecha. Parar e
assunto de quem chamou, nao daqui: a narracao roda como tarefa em segundo plano
do Claude Code, e encerrar essa tarefa derruba o player junto, porque ele e
processo filho dela.

Nao confundir com o player da video-aula, que e o JavaScript do aula_template.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PLAYER = """
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

# Da esquerda para a direita, o primeiro que existir toca. Todos precisam sair
# sozinhos no fim do audio e nao abrir janela: quem so entende WAV, como o
# paplay, fica de fora, porque a narracao e sempre MP3.
PLAYERS_UNIX = (
    ["afplay"],
    ["mpv", "--no-video", "--no-terminal"],
    ["mpg123", "-q"],
    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error"],
    ["cvlc", "--play-and-exit", "--intf", "dummy"],
    ["gst-play-1.0", "--quiet"],
    ["pw-play"],
    ["play", "-q"],
)


def players_disponiveis(existe=shutil.which) -> list[list[str]]:
    """Os players instalados nesta maquina, na ordem de preferencia."""
    return [comando for comando in PLAYERS_UNIX if existe(comando[0])]


def tocar(caminho: Path) -> None:
    """Toca e so retorna no fim, ou quando a tarefa que chamou e encerrada."""
    if sys.platform == "win32":
        script = PLAYER.format(uri=caminho.resolve().as_uri())
        feito = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True,
        )
        if feito.returncode != 0 and feito.stderr.strip():
            print(f"[aviso] player embutido falhou: {feito.stderr.strip()[:200]}",
                  file=sys.stderr)
        return

    for comando in players_disponiveis():
        try:
            # sem stdin: player nenhum daqui le teclado, e mpv e gst-play leriam
            subprocess.run(comando + [str(caminho)], check=True,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (OSError, subprocess.CalledProcessError):
            continue
    nomes = ", ".join(comando[0] for comando in PLAYERS_UNIX[1:])
    print(f"[aviso] nenhum player tocou o audio, que esta em {caminho}. "
          f"Instale um destes: {nomes}.", file=sys.stderr)


def abrir_no_sistema(caminho: Path) -> None:
    """Entrega o arquivo ao programa de audio do usuario e volta na hora."""
    if sys.platform == "win32":
        os.startfile(str(caminho))  # type: ignore[attr-defined]
        return

    abridor = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([abridor, str(caminho)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"[aviso] nao achei {abridor}; o audio esta em {caminho}",
              file=sys.stderr)
