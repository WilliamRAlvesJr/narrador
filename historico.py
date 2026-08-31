#!/usr/bin/env python3
"""Historico das narracoes: o que foi lido, quando, e o audio para ouvir de novo.

Uma linha JSON por narracao, do mais antigo para o mais recente, ao lado dos
arquivos em out/. Serve para tocar de novo sem gastar credito e para saber o que
o Claude narrou enquanto voce estava longe da tela.

A pasta nao cresce sem limite: podar mantem as ultimas NARRADOR_HISTORICO_MAX
narracoes (50 por padrao) e apaga o audio das que sairam.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

ARQUIVO = config.DADOS / "historico.jsonl"


def maximo() -> int:
    try:
        return max(1, int(os.environ.get("NARRADOR_HISTORICO_MAX", "50")))
    except ValueError:
        return 50


def ler() -> list[dict]:
    """Do mais antigo para o mais recente; linha corrompida e ignorada."""
    if not ARQUIVO.is_file():
        return []
    itens = []
    try:
        linhas = ARQUIVO.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        try:
            itens.append(json.loads(linha))
        except ValueError:
            continue
    return itens


def escrever(itens: list[dict]) -> None:
    try:
        config.DADOS.mkdir(parents=True, exist_ok=True)
        ARQUIVO.write_text(
            "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in itens),
            encoding="utf-8",
        )
    except OSError:
        pass


def registrar(arquivo: Path, origem: str, caracteres: int, duracao: float,
              voz: str, modelo: str, velocidade: float) -> None:
    """Anota a narracao e poda o que passou do limite. Nunca interrompe quem chama."""
    itens = ler()
    itens.append({
        "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo": str(arquivo),
        "origem": origem,
        "caracteres": caracteres,
        "duracao": round(duracao, 1),
        "voz": voz,
        "modelo": modelo,
        "velocidade": velocidade,
    })
    escrever(podar(itens))


def podar(itens: list[dict]) -> list[dict]:
    """Deixa so as ultimas narracoes, apagando o audio das que sairam."""
    limite = maximo()
    if len(itens) <= limite:
        return itens
    for velho in itens[:-limite]:
        try:
            Path(velho.get("arquivo", "")).unlink(missing_ok=True)
        except OSError:
            pass
    return itens[-limite:]


def recentes(quantos: int = 20) -> list[dict]:
    """Do mais recente para o mais antigo, que e a ordem em que se procura."""
    return list(reversed(ler()))[:max(1, quantos)]


def item(posicao: int) -> dict | None:
    """A narracao numero N contando do fim: 1 e a ultima."""
    todos = list(reversed(ler()))
    if posicao < 1 or posicao > len(todos):
        return None
    return todos[posicao - 1]


def formatar(itens: list[dict]) -> str:
    """A listagem que o usuario le: numero, quando, duracao e de onde veio."""
    if not itens:
        return "Nenhuma narracao no historico ainda."
    linhas = []
    for numero, i in enumerate(itens, 1):
        minutos, segundos = divmod(int(i.get("duracao", 0) + 0.5), 60)
        existe = "" if Path(i.get("arquivo", "")).is_file() else "  (audio apagado)"
        linhas.append(f"{numero:>3}. {i.get('quando', '?')}  {minutos}:{segundos:02d}  "
                      f"{i.get('origem', '?')}{existe}")
    return "\n".join(linhas)
