#!/usr/bin/env python3
"""Liga e desliga a narracao automatica das respostas do Claude.

O interruptor e um arquivo sentinela na pasta de dados, lido pelo hook
SessionStart. Onde esse arquivo fica e decisao do config.py, nunca deste script.

A sentinela sozinha decide as proximas sessoes; a que esta em andamento muda
porque `on` e `off` imprimem tambem o texto que passa a valer, e a skill manda o
Claude segui-lo. Esse texto mora aqui, e nao no hook, porque os dois caminhos
precisam do mesmo: uma fonte so evita versoes divergentes.

Uso: python narrar.py [on|off]
"""

from __future__ import annotations

import os
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
2. Rode **em segundo plano** (run_in_background), nunca no turno:
   python "{speak}" "<o arquivo do roteiro>"
   Assim a narração vira uma tarefa que o usuário encerra quando quiser, e o
   turno não fica preso pelo tempo do áudio. Encerrar a tarefa corta o som.

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
    """Liga, e imprime de uma vez tudo o que quem chamou precisa saber."""
    config.carregar_env()
    if not os.environ.get("ELEVENLABS_API_KEY", "").strip():
        print("Narracao automatica NAO ligada: falta a chave da ElevenLabs.")
        print(config.instrucao_da_chave(), file=sys.stderr)
        return 1

    try:
        config.SENTINELA.parent.mkdir(parents=True, exist_ok=True)
        config.SENTINELA.touch()
    except OSError as err:
        print(f"Nao consegui criar {config.SENTINELA}: {err}", file=sys.stderr)
        return 1

    print("Narracao automatica LIGADA.")
    print(instrucao())
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
    print(f"Argumento desconhecido: {argumentos[0]}\n{USO}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
