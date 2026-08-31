# narrador

Plugin do Claude Code que lê seus arquivos em voz alta, guarda cada narração para
ouvir de novo, e transforma um assunto em vídeo-aula: slides e diagramas que
acendem no instante exato da fala. A voz vem da ElevenLabs; o código é Python
puro, só stdlib, sem `pip install`.

## Instalação

```
/plugin marketplace add WilliamRAlvesJr/narrador
/plugin install narrador@narrador-marketplace
```

Na primeira sessão depois da instalação o plugin copia o `.env.example` para
`~/.claude/narrador/.env`. Falta só colar a sua chave nele:

```
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=<a voz que você escolheu>
ELEVENLABS_LANGUAGE=pt
ELEVENLABS_SPEED=0.9
```

Para conferir, rode `python3 config.py` na raiz do plugin: ele imprime voz,
modelo, idioma e se a chave existe, sem chamar a API. É o mesmo comando que o
Claude roda antes de escrever um roteiro para narrar.

Requisitos: Python 3.10+, com o interpretador no PATH. Os comandos deste README
usam `python3`; em máquinas Windows onde só existe `python`, é esse o nome. O hook
do plugin resolve os dois sozinho.

A reprodução no Windows usa `System.Windows.Media.MediaPlayer` via PowerShell; em
macOS e Linux tenta `afplay`, `mpv` e `ffplay`, nessa ordem, e sem nenhum deles o
áudio é apenas salvo. `replay` abre o arquivo no `open` (macOS) ou no `xdg-open`
(Linux).

Nada do que você mantém fica dentro do plugin, que é reescrito a cada
atualização: chave, áudio, histórico e cache moram em `~/.claude/narrador/`
(`NARRADOR_HOME` muda o lugar).

## O que ele faz

**`/narrador:ler-em-voz-alta`** narra um arquivo `.md`, `.txt` ou `.html`, um
trecho colado, ou um resumo escrito na hora. Documento técnico não vai direto
para o áudio: o Claude escreve antes um roteiro em prosa, porque tabela, comando
e endereço de site viram ruído quando falados.

**`/narrador:replay`** lista as últimas narrações num seletor e abre a escolhida
no programa de áudio do computador. Não gera áudio novo, nem gasta créditos.

**`/narrador:video-aula`** gera uma página com slides narrados. Cada tópico e
cada parte do diagrama acende no instante em que é dito, usando os tempos por
caractere que a ElevenLabs devolve no endpoint `with-timestamps`. A página sai
com o áudio embutido, pronta para publicar.

**`/narrador:narrar-respostas`** liga e desliga a narração automática, em que o
Claude escreve um roteiro falado de cada resposta de substância e narra o
roteiro. Vem desligada, e também atende em voz corrente ("liga a narração",
"para de narrar").

## Enquanto toca

A narração roda como tarefa de segundo plano do Claude Code, e o player é
processo filho dela: **você para o áudio encerrando essa tarefa**.

Para pausar, voltar ou mudar o volume, use o `replay`: o arquivo abre no seu
programa de áudio, com os controles dele.

## Histórico

Toda narração fica em `~/.claude/narrador/out/`, anotada em `historico.jsonl` com
data, origem, duração e a voz usada. Guarda as últimas 50
(`NARRADOR_HISTORICO_MAX` muda o número) e apaga o áudio das que saem.

```bash
python3 speak.py --historico           # lista as últimas narrações
python3 speak.py --abrir 2             # abre a segunda no player do sistema
```

## Narração automática

O gatilho é o arquivo `~/.claude/narrador/narrar-respostas`: quando ele existe, o
hook `SessionStart` injeta a instrução; sem ele, sai calado. Como a leitura é no
começo da sessão, ligar e desligar imprimem também a instrução que passa a valer,
e a skill manda o Claude segui-la, então a conversa em andamento muda junto.

```
python3 narrar.py on     liga
python3 narrar.py off    desliga
python3 narrar.py        mostra o estado e onde fica a sentinela
```

Confirmação curta e resposta de uma linha não viram áudio, e cada narração
consome créditos.

Para ver o estado o tempo todo, aponte a barra do Claude Code para o
`statusline.py`, no seu `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 \"/home/voce/.claude/narrador/statusline.py\""
}
```

No Windows, `"command": "python \"C:/Users/voce/.claude/narrador/statusline.py\""`.
Troque pelo caminho da sua pasta de dados, escrito por extenso: `python3 narrar.py`
imprime onde ela fica. Nada de `~` aí, que nem todo shell expande.

A barra mostra a pasta, o modelo e `🔊 narrando` ou `🔇 sem narrar`. O arquivo
apontado é a cópia na pasta de dados, que o hook reescreve quando o plugin muda:
o caminho dentro do plugin leva a versão no nome e quebraria na atualização
seguinte.

## Uso direto, sem o Claude

```bash
python3 speak.py notas.md              # extrai, sintetiza e toca
python3 speak.py --text "bom dia"
cat notas.txt | python3 speak.py -
python3 speak.py notas.md --dry-run    # mostra o texto extraído e a config
python3 speak.py --list-voices

python3 aula.py roteiros/narrador.aula.md --dry-run
python3 aula.py roteiros/narrador.aula.md
```

