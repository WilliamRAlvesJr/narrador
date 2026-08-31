#!/usr/bin/env python3
"""Hook SessionStart: pede ao Claude que narre um roteiro de cada resposta.

A narracao automatica antiga era um hook Stop: pegava a resposta pronta,
limpava a marcacao e mandava para a API. Sem modelo no caminho, caminho de
arquivo, flag e nome de variavel iam para o audio como estao, e quem ouvia
recebia o texto da tela lido em voz alta.

Aqui o trabalho volta para o Claude: em vez de narrar a resposta, ele escreve
um roteiro falado dela e narra o roteiro. O interruptor continua sendo o
arquivo sentinela (python narrar.py on/off); sem ele o hook sai calado, porque
o stdout do SessionStart entra no contexto da sessao.

O texto injetado mora no narrar.py, que tambem o imprime com --instrucao quando
a skill liga a narracao no meio da sessao.
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
