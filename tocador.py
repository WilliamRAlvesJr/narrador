#!/usr/bin/env python3
"""Reproducao do audio.

O player e o mais simples que existe: abre, toca ate o fim, fecha. Parar e
assunto de quem chamou, nao daqui: a narracao roda como tarefa em segundo plano
do Claude Code, e encerrar essa tarefa derruba o player junto, porque ele e
processo filho dela.

Sem nenhum player de linha de comando, o audio ainda vai para o programa padrao
do sistema. Esse desfecho e pior de proposito: o programa nao e filho da tarefa,
entao o usuario perde o silencio a um clique. Perder o som inteiro e pior.

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

NOMES = ", ".join(comando[0] for comando in PLAYERS_UNIX[1:])  # o afplay ja vem no macOS


def players_disponiveis(existe=shutil.which) -> list[list[str]]:
    """Os players instalados nesta maquina, na ordem de preferencia."""
    return [comando for comando in PLAYERS_UNIX if existe(comando[0])]


def tocar(caminho: Path) -> None:
    """Toca e so retorna no fim, ou quando a tarefa que chamou e encerrada."""
    if sys.platform == "win32":
        tocar_no_windows(caminho)
        return
    tocar_no_unix(caminho)


def tocar_no_windows(caminho: Path) -> None:
    script = PLAYER.format(uri=caminho.resolve().as_uri())
    feito = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True,
    )
    if feito.returncode != 0 and feito.stderr.strip():
        print(f"[aviso] player embutido falhou: {feito.stderr.strip()[:200]}",
              file=sys.stderr)


def tocar_no_unix(caminho: Path) -> None:
    for comando in players_disponiveis():
        try:
            # sem stdin: player nenhum daqui le teclado, e mpv e gst-play leriam
            subprocess.run(comando + [str(caminho)], check=True,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (OSError, subprocess.CalledProcessError):
            continue

    if abrir_no_sistema(caminho):
        print("[aviso] sem player de linha de comando: o audio foi para o programa "
              "padrao do sistema, que nao para junto com esta tarefa. Para o "
              f"silencio voltar a ser seu, instale um destes: {NOMES}.",
              file=sys.stderr)
        return
    print(f"[aviso] nada tocou o audio, que esta em {caminho}. "
          f"Instale um destes: {NOMES}.", file=sys.stderr)


def abrir_no_sistema(caminho: Path) -> bool:
    """Entrega o arquivo ao programa de audio do usuario e volta na hora.

    Devolve False quando ninguem abriu: sem o abridor, sem programa associado ao
    MP3, ou sem sessao grafica. Silencio calado e o pior desfecho possivel, entao
    cada um desses casos sai com o aviso que diz o que fazer.
    """
    if sys.platform == "win32":
        try:
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        except OSError as err:
            print(f"[aviso] o Windows nao abriu {caminho}: {err}", file=sys.stderr)
            return False
        return True

    abridor = "open" if sys.platform == "darwin" else "xdg-open"
    if shutil.which(abridor) is None:
        print(f"[aviso] nao achei {abridor}; o audio esta em {caminho}. "
              f"Num Linux sem ele, o jeito e um player: {NOMES}.", file=sys.stderr)
        return False

    try:
        processo = subprocess.Popen(
            [abridor, str(caminho)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        # o abridor sai assim que entrega; se prende, e porque o programa de audio
        # esta pendurado nele, e ai matar a espera mataria o som junto
        _, erro = processo.communicate(timeout=5)
    except OSError as err:
        print(f"[aviso] {abridor} falhou: {err}", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        return True

    if processo.returncode == 0:
        return True

    ultima = (erro or "").strip().splitlines()
    print(f"[aviso] {abridor} saiu com {processo.returncode}; o audio esta em "
          f"{caminho}." + (f" {ultima[-1][:160]}" if ultima else ""), file=sys.stderr)
    if sys.platform != "darwin":
        print("[aviso] " + (
            "nenhum programa esta associado a MP3. Um comando resolve: "
            "xdg-mime default <programa>.desktop audio/mpeg"
            if tem_tela() else
            f"a sessao nao tem tela: num servidor, num container ou no WSL, so um "
            f"player de linha de comando toca ({NOMES})"), file=sys.stderr)
    return False


def tem_tela() -> bool:
    """Sem DISPLAY nem WAYLAND_DISPLAY, o xdg-open nao tem para onde abrir."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
