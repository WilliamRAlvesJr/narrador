# narrador: código do plugin

Este arquivo é para quem mexe no plugin. As instruções de uso ficam nas skills
`skills/ler-em-voz-alta`, `skills/replay`, `skills/video-aula` e
`skills/narrar-respostas`, que o Claude carrega quando o usuário pede uma
narração, quer ouvir de novo algo já narrado, pede uma aula, ou liga e desliga a
narração automática.

## Nada de estado dentro do plugin

O plugin roda de dentro do cache do Claude Code, reescrito a cada atualização.
`config.py` é o único lugar que decide caminhos: chave, áudio gerado, histórico e
cache vivem em `~/.claude/narrador/` (ou `NARRADOR_HOME`). Nenhum módulo escreve
ao lado do próprio código, nem lê um `.env` fixo da raiz, salvo o fallback de
desenvolvimento que `config.arquivos_de_env` cobre.

Nas skills, nunca escreva caminho absoluto de máquina: use `${CLAUDE_PLUGIN_ROOT}`
ou a raiz derivada do "Base directory for this skill".

## Os módulos

| Arquivo | Papel |
| --- | --- |
| `speak.py` | extração, chunking, síntese com cache, emenda e a CLI |
| `tocador.py` | reprodução: o player embutido que espera o fim, e a entrega ao programa de áudio do sistema |
| `historico.py` | uma linha JSON por narração, com poda do áudio velho |
| `mp3.py` | limpeza de ID3/Xing e duração por contagem de frames |
| `aula.py` | roteiro em página de aula, com tempos por caractere |
| `aula_template.html` | layout e player da aula |
| `config.py` | pasta de dados, `.env` e cache; `python3 config.py` checa a configuração |
| `narrar.py` | interruptor da narração automática: sentinela, e o texto da instrução que o hook e o `on` injetam |
| `statusline.py` | barra de estado do Claude Code; autocontido, roda da cópia em `~/.claude/narrador/` |
| `testes.py` | `python3 testes.py`: stdlib, sem rede, com a síntese trocada por uma função de mentira |
| `hooks/semear_env.py` | hook `SessionStart`: semeia o `.env` e atualiza a cópia do `statusline.py` |
| `hooks/narrar_respostas.py` | hook `SessionStart`: manda narrar um roteiro de cada resposta, ligado pelo arquivo sentinela |

Rode `python3 testes.py` antes de commitar: 71 testes, alguns segundos, nenhuma
chamada à API.

## Quem manda no áudio

- **A narração roda em segundo plano** (`run_in_background`), e o player é
  processo filho dessa tarefa: encerrar a tarefa no Claude Code encerra o som.
  É assim que o usuário pede silêncio.
- **Sem player instalado, o som ainda sai.** `tocar_no_unix` cai no programa
  padrão de MP3 da máquina, e avisa que a partir daí encerrar a tarefa não cala
  mais o som. Silêncio calado é o pior desfecho: cada saída sem áudio (sem
  `xdg-open`, sem programa associado, sessão sem tela) sai com o aviso que diz o
  que fazer, e `abrir_no_sistema` devolve `False` para quem chamou.
- **A reprodução com controles é a do sistema.** `--abrir` entrega o arquivo do
  histórico ao programa de áudio do computador e retorna na hora; pausa, barra e
  volume são de lá.
- **Controle de reprodução não mora neste plugin.** Nada de player com teclado:
  nenhum caminho daqui tem console com entrada própria, nem a sessão do Claude
  nem o `!` do prompt, e `[Console]::KeyAvailable` estoura com a entrada
  redirecionada. Nada de comando que interrompa de fora, e nada de hook lendo o
  prompt: prompt é conversa, não interface.

## Invariantes

- **Nada de `python` puro num comando do plugin.** Em Linux e macOS esse nome
  costuma não existir, e em Windows costuma ser o único: os dois hooks do
  `hooks.json` rodam em shell form e escolhem entre `python3` e `python` antes de
  chamar o script, as skills e o README pedem `python3` com a ressalva do outro
  nome, e o texto que `narrar.py` injeta cita o `sys.executable` que está
  rodando. Shell form também significa: nada de `args`, e todo caminho entre
  aspas.
- **`load_dotenv` antes do parser.** Os defaults das flags saem das variáveis de
  ambiente; carregar o `.env` depois de `parse_args` faz o script ignorar a
  configuração inteira e narrar com a voz errada.
