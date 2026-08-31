#!/usr/bin/env python3
"""Hook SessionStart: pede ao Claude que narre um roteiro de cada resposta.

A narracao automatica antiga era um hook Stop: pegava a resposta pronta,
limpava a marcacao e mandava para a API. Sem modelo no caminho, caminho de
arquivo, flag e nome de variavel iam para o audio como estao, e quem ouvia
recebia o texto da tela lido em voz alta.

Aqui o trabalho volta para o Claude: em vez de narrar a resposta, ele escreve
um roteiro falado dela e narra o roteiro. O interruptor continua sendo o
arquivo sentinela (narrar.cmd on/off); sem ele o hook sai calado, porque o
stdout do SessionStart entra no contexto da sessao.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

INSTRUCAO = """\
[narrador] Narração automática das respostas: LIGADA nesta sessão.

Ao terminar uma resposta de substância, narre-a como último passo do turno:

1. Escreva um roteiro falado num arquivo .md temporário (use o scratchpad da sessão).
2. Rode, com timeout de 600 s:
   python "{speak}" "<o arquivo do roteiro>"
   O comando só retorna quando o áudio acaba; não o interrompa achando que travou.

O roteiro não é a resposta: é o que sobra dela quando só existe o ouvido. Prosa
corrida, uma ideia por frase, no máximo uns 900 caracteres. Fora caminho de
arquivo, flag, comando, nome de variável, bloco de código, tabela e endereço de
site: no lugar deles, diga o que a coisa faz. Se o que restar não fizer sentido
sem a tela, narre só a conclusão. A skill ler-em-voz-alta tem as regras completas.

Não narre confirmação curta, pergunta de uma linha, resposta que é só um comando,
nem resposta em que o próprio usuário já pediu uma narração ou uma aula, que já
sai em áudio pela skill.

Cada narração consome créditos da ElevenLabs. Se a síntese falhar, diga o motivo
em uma linha e siga; nunca repita a chamada por conta própria.\
"""


def main() -> None:
    if not config.SENTINELA.exists():
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # stdout substituido ou sem encoding
        pass
    print(INSTRUCAO.format(speak=ROOT / "speak.py"))


if __name__ == "__main__":
    main()
