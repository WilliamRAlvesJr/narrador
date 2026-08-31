---
name: ler-em-voz-alta
description: Narra um texto em áudio com a voz do usuário na ElevenLabs. Use quando ele pedir para ler em voz alta, narrar, falar, escutar, ouvir, "me lê isso", "lê pra mim" ou "gera o áudio disso", seja de um arquivo .md/.txt/.html, de um trecho colado, ou de um resumo que você mesmo escreveu; e quando perguntar o que já foi narrado. Para repetir um áudio antigo, a skill é replay.
user-invocable: true
---

# Ler em voz alta

Gere o áudio com o script abaixo. Nunca "leia" imitando fala no chat: o pedido é por som.

```powershell
python "${CLAUDE_PLUGIN_ROOT}/speak.py" <arquivo-ou-texto>
```

Os scripts ficam na raiz do plugin: `${CLAUDE_PLUGIN_ROOT}`. Se a variável não
estiver no ambiente do seu shell, a raiz é o diretório dois níveis acima do
"Base directory for this skill" mostrado no topo desta skill. Cite o caminho
entre aspas: em algumas instalações ele contém espaços.

Aceita `.md`, `.markdown`, `.txt`, `.html`, `.htm` (formato detectado pela extensão),
texto literal, ou `-` para stdin. O script extrai o texto puro (remove tags HTML,
blocos de código, links e marcação Markdown), quebra em chunks, sintetiza, guarda
o áudio e toca.

O comando só retorna quando a narração termina, e um `.md` de 2000 caracteres
leva uns dois minutos: por isso ele nunca roda dentro do turno.

## Rode sempre em segundo plano

A narração vai para uma tarefa de segundo plano (`run_in_background`), nunca
dentro do turno. São duas razões: o turno não fica preso pelos minutos de áudio,
e a tarefa aparece na lista do Claude Code, onde o usuário a encerra sozinho
quando quiser silêncio. Encerrar a tarefa derruba o player junto.

Não existe pausar, avançar nem interromper por comando: quem para é ele, na
tarefa.

O áudio de cada narração fica guardado, e a lista do que já foi narrado sai com:

```powershell
python "${CLAUDE_PLUGIN_ROOT}/speak.py" --historico
```

Cada linha traz data, duração e origem.

## Ouvir de novo

Pedido de repetir um áudio já narrado é da skill `replay`, que lista as últimas e
abre a escolhida no programa de áudio do computador. Não sintetize de novo o
mesmo texto.

## Primeiro comando: cheque a configuração

```powershell
python "${CLAUDE_PLUGIN_ROOT}/config.py"
```

Roda num instante, não chama a API e não gasta crédito. Imprime de onde veio a
configuração, a voz, o modelo, o idioma, a velocidade e se a chave existe.

Se sair `chave: AUSENTE`, **pare antes de escrever o roteiro**: peça ao usuário
que preencha a `ELEVENLABS_API_KEY` em `~/.claude/narrador/.env`, que o plugin
já deixou pronto na instalação (o comando imprime o caminho exato), e só siga
quando ele confirmar. Escrever o roteiro primeiro
joga fora o trabalho e adia o único problema que trava tudo.

Se a voz ou o idioma não forem os que o usuário espera, quem manda é o `.env`
dele: aponte a divergência e deixe ele corrigir, não passe flag na linha de comando.

## Antes de narrar: escreva o roteiro

Documento técnico foi escrito para os olhos. Tabela, flag, caminho de arquivo,
bloco de código e URL viram ruído no áudio, e o ouvinte não pode voltar atrás.

Quando o alvo for README, documentação, changelog, código, ou qualquer texto
estruturado, **não narre o arquivo original**. Escreva antes um roteiro falado em
`<scratchpad>/roteiro-<nome>.md` e narre esse arquivo:

- prosa corrida, frases curtas, uma ideia por frase;
- números e símbolos por extenso: "nove décimos", não "0.9";
- tabela vira frase, lista vira enumeração falada;
- comando, flag, caminho e URL saem, ou viram a descrição do que fazem;
- diga o que a coisa faz, não como se digita.

Diga ao usuário que narrou o roteiro e quantos caracteres foram, ele economiza
créditos. Só narre o arquivo original se ele pedir a leitura literal.

Texto que já é prosa (uma nota, um e-mail, um trecho colado) vai direto, sem roteiro.

Se o assunto pede imagem junto da voz (um mecanismo, um fluxo, uma comparação),
a skill `video-aula` gera slides com diagramas sincronizados com a fala.

## Casos

| Pedido | Comando |
| --- | --- |
| Ler um documento técnico | escreva o roteiro falado e narre o roteiro |
| Ler um arquivo de prosa | `python "<raiz>/speak.py" docs/notas.md` |
| Ler um texto seu, escrito na hora | `... /speak.py --text "o deploy terminou"` |
| Ler algo longo, ou com aspas e acentos | salve num arquivo do scratchpad e passe o caminho |
| Guardar o áudio | já é o padrão: fica em `out/` e no histórico |
| Narrar sem deixar arquivo | `... /speak.py notas.md --sem-historico` |
| Só gerar, sem tocar | `... /speak.py notas.md --no-play --out saida.mp3` |
| Ver o que será falado e a config | `... /speak.py notas.md --dry-run` |
| Ver vozes da conta | `... /speak.py --list-voices` |
| Conferir chave e voz configuradas | `python "<raiz>/config.py"` |

## Regras

- **Não passe `--voice`, `--model`, `--language` nem `--speed`** sem o usuário pedir.
  Esses valores vêm do `.env` do usuário, em `~/.claude/narrador/.env`. Sobrepor
  é o caminho para narrar com a voz ou o idioma errados.
- Antes de narrar um documento longo, rode `--dry-run` e diga quantos caracteres são.
  Cada caractere consome um crédito da conta.
- Para narrar um resumo, escreva o resumo num `.md` do scratchpad e leia o arquivo.
  Texto direto no `--text` quebra fácil no quoting do PowerShell.
- Escreva o texto a narrar como se fala: sem tabelas, sem trechos de código, sem URLs.
  Marcação sobrevive à extração e vira ruído no áudio.
- Nunca imprima a `ELEVENLABS_API_KEY`.
- No Bash use caminhos com barra normal. Barra invertida escapada some no shell
  e o arquivo não é encontrado.

## Quando der erro

- `402 paid_plan_required`: a conta caiu para o plano free e a voz é da Voice Library.
  Reporte, não troque de voz por conta própria.
- `401`: chave inválida ou sem o escopo **Text to Speech**.
- `ELEVENLABS_API_KEY nao definida`: peça ao usuário que preencha o `.env` que a
  própria mensagem de erro aponta. Não invente chave.
  Rodar `config.py` antes do roteiro evita chegar até aqui.
- Saiu no idioma ou na voz errada: rode `--dry-run` e confira a linha de config
  contra o `.env`.

O código, as flags e os detalhes de implementação estão no `CLAUDE.md` e no
`README.md` da raiz do plugin. Leia se for mexer no script.
