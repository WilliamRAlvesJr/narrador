#!/usr/bin/env python3
"""Linha de estado do Claude Code: pasta, modelo e narracao automatica.

Roda a cada atualizacao da barra, com o contexto da sessao em JSON no stdin, e
imprime uma linha so. Falha nenhuma pode aparecer para o usuario: campo que
faltar simplesmente sai da linha.

Este e o unico arquivo do plugin que repete a regra do config.py sobre onde
fica a pasta de dados. E de proposito: a barra aponta para a copia em
~/.claude/narrador/, fora do plugin, porque o caminho do cache muda a cada
versao instalada e quebraria a configuracao do usuario. La ele roda sozinho,
sem o config.py ao lado, entao precisa saber achar a sentinela por conta.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SENTINELA = "narrar-respostas"


def pasta_de_dados() -> Path:
    escolhida = os.environ.get("NARRADOR_HOME")
    if escolhida:
        return Path(escolhida).expanduser()
    return Path.home() / ".claude" / "narrador"


def contexto() -> dict:
    """O JSON que o Claude Code manda no stdin, ou vazio se nao vier nada."""
    try:
        return json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return {}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ctx = contexto()
    partes: list[str] = []

    pasta = (ctx.get("workspace") or {}).get("current_dir") or os.getcwd()
    if pasta:
        partes.append(Path(pasta).name)

    modelo = (ctx.get("model") or {}).get("display_name")
    if modelo:
        partes.append(str(modelo))

    ligada = (pasta_de_dados() / SENTINELA).exists()
    partes.append("\U0001F50A narrando" if ligada else "\U0001F507 sem narrar")

    print(" | ".join(partes))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # barra quebrada e pior que barra pobre
        print("")