- **`language_code` não existe no `eleven_multilingual_v2`.** Por isso o padrão é
  `eleven_turbo_v2_5`; ao trocar de modelo, o campo é omitido sozinho.
- **ID3 e frame Xing na emenda.** Cada resposta da API é um MP3 completo, com tag
  e com um frame que declara a duração daquele trecho. Emendados crus, o player
  adota o primeiro como duração do arquivo e recusa seek adiante: `speak.emendar`
  e `aula.py` passam cada trecho por `mp3.limpar`, e `aula.py` avisa quando a
  emenda medida diverge da soma. Trecho único fica intocado, porque o cabeçalho
  dele já descreve o arquivo certo. Qualquer outra emenda de áudio passa por ali.
- **Ligar a narração vale na sessão em curso.** A instrução entra pelo
  `SessionStart`, então a sentinela sozinha não muda a conversa em andamento:
  `on` e `off` imprimem a instrução e a revogação junto da confirmação, e a skill
  manda o Claude seguir o que saiu. `on` é um comando só, com a checagem da chave
  dentro: cada comando a mais é espera para o que é um interruptor.
- **Só roteiro vai para a síntese.** O hook injeta a instrução; quem escreve o
  roteiro falado é o Claude. Nenhum hook deste plugin sintetiza texto que ninguém
  reescreveu para o ouvido, senão caminho de arquivo e nome de variável viram
  áudio.
- **O settings do usuário é dele.** A barra de estado é uma só, e um plugin de
  narração não apaga a que já está lá: `config.sugestao_da_statusline` monta o
  trecho com o interpretador em uso e o caminho da cópia, e quem cola é o
  usuário. Sai em dois lugares, os dois de uma vez só: o `narrar.py on`, e a
  primeira sessão depois da instalação, junto do pedido da chave, que é a
  única vez que o `semear_env` fala.
- **Caminho do plugin no settings do usuário.** A pasta do cache leva a versão no
  nome, então caminho anotado fora do plugin morre na atualização seguinte. A
  barra de estado aponta para a cópia em `~/.claude/narrador/`, que o hook
  reescreve quando o plugin muda, e por isso `statusline.py` é autocontido:
  rodando de lá, não tem o `config.py` ao lado.
- **Chave vazia no `.env`.** O arquivo semeado vem com `ELEVENLABS_API_KEY=` em
  branco; `carregar_env` ignora valor vazio, senão ele vence o `.env` da raiz do
  plugin no fallback de desenvolvimento e a chave some.
- **Cache por conteúdo.** A chave inclui texto, voz, modelo, formato, velocidade
  e idioma, e na leitura em voz alta também os trechos vizinhos, que mudam a
  prosódia. Ao mudar como a síntese é pedida, invalide o cache junto.
- **Velocidade validada antes da chamada.** A API aceita de 0.7 a 1.2 e responde
  422 depois de receber o texto inteiro. `speak.ler_velocidade` é o único caminho
  para ler `ELEVENLABS_SPEED`.
- **Histórico podado.** Guardar o áudio é o padrão, então `historico` mantém as
  últimas `NARRADOR_HISTORICO_MAX` (50) narrações e apaga o som das que saem.
  Quem gravar áudio por outro caminho registra e poda junto.
- **O player do Unix é MP3, e sai sozinho.** `PLAYERS_UNIX` só aceita programa
  que decodifica MP3, termina no fim do áudio e não abre janela: `paplay` e
  `aplay` ficam de fora por só entenderem WAV. `players_disponiveis` filtra
  pelo `shutil.which`, e a chamada vai sem stdin, senão mpv e gst-play comem a
  entrada do processo que pediu a narração.
- **Break tags desalinham a aula.** Ritmo na vídeo-aula é controle do player da
  página, nunca da gravação.

## Ao mexer no player da vídeo-aula

Isto é sobre o JavaScript do `aula_template.html`, não sobre o `tocador.py`.

O acompanhamento roda quadro a quadro enquanto toca; depender de `timeupdate`
faz o início sair corrido. Qualquer avanço de tópico dispara o respiro, nunca o
incremento exato de um. A velocidade é reaplicada no `loadedmetadata` e no
`play`, com `defaultPlaybackRate` junto.
