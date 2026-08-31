#!/usr/bin/env python3
"""Hook SessionStart: pede ao Claude que narre um roteiro de cada resposta.

O hook injeta instrucao, e nunca sintetiza nada: quem escreve o roteiro falado
da resposta e o Claude, e e o roteiro que vai para o audio. Resposta crua daria
caminho de arquivo, flag e nome de variavel lidos em voz alta.

O interruptor e o arquivo sentinela (python narrar.py on/off); sem ele o hook
sai calado, porque o stdout do SessionStart entra no contexto da sessao.

O texto injetado mora no narrar.py, que tambem o imprime ao ligar a narracao no
meio da sessao.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import narrar  # noqa: E402


def main() -> None:
    if not config.SENTINELA.exists():
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # stdout substituido ou sem encoding
        pass
    print(narrar.instrucao())


if __name__ == "__main__":
    main()
