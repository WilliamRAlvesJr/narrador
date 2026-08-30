---
name: video-aula
description: Gera uma vídeo-aula narrada com slides e diagramas que acendem no instante em que são falados, publicada como página no claude.ai. Use quando ele pedir uma aula, uma explicação em áudio com visual, slides narrados, "me explica isso com imagem", "faz uma aula sobre", ou quando um assunto for complexo o bastante para que ouvir e ver juntos ajudem mais do que ler.
user-invocable: true
---

# Vídeo-aula narrada

Escreva um roteiro, desenhe os diagramas, gere a página e publique. O áudio usa a
voz do usuário na ElevenLabs; os tempos vêm do endpoint `with-timestamps`, então
cada tópico e cada parte do desenho acende no instante exato da fala.

```powershell
python "${CLAUDE_PLUGIN_ROOT}/aula.py" <roteiro>.aula.md --dry-run
python "${CLAUDE_PLUGIN_ROOT}/aula.py" <roteiro>.aula.md
```

Os scripts ficam na raiz do plugin: `${CLAUDE_PLUGIN_ROOT}`. Se a variável não
estiver no ambiente do seu shell, a raiz é o diretório dois níveis acima do
"Base directory for this skill" mostrado no topo desta skill. Cite o caminho
entre aspas: em algumas instalações ele contém espaços.

Saída: `~/.claude/narrador/out/<nome>.html`, com o áudio embutido (o comando
imprime o caminho). Publique com a ferramenta Artifact
e devolva o link. Para atualizar, republique **o mesmo caminho de arquivo**, que o
link não muda.

## Primeiro comando: cheque a configuração

```powershell
python "${CLAUDE_PLUGIN_ROOT}/config.py"
```

Roda num instante, não chama a API e não gasta crédito. Imprime de onde veio a
configuração, a voz, o modelo, o idioma, a velocidade e se a chave existe.

Se sair `chave: AUSENTE`, **pare antes de escrever o roteiro e as figuras**:
peça ao usuário que preencha a `ELEVENLABS_API_KEY` em `~/.claude/narrador/.env`,
que o plugin já deixou pronto na instalação (o comando imprime o caminho exato),
e só siga quando ele confirmar.
Uma aula é caro de montar para descobrir no fim que não há como gravar.

## O roteiro

Guarde o roteiro **no projeto sobre o qual a aula fala**, não na pasta do
plugin: uma aula sobre outro repositório pertence àquele repositório. Sem
projeto óbvio, use o scratchpad da sessão. Formato:

```markdown
# Título da aula
Uma linha de subtítulo.

## Título do slide
figura: figuras/nome.svg
- Rótulo curto :: Frase completa que será narrada.
- Outro rótulo :: Outra frase, uma ideia por vez.
```

O rótulo à esquerda é o que aparece no slide; o texto à direita é o que se ouve.
Sem `::`, o próprio rótulo é narrado.

Proporções que funcionam: **3 tópicos por slide** (2 a 4), rótulo de até seis
palavras, narração de uma a duas frases. Seis a dez slides numa aula. Escreva a
narração como fala: sem tabela, sem comando, sem endereço de site, números por
extenso. O rótulo é a âncora visual, não o resumo da frase.

## As figuras

Um diagrama por slide sempre que houver um mecanismo: um fluxo, uma decisão, um
antes e depois. Slide sem mecanismo pode ficar sem figura, o layout se ajusta.

Desenhe SVG à mão numa pasta `figuras/` ao lado do roteiro, `viewBox="0 0 560 300"`:

- `fill="none" stroke="currentColor"` no `<svg>`, e **nada de cor literal**: a
  página tem tema claro e escuro, e `currentColor` resolve os dois;
- cada parte ligada a um tópico vai num `<g class="passo" data-passo="0">`, com o
  índice do tópico (0, 1, 2). O grupo acende quando aquele tópico é falado, e
  fica em tom médio depois;
