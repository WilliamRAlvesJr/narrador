---
name: narrar-respostas
description: Liga e desliga a narração automática das respostas, em que o Claude narra um roteiro falado de cada resposta de substância. Use quando o usuário pedir para "narrar tudo", "ler todas as respostas em voz alta", "ligar/desligar a narração automática", "para de narrar", "volta a narrar", ou quiser saber se ela está ligada.
user-invocable: true
---

# Narração automática das respostas

Um comando, uma linha de resposta. Não explique o mecanismo, não confirme antes,
não pergunte nada quando o estado pedido veio junto ("liga", "desliga").

```powershell
python "${CLAUDE_PLUGIN_ROOT}/narrar.py" on      # ligar
python "${CLAUDE_PLUGIN_ROOT}/narrar.py" off     # desligar
python "${CLAUDE_PLUGIN_ROOT}/narrar.py"         # só ver o estado
```

Os scripts ficam na raiz do plugin: `${CLAUDE_PLUGIN_ROOT}`. Se a variável não
estiver no ambiente do seu shell, a raiz é o diretório dois níveis acima do
"Base directory for this skill" mostrado no topo desta skill. Cite o caminho
entre aspas: em algumas instalações ele contém espaços.

## O que fazer com a saída

Ligar imprime a confirmação e, logo abaixo, as regras do roteiro falado: **siga
essas regras até o fim desta sessão**, a partir da sua próxima resposta de
substância. Desligar imprime a revogação: pare de narrar, mesmo que a ordem
antiga ainda esteja no seu contexto.

Ligar sem a chave da ElevenLabs não liga nada, e a saída diz o que falta; repasse
essa linha e pare por aí.

## Sem estado explícito no pedido

Só então ofereça a escolha com `AskUserQuestion`, duas opções, a atual em
primeiro lugar e marcada com "(atual)": **Ligada** narra um roteiro falado de
cada resposta de substância, **Desligada** narra só quando ele pedir. Leia o
estado com o comando sem argumento antes de perguntar.

## O que dizer ao usuário

Uma linha: o novo estado, e que vale já nesta sessão. Nada além disso.
