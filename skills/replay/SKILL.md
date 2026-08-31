---
name: replay
description: Abre de novo uma narração já gerada, escolhida numa lista das últimas, no programa de áudio do computador. Use quando o usuário pedir para ouvir de novo, repetir um áudio, "toca aquele áudio", "põe de novo a última narração", ou quiser rever o que já foi narrado para escutar. Não gera áudio novo nem gasta créditos.
user-invocable: true
---

# Ouvir de novo uma narração

Três passos, sem explicação no meio. O áudio já existe: nada aqui chama a API.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/speak.py" --historico 4
python3 "${CLAUDE_PLUGIN_ROOT}/speak.py" --abrir 2
```

Os scripts ficam na raiz do plugin: `${CLAUDE_PLUGIN_ROOT}`. Se a variável não
estiver no ambiente do seu shell, a raiz é o diretório dois níveis acima do
"Base directory for this skill" mostrado no topo desta skill. Cite o caminho
entre aspas: em algumas instalações ele contém espaços. Onde `python3`
não existir, chame `python`: em algumas máquinas Windows esse é o único nome.

## Entre um comando e outro: o seletor

Ofereça as narrações com `AskUserQuestion`, no máximo quatro, da mais recente
para a mais antiga. No rótulo, a origem enxuta (o nome do arquivo sem extensão,
ou o começo do texto); na descrição, a data, a hora e a duração em minutos e
segundos. O número da opção é o mesmo número da lista, que é o que `--abrir`
recebe.

Pule o seletor quando o pedido já disser qual: "a última" é `--abrir 1`, e um
número dito pelo usuário vai direto.

Histórico vazio é uma linha de resposta, não um seletor: nada foi narrado ainda.

## Depois de abrir

O comando entrega o arquivo ao programa de áudio do computador e volta na hora.
Diga em uma linha o que abriu. A reprodução passa a ser dele: pausa, barra e
volume são do programa, e fechar a janela encerra. Não há nada para interromper
deste lado, e nenhum crédito foi gasto.

Se a saída disser que o áudio saiu do disco, repasse isso: o histórico guarda as
últimas 50 narrações e apaga o som das que saem.
