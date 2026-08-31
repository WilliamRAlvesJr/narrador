#!/usr/bin/env python3
"""Liga e desliga a narracao automatica das respostas do Claude.

O interruptor e um arquivo sentinela na pasta de dados, lido pelo hook
SessionStart: por isso a mudanca so vale na proxima sessao. Onde esse arquivo
fica e decisao do config.py, nunca deste script.

A instrucao que o Claude segue quando a narracao esta ligada mora aqui, e nao
no hook, porque dois caminhos precisam dela: o hook, no inicio da sessao, e a
skill narrar-respostas, que liga no meio da sessao e imprime o mesmo texto com
--instrucao. Uma fonte so evita as duas versoes divergirem.

Uso: python narrar.py [on|off|--instrucao]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

USO = "Uso: python narrar.py [on|off]"

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

DESLIGA_NA_SESSAO = (
    "[narrador] Narração automática das respostas: DESLIGADA nesta sessão.\n\n"
    "Pare de narrar as respostas a partir de agora, mesmo que a instrução de\n"
    "narrar já esteja no contexto desta sessão. Continue narrando apenas quando\n"
    "o usuário pedir explicitamente uma narração ou uma aula."
)


def instrucao() -> str:
    """O texto que o hook injeta no inicio da sessao, com o caminho ja resolvido."""
    return INSTRUCAO.format(speak=ROOT / "speak.py")


def estado() -> str:
    return "LIGADA" if config.SENTINELA.exists() else "DESLIGADA"


def ligar() -> int:
    try:
        config.SENTINELA.parent.mkdir(parents=True, exist_ok=True)
        config.SENTINELA.touch()
    except OSError as err:
        print(f"Nao consegui criar {config.SENTINELA}: {err}", file=sys.stderr)
        return 1
    print("Narracao automatica LIGADA a partir da proxima sessao do Claude Code.")
    print("Para valer ja nesta sessao, rode: python narrar.py --instrucao")
    return 0


def desligar() -> int:
    try:
        config.SENTINELA.unlink(missing_ok=True)
    except OSError as err:
        print(f"Nao consegui remover {config.SENTINELA}: {err}", file=sys.stderr)
        return 1
    print("Narracao automatica DESLIGADA a partir da proxima sessao do Claude Code.")
    print(DESLIGA_NA_SESSAO)
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    argumentos = sys.argv[1:]
    if not argumentos:
        print(f"Narracao automatica: {estado()}")
        print(USO)
        print(f"Sentinela: {config.SENTINELA}")
        return 0

    acao = argumentos[0].lower()
    if acao == "on":
        return ligar()
    if acao == "off":
        return desligar()
    if acao == "--instrucao":
        print(instrucao())
        return 0

    print(f"Argumento desconhecido: {argumentos[0]}\n{USO}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
