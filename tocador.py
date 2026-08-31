#!/usr/bin/env python3
"""Reproducao do audio: com controles de teclado, e sempre interrompivel.

Duas situacoes diferentes moram aqui. Quando o usuario roda o script no
terminal dele, existe teclado: espaco pausa, as setas pulam e mudam o volume, q
encerra. Quando quem roda e o Claude, dentro de uma sessao, nao ha teclado nenhum
e o audio so termina sozinho; por isso o processo que toca anota o proprio PID,
e um `speak.py --parar` de qualquer outro lugar corta a narracao.

Nao confundir com o player da video-aula, que e o JavaScript do aula_template.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

ESTADO = config.DADOS / "tocando.json"

# --------------------------------------------------------------------------- #
# scripts do player do Windows
# --------------------------------------------------------------------------- #
ABERTURA = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([uri]'{uri}')
$deadline = (Get-Date).AddSeconds(15)
while (-not $player.NaturalDuration.HasTimeSpan -and (Get-Date) -lt $deadline) {{
    Start-Sleep -Milliseconds 100
}}
$player.Play()
"""

# sem teclado: dorme o tempo do audio e sai
SIMPLES = ABERTURA + """
if ($player.NaturalDuration.HasTimeSpan) {{
    Start-Sleep -Seconds ($player.NaturalDuration.TimeSpan.TotalSeconds + 0.6)
}} else {{
    Start-Sleep -Seconds 5
}}
$player.Stop()
$player.Close()
"""

# com teclado: o laco acompanha a posicao e le as teclas sem eco
CONTROLES = ABERTURA + """
Write-Host 'espaco pausa | setas <- -> pulam 5s | ^ v volume | q encerra'
$pausado = $false
$fim = $false
while (-not $fim) {{
    if ([Console]::KeyAvailable) {{
        $tecla = [Console]::ReadKey($true)
        switch ($tecla.Key) {{
            'Spacebar' {{
                if ($pausado) {{ $player.Play() }} else {{ $player.Pause() }}
                $pausado = -not $pausado
            }}
            'RightArrow' {{ $player.Position = $player.Position.Add([TimeSpan]::FromSeconds(5)) }}
            'LeftArrow'  {{ $player.Position = $player.Position.Subtract([TimeSpan]::FromSeconds(5)) }}
            'UpArrow'    {{ $player.Volume = [Math]::Min(1.0, $player.Volume + 0.1) }}
            'DownArrow'  {{ $player.Volume = [Math]::Max(0.0, $player.Volume - 0.1) }}
            'Q'          {{ $fim = $true }}
            'Escape'     {{ $fim = $true }}
        }}
    }}
    if (-not $pausado -and $player.NaturalDuration.HasTimeSpan) {{
        if ($player.Position -ge $player.NaturalDuration.TimeSpan) {{ $fim = $true }}
    }}
    Start-Sleep -Milliseconds 100
}}
$player.Stop()
$player.Close()
"""

PLAYERS_UNIX = (["afplay"], ["mpv", "--no-video"], ["ffplay", "-nodisp", "-autoexit"])


# --------------------------------------------------------------------------- #
# quem esta tocando agora
# --------------------------------------------------------------------------- #
def anotar(pid: int, arquivo: Path) -> None:
    """Deixa o PID em disco para que outro processo consiga parar a narracao."""
    try:
        config.DADOS.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps({
            "pid": pid, "arquivo": str(arquivo), "desde": time.time(),
        }), encoding="utf-8")
    except OSError:
        pass


def esquecer() -> None:
    try:
        ESTADO.unlink(missing_ok=True)
    except OSError:
        pass


def tocando() -> dict | None:
    """O que esta tocando, ou None. Anotacao orfa e limpa na hora."""
    try:
        dados = json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not vivo(int(dados.get("pid", 0))):
        esquecer()
        return None
    return dados


def vivo(pid: int) -> bool:
    """PID de processo vivo e nosso: o sistema recicla numero, entao confere o nome."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        saida = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True,
        )
        linha = saida.stdout.strip().lower()
        return linha.startswith('"powershell') or linha.startswith('"pwsh')
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def parar() -> Path | None:
    """Interrompe a narracao em andamento. Devolve o arquivo que tocava, ou None."""
    dados = tocando()
    if not dados:
        return None
    pid = int(dados["pid"])
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    esquecer()
    return Path(dados.get("arquivo", ""))


# --------------------------------------------------------------------------- #
# reproducao
# --------------------------------------------------------------------------- #
def ha_teclado() -> bool:
    """Console de verdade, com alguem para apertar tecla."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def tocar(caminho: Path, controles: bool | None = None) -> None:
    """Toca e so retorna no fim. controles=None decide pelo terminal."""
    if controles is None:
        controles = ha_teclado()

    if sys.platform == "win32":
        script = (CONTROLES if controles else SIMPLES).format(
            uri=caminho.resolve().as_uri())
        processo = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        anotar(processo.pid, caminho)
        _, erro = processo.communicate()
        esquecer()
        if processo.returncode == 0:
            return
        # matar de proposito nao e falha: so avisa quando o player quebrou
        if processo.returncode not in (1, -1) and erro.strip():
            print(f"[aviso] player embutido falhou: {erro.strip()[:200]}", file=sys.stderr)
        return

    for comando in PLAYERS_UNIX:
        try:
            processo = subprocess.Popen(comando + [str(caminho)],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        anotar(processo.pid, caminho)
        processo.wait()
        esquecer()
        return
    print(f"[aviso] nenhum player encontrado; audio salvo em {caminho}", file=sys.stderr)
