#!/usr/bin/env python3
"""Hook SessionStart: deixa o .env pronto na pasta de dados do usuario.

O Claude Code nao roda nada no /plugin install, entao a primeira sessao depois
da instalacao e o momento mais cedo em que o plugin consegue agir. Copia o
.env.example para ~/.claude/narrador/.env quando ainda nao existe nenhum, e
avisa o Claude para pedir a chave. Sem nada a fazer, sai calado: o stdout do
hook entra no contexto da sessao.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402


def main() -> None:
    criado = config.semear_env()
    if not criado:
        return
    print(
        f"[narrador] Criei {criado} a partir do .env.example. "
        "O plugin so narra depois que o usuario preencher ELEVENLABS_API_KEY "
        "nesse arquivo; avise isso quando ele pedir uma narracao ou uma aula."
    )


if __name__ == "__main__":
    main()
