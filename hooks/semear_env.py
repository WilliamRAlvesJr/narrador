#!/usr/bin/env python3
"""Hook SessionStart: deixa a pasta de dados do usuario pronta.

O Claude Code nao roda nada no /plugin install, entao a primeira sessao depois
da instalacao e o momento mais cedo em que o plugin consegue agir. Copia o
.env.example para ~/.claude/narrador/.env quando ainda nao existe nenhum, e
avisa o Claude para pedir a chave. Sem nada a fazer, sai calado: o stdout do
hook entra no contexto da sessao.

Tambem atualiza a copia do statusline.py, que a barra de estado do usuario
executa por um caminho estavel, fora do cache versionado do plugin. A copia e
sempre silenciosa; o convite para ligar a barra sai junto do pedido da chave,
que e a unica vez que este hook fala.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402


def main() -> None:
    config.sincronizar_statusline()
    criado = config.semear_env()
    if not criado:
        return
    print(
        f"[narrador] Criei {criado} a partir do .env.example. "
        "O plugin so narra depois que o usuario preencher ELEVENLABS_API_KEY "
        "nesse arquivo; avise isso quando ele pedir uma narracao ou uma aula."
    )
    sugestao = config.sugestao_da_statusline()
    if sugestao:
        print(f"[narrador] Ofereca tambem, uma vez so, a barra de estado. "
              f"Quem cola no settings e o usuario.\n{sugestao}")


if __name__ == "__main__":
    main()
