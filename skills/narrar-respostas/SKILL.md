---
name: narrar-respostas
description: Liga e desliga a narração automática das respostas, em que o Claude narra um roteiro falado de cada resposta de substância. Use quando o usuário pedir para "narrar tudo", "ler todas as respostas em voz alta", "ligar/desligar a narração automática", "para de narrar", "volta a narrar", ou quiser saber se ela está ligada.
user-invocable: true
---

# Narração automática das respostas

O interruptor é um arquivo sentinela na pasta de dados do usuário, lido pelo hook
`SessionStart`. Mexer nele resolve as próximas sessões; esta sessão só muda porque
os comandos abaixo também imprimem a instrução que vale agora. Rode os dois passos,
nunca só o primeiro.

Os scripts ficam na raiz do plugin: `${CLAUDE_PLUGIN_ROOT}`. Se a variável não
estiver no ambiente do seu shell, a raiz é o diretório dois níveis acima do
"Base directory for this skill" mostrado no topo desta skill. Cite o caminho
entre aspas: em algumas instalações ele contém espaços.

## Sem instrução explícita: mostre o seletor

Se o usuário não disse qual estado quer ("liga", "desliga"), não adivinhe nem
pergunte em texto corrido. Leia o estado atual e ofereça a escolha com a
ferramenta `AskUserQuestion`, duas opções, a atual em primeiro lugar:

- **Ligada**: o Claude narra um roteiro falado de cada resposta de substância
- **Desligada**: só narra quando você pedir

Rotule a opção vigente com "(atual)" na descrição, para ele ver onde está antes
de escolher. Depois aplique a escolha pelos passos abaixo. Se a escolha for a
que já vale, diga isso em uma linha e não rode nada.

## Ligar

```powershell
python "${CLAUDE_PLUGIN_ROOT}/config.py"
python "${CLAUDE_PLUGIN_ROOT}/narrar.py" on
python "${CLAUDE_PLUGIN_ROOT}/narrar.py" --instrucao
```

A checagem vem primeiro porque narração ligada sem `ELEVENLABS_API_KEY` falha em
toda resposta: se sair `chave: AUSENTE`, diga isso e não ligue.

O último comando imprime as regras do roteiro falado. **Siga-as até o fim desta
sessão**, começando pela sua próxima resposta de substância.

## Desligar

```powershell
python "${CLAUDE_PLUGIN_ROOT}/narrar.py" off
```

A saída manda parar de narrar nesta sessão. Obedeça mesmo que a instrução de
narrar já esteja no seu contexto, vinda do início da sessão: ela foi revogada.

## Estado

```powershell
python "${CLAUDE_PLUGIN_ROOT}/narrar.py"
```

Imprime `LIGADA` ou `DESLIGADA` e o caminho da sentinela, sem mudar nada.

## O que dizer ao usuário

Uma linha: o novo estado e que ele vale já nesta sessão. Se ele ligou, avise que
cada resposta narrada consome créditos da ElevenLabs, e que confirmação curta e
resposta de uma linha continuam sem áudio.
