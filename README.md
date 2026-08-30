# narrador

Plugin do Claude Code que lê seus arquivos em voz alta e transforma um assunto em
vídeo-aula: slides e diagramas que acendem no instante exato da fala. A voz vem da
ElevenLabs; o código é Python puro, só stdlib, sem `pip install`.

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

Para conferir, rode `python config.py` na raiz do plugin: ele imprime voz,
modelo, idioma e se a chave existe, sem chamar a API. É o mesmo comando que
as skills rodam antes de escrever qualquer roteiro.

Requisitos: Python 3.10+. No Windows a reprodução usa
`System.Windows.Media.MediaPlayer` via PowerShell; em macOS e Linux tenta
`afplay`, `mpv` e `ffplay`, nessa ordem.

Nada do que você mantém fica dentro do plugin, que é reescrito a cada
atualização: chave, áudio gerado e cache moram em `~/.claude/narrador/`
(`NARRADOR_HOME` muda o lugar).

## O que ele faz

**`/narrador:ler-em-voz-alta`** narra um arquivo `.md`, `.txt` ou `.html`, um
trecho colado, ou um resumo escrito na hora. Documento técnico não vai direto
para o áudio: o Claude escreve antes um roteiro em prosa, porque tabela, comando
e endereço de site viram ruído quando falados.

**`/narrador:video-aula`** gera uma página com slides narrados. Cada tópico e
cada parte do diagrama acende no instante em que é dito, usando os tempos por
caractere que a ElevenLabs devolve no endpoint `with-timestamps`. A página sai
com o áudio embutido, pronta para publicar.

**Narração automática** (opcional, desligada): o hook `Stop` narra a resposta
assim que o Claude termina de responder.

```
narrar.cmd on     liga
narrar.cmd off    desliga
narrar.cmd        mostra o estado
```

O gatilho é o arquivo `~/.claude/narrador/narrar-respostas`: sem ele o hook sai
na hora, sem chamar a API. Roda com `async`, trunca em 1200 caracteres
(`NARRAR_MAX_CHARS` muda), ignora respostas com menos de 15 caracteres, e cada
resposta narrada consome créditos.

## Uso direto, sem o Claude

```powershell
python speak.py notas.md              # extrai, sintetiza e toca
python speak.py --text "bom dia"
type notas.txt | python speak.py -
python speak.py notas.md --keep       # mantém o mp3 em ~/.claude/narrador/out
python speak.py notas.md --dry-run    # mostra o texto extraído e a config
python speak.py --list-voices

python aula.py roteiros\narrador.aula.md --dry-run
python aula.py roteiros\narrador.aula.md
```

Flags de `speak.py`: `--as md|html|txt`, `--voice`, `--model`, `--format`,
`--speed`, `--language`, `--pause`, `--out`, `--keep`, `--no-play`, `--dry-run`,
`--list-voices`.

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
4. **Reprodução**: toca e apaga o temporário, salvo com `--keep` ou `--out`. Erro
   da API não deixa arquivo vazio: o destino só é escrito no fim.

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

`mp3.py` cuida da emenda: cada resposta da API é um MP3 completo, com ID3 e frame
Xing, e o player usaria o Xing do primeiro trecho como duração do arquivo
inteiro, recusando qualquer seek além dele. Os trechos são limpos antes de
emendar e a duração é contada frame a frame.

O áudio fica em cache por conteúdo em `~/.claude/narrador/cache-audio/`, então
ajustar figura ou layout e regerar não consome créditos.

## Estrutura

| Caminho | Papel |
| --- | --- |
| `speak.py` | leitura em voz alta |
| `aula.py`, `aula_template.html` | vídeo-aula com slides sincronizados |
| `mp3.py` | limpeza e medição dos trechos de áudio |
| `config.py` | onde ficam chave, saída e cache, e a checagem da configuração |
| `hooks/` | hook `Stop` da narração automática e `SessionStart` que semeia o `.env` |
| `skills/` | as duas skills que o Claude carrega |
| `roteiros/` | a aula sobre o próprio plugin, e as figuras de referência |
