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

PLAYERS_UNIX = (["afplay"], ["mpv", "--no-video"], ["ffplay", "-nodisp", "-autoexit"])


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

    for comando in PLAYERS_UNIX:
        try:
            subprocess.run(comando + [str(caminho)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    print(f"[aviso] nenhum player encontrado; audio salvo em {caminho}", file=sys.stderr)


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