- o que é cenário fixo (a caixa central, uma linha do tempo) fica fora de
  qualquer `passo`, sempre visível;
- rotule as setas (`lê`, `sintetiza`, `erro`), texto de 11 a 14px, sem frase
  longa dentro do desenho;
- nada de `<script>`, `<style>` ou imagem externa dentro do SVG;
- também aceita `.png` e `.jpg`, embutidos automaticamente.

Os SVGs em `roteiros/figuras/` da raiz do plugin são a referência de estilo:
olhe um antes de inventar outro traço.

## Ordem de trabalho

1. `python "<raiz>/config.py"`: chave, voz e idioma no lugar.
2. Escreva o roteiro inteiro antes de gerar nada.
3. Desenhe as figuras e cheque que cada `data-passo` existe no slide certo.
4. `--dry-run`: confira os slides e **diga ao usuário quantos caracteres são**,
   que é quanto vai custar em créditos.
5. Gere, publique como Artifact (favicon e `description` de uma frase) e mande o link.

## Custo e cache

O áudio fica em cache por conteúdo em `~/.claude/narrador/cache-audio/`. Mexer em figura,
layout ou rótulo **não gasta créditos**: só mudar o texto narrado gera cobrança
nova. Então itere no visual à vontade, e pense duas vezes antes de reescrever a
narração.

A página cabe até 16 MB; a 64 kbps isso dá uns dez minutos de áudio. Aula maior
que isso, divida em duas.

## Ritmo é do ouvinte, não da gravação

A barra da página traz velocidade (0,75× a 1,3×), pausa entre tópicos (0 a 3 s) e
volume com mudo. As três escolhas ficam no navegador do viewer, então a próxima
aula abre no ritmo dele. Atalhos: espaço toca e pausa, ← → pulam slide, ↑ ↓ mudam
o volume.

A pausa é silêncio real na reprodução: o áudio para na fronteira do tópico, com
ele já aceso no slide, e volta sozinho. Duas armadilhas ao mexer nisso:

- o acompanhamento roda **quadro a quadro** enquanto toca. Depender só de
  `timeupdate` faz o início sair corrido, porque ele engasga durante o decode do
  áudio embutido e pula fronteiras;
- qualquer avanço de tópico dispara o respiro, nunca o incremento exato de um;
- reaplique a velocidade no `loadedmetadata` e no `play`, e defina também
  `defaultPlaybackRate`: o elemento volta à taxa padrão ao carregar a mídia.

Nunca resolva ritmo na geração:

- as etiquetas `<break>` do `speak.py` entrariam no alinhamento de caracteres e
  desalinhariam os slides, que é o defeito mais caro dessa página;
- mudar a velocidade no `.env` gera áudio novo e cobra créditos de novo, para um
  ajuste que o ouvinte faz num seletor.

## A emenda dos trechos

Cada resposta da API é um MP3 completo, com tag ID3 e frame Xing. Emendados
crus, o player lê o Xing do primeiro trecho, conclui que o arquivo inteiro dura
o tempo daquele trecho e **recusa todo seek além disso**: clicar num slide
adiante não sai do lugar e a fala segue de onde estava.

`mp3.py` resolve: `limpar()` tira ID3 e Xing de cada trecho, `duracao()` conta
frames em vez de estimar por bytes. Se você mexer na montagem do áudio, mantenha
as duas. O `aula.py` avisa quando a emenda medida diverge da soma dos trechos,
que é o sintoma desse defeito voltando.

## Regras

- Voz, modelo, idioma e velocidade da gravação vêm do `.env`. Não passe nada
  disso na linha de comando sem o usuário pedir.
- Se o usuário só quer ouvir, sem visual, use a skill `ler-em-voz-alta`.
- No Bash, caminhos com barra normal; barra invertida escapada some no shell.
- Nunca imprima a `ELEVENLABS_API_KEY`.

O código está em `aula.py` e o layout em `aula_template.html`, na raiz do
plugin. Leia se for mudar o comportamento da página.
