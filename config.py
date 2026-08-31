"""Onde ficam a chave, o audio gerado e o cache.

Como plugin, o codigo roda de dentro do cache do Claude Code, que e reescrito a
cada atualizacao. Nada que o usuario precise manter pode morar la: chave, saida e
cache vao para a pasta de dados, fora do plugin.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def pasta_de_dados() -> Path:
    """~/.claude/narrador, ou o que NARRADOR_HOME apontar."""
    escolhida = os.environ.get("NARRADOR_HOME")
    if escolhida:
        return Path(escolhida).expanduser()
    return Path.home() / ".claude" / "narrador"


DADOS = pasta_de_dados()
OUT_DIR = DADOS / "out"
CACHE_DIR = DADOS / "cache-audio"
SENTINELA = DADOS / "narrar-respostas"


def arquivos_de_env() -> list[Path]:
    """Do mais especifico ao mais geral; o primeiro que definir a chave vence."""
    return [DADOS / ".env", RAIZ / ".env"]


def carregar_env() -> None:
    """Le os arquivos .env sem sobrescrever o que ja veio do ambiente."""
    for arquivo in arquivos_de_env():
        if not arquivo.is_file():
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            valor = valor.strip().strip('"').strip("'")
            # valor vazio nao define nada: senao o .env semeado, ainda sem chave,
            # bloquearia o proximo arquivo da lista
            if not valor:
                continue
            os.environ.setdefault(chave.strip(), valor)


def onde_por_a_chave() -> str:
    return str(DADOS / ".env")


def instrucao_da_chave() -> str:
    """A frase que o usuario precisa ler: criar o .env, ou so preencher."""
    destino = DADOS / ".env"
    if destino.is_file():
        return f"Preencha ELEVENLABS_API_KEY=sk_... em {destino}."
    return (
        f"Crie {destino} com ELEVENLABS_API_KEY=sk_... "
        f"(modelo em {RAIZ / '.env.example'}) ou exporte a variavel."
    )


EXEMPLO = RAIZ / ".env.example"


def semear_env() -> Path | None:
    """Copia o .env.example para a pasta de dados na primeira vez.

    Chamado pelo hook SessionStart: e o mais perto de "na instalacao" que um
    plugin alcanca, ja que o codigo so roda quando o Claude Code abre a sessao.
    Devolve o caminho criado, ou None se ja havia .env, se a chave veio do
    ambiente, ou se nada pode ser escrito. Nunca sobrescreve.
    """
    destino = DADOS / ".env"
    if destino.exists() or os.environ.get("ELEVENLABS_API_KEY", "").strip():
        return None
    if not EXEMPLO.is_file():
        return None
    try:
        DADOS.mkdir(parents=True, exist_ok=True)
        destino.write_text(EXEMPLO.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        return None
    return destino


STATUSLINE = RAIZ / "statusline.py"


def sincronizar_statusline() -> Path | None:
    """Mantem uma copia do statusline.py na pasta de dados.

    A barra de estado guarda o caminho do comando no settings.json do usuario, e
    o caminho do plugin no cache leva a versao no nome: apontar para la quebraria
    a barra a cada atualizacao. A copia mora num caminho estavel e e reescrita
    quando o plugin muda. Devolve o destino quando escreveu, senao None.
    """
    destino = DADOS / "statusline.py"
    try:
        conteudo = STATUSLINE.read_bytes()
    except OSError:
        return None
    try:
        if destino.is_file() and destino.read_bytes() == conteudo:
            return None
        DADOS.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    except OSError:
        return None
    return destino


# --------------------------------------------------------------------------- #
# checagem, chamada pelas skills antes de escrever o roteiro
# --------------------------------------------------------------------------- #
CAMPOS = [
    ("ELEVENLABS_VOICE_ID", "voz"),
    ("ELEVENLABS_MODEL_ID", "modelo"),
    ("ELEVENLABS_LANGUAGE", "idioma"),
    ("ELEVENLABS_SPEED", "velocidade"),
    ("ELEVENLABS_SENTENCE_PAUSE", "pausa"),
]


def checar() -> int:
    """Imprime a configuracao e devolve 0 se da para narrar, 1 se falta a chave.

    Nunca imprime a chave: so se ela existe e de onde a configuracao veio.
    """
    carregar_env()
    lidos = [str(a) for a in arquivos_de_env() if a.is_file()]

    print(f"dados: {DADOS}")
    print(f".env lido: {', '.join(lidos) if lidos else 'nenhum'}")
    for var, rotulo in CAMPOS:
        valor = os.environ.get(var)
        print(f"{rotulo}: {valor if valor else 'padrao do script'}")

    if not os.environ.get("ELEVENLABS_API_KEY", "").strip():
        print("chave: AUSENTE")
        print(instrucao_da_chave())
        return 1

    print("chave: definida")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(checar())