Flags de `speak.py`: `--as md|html|txt`, `--voice`, `--model`, `--format`,
`--speed`, `--language`, `--pause`, `--out`, `--no-play`, `--dry-run`,
`--no-cache`, `--sem-historico`, `--historico`, `--abrir`, `--list-voices`.

Cada trecho sintetizado fica em cache por conteúdo em
`~/.claude/narrador/cache-audio/`, a mesma pasta que a vídeo-aula usa: reler o
mesmo documento não gasta crédito de novo, e `--no-cache` força a síntese. A
chave cobre texto, voz, modelo, formato, velocidade, idioma e os trechos
vizinhos, que a API recebe para não quebrar a prosódia na emenda.

A velocidade é validada antes de qualquer chamada: fora de 0.7 a 1.2, ou com
valor que não é número, o script sai com uma linha dizendo o que corrigir, em vez
de mandar o texto inteiro e receber um 422 da API.

Voz padrão: `JBFqnCBsd6RMkjVDRZzb` (George, a do quickstart da ElevenLabs).
Modelo padrão: `eleven_turbo_v2_5`, o da família v2 que aceita `language_code`;
com `eleven_multilingual_v2` o idioma é adivinhado pelo texto, e um documento com
termos em inglês sai lido com sotaque errado. Ao trocar de modelo o script omite
`language_code` sozinho, que a API rejeitaria.

## Como funciona

1. **Extração**: markdown perde front matter, blocos de código, links e ênfase;
   HTML perde `script`, `style` e tags, com entidades decodificadas.
2. **Chunking**: blocos de até 2500 caracteres (1200 com pausa ligada), sempre em
   fronteira de frase, e cada requisição recebe `previous_text`/`next_text` para
   a prosódia não quebrar na emenda.
3. **Pausas** (só na leitura em voz alta): `ELEVENLABS_SENTENCE_PAUSE=2` vira
   `.<break time="2.0s" />` após cada ponto final de frase, máximo 3 s. Decimais
   e o ponto que encerra o texto são ignorados.
4. **Emenda**: cada resposta da API é um MP3 completo, com ID3 e frame Xing, e o
   player adotaria o Xing do primeiro trecho como duração do arquivo inteiro,
   recusando seek além dele. `mp3.py` limpa os trechos antes de emendar e conta a
   duração frame a frame. Trecho único fica como veio.
5. **Reprodução**: o áudio fica em `out/`, anotado no histórico, e toca. Com
   `--sem-historico` ele é temporário e some depois de tocado. Erro da API não
   deixa arquivo vazio: o destino só é escrito no fim.

## A vídeo-aula

O roteiro fica no projeto sobre o qual a aula fala, e as figuras numa pasta
`figuras/` ao lado dele:

```markdown
## Título do slide
figura: figuras/nome.svg
- Rótulo curto :: Frase completa que será narrada.
```

Nos SVGs, `<g class="passo" data-passo="0">` amarra aquele trecho do desenho ao
primeiro tópico. Use `currentColor`, nunca cor literal: a página segue o tema do
navegador.

Na página, velocidade (0,75× a 1,3×), pausa entre tópicos (0 a 3 s) e volume são
controles do ouvinte, guardados no navegador dele. A pausa é silêncio real na
reprodução, então não custa áudio novo nem interfere na sincronia. Atalhos:
espaço toca e pausa, ← → pulam slide, ↑ ↓ mudam o volume.

O áudio de cada slide fica no mesmo cache por conteúdo da leitura em voz alta,
então ajustar figura ou layout e regerar não consome créditos.

## Testes

```
python3 testes.py
```

São 58, só stdlib, sem rede e sem chave: a síntese é substituída por uma função
de mentira e o MP3 dos testes é montado frame a frame. Cobrem extração,
chunking, pausas, emenda, cache, velocidade, histórico, roteiro da aula, leitura
do `.env`, o interruptor e a barra de estado.

## Estrutura

| Caminho | Papel |
| --- | --- |
| `speak.py` | leitura em voz alta: extração, síntese, emenda e a CLI |
| `tocador.py` | reprodução, e a entrega ao player do sistema |
| `historico.py` | o que foi narrado, e o áudio para ouvir de novo |
| `mp3.py` | limpeza e medição dos trechos de áudio, na leitura e na aula |
| `aula.py`, `aula_template.html` | vídeo-aula com slides sincronizados |
| `config.py` | onde ficam chave, áudio, histórico e cache, e a checagem da configuração |
| `narrar.py` | liga e desliga a narração automática |
| `statusline.py` | a barra de estado: pasta, modelo e se a narração está ligada |
| `testes.py` | a suíte, sem rede e sem chave |
| `hooks/` | dois `SessionStart`: um prepara a pasta de dados, o outro injeta a instrução de narrar |
| `skills/` | as quatro skills que o Claude carrega |
| `roteiros/` | a aula sobre o próprio plugin, e as figuras de referência |
