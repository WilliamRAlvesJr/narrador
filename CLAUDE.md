# narrador: código do plugin

Este arquivo é para quem mexe no plugin. As instruções de uso ficam nas skills
`skills/ler-em-voz-alta`, `skills/video-aula` e `skills/narrar-respostas`, que o
Claude carrega quando o usuário pede uma narração, uma aula, ou liga e desliga a
narração automática.

## Nada de estado dentro do plugin

O plugin roda de dentro do cache do Claude Code, reescrito a cada atualização.
`config.py` é o único lugar que decide caminhos: chave, saída e cache vivem em
`~/.claude/narrador/` (ou `NARRADOR_HOME`). Nenhum módulo deve escrever ao lado
do próprio código, nem ler um `.env` fixo da raiz, salvo o fallback de
desenvolvimento que `config.arquivos_de_env` já cobre.

Nas skills, nunca escreva caminho absoluto de máquina: use `${CLAUDE_PLUGIN_ROOT}`
ou a raiz derivada do "Base directory for this skill".

## Os módulos

| Arquivo | Papel |
| --- | --- |
| `speak.py` | extração, chunking, síntese e reprodução |
| `aula.py` | roteiro em página de aula, com tempos por caractere |
| `aula_template.html` | layout e player da aula |
| `mp3.py` | limpeza de ID3/Xing e duração por contagem de frames |
| `config.py` | pasta de dados, `.env`, saída e cache; `python config.py` checa a configuração |
| `narrar.py` | interruptor da narração automática: sentinela, e o texto da instrução que o hook e a skill injetam |
| `statusline.py` | barra de estado do Claude Code; autocontido, roda da cópia em `~/.claude/narrador/` |
| `hooks/narrar_respostas.py` | hook `SessionStart`: manda narrar um roteiro de cada resposta, ligado pelo arquivo sentinela |
| `hooks/semear_env.py` | hook `SessionStart`: copia o `.env.example` para a pasta de dados na primeira vez |

## Armadilhas que já custaram caro

- **`load_dotenv` antes do parser.** Os defaults das flags saem das variáveis de
  ambiente; carregar o `.env` depois de `parse_args` faz o script ignorar a
  configuração inteira e narrar com a voz errada.
- **`language_code` não existe no `eleven_multilingual_v2`.** Por isso o padrão é
  `eleven_turbo_v2_5`; ao trocar de modelo, o campo é omitido sozinho.
- **ID3 e frame Xing na emenda.** Cada resposta da API é um MP3 completo; sem
  `mp3.limpar` o player adota o Xing do primeiro trecho como duração do arquivo e
  recusa seek adiante. `aula.py` avisa quando a emenda medida diverge da soma.
- **Ligar a narração sem valer na sessão.** A instrução entra pelo
  `SessionStart`: criar a sentinela no meio da sessão não muda nada, e apagá-la
  não revoga o que já está no contexto. Quem liga ou desliga precisa imprimir
  também o texto que vale agora, que é o que `narrar.py --instrucao` e a saída
  do `off` fazem.
- **Narrar a resposta crua.** A narração automática já foi um hook `Stop` que
  mandava a resposta pronta para a API: sem modelo no caminho, caminho de arquivo
  e nome de variável iam para o áudio como estão. Hoje o hook só injeta a
  instrução; quem escreve o roteiro é o Claude. Nenhum hook deste plugin deve
  voltar a sintetizar texto que ninguém reescreveu para o ouvido.
- **Caminho do plugin no settings do usuário.** A pasta do cache leva a versão
  no nome, então qualquer caminho anotado fora do plugin morre na atualização
  seguinte. Por isso a barra de estado aponta para a cópia em
  `~/.claude/narrador/`, que o hook reescreve quando o plugin muda, e o
  `statusline.py` é autocontido: rodando de lá, ele não tem o `config.py` ao lado.
- **Break tags desalinham a aula.** Ritmo na vídeo-aula é controle do player
  (velocidade, pausa, volume), nunca da gravação.
- **Chave vazia no `.env`.** O arquivo semeado vem com `ELEVENLABS_API_KEY=`
  em branco; por isso `carregar_env` ignora valor vazio, senão ele venceria o
  `.env` da raiz do plugin no fallback de desenvolvimento e a chave sumiria.
- **Cache por conteúdo.** A chave inclui texto, voz, modelo, formato, velocidade
  e idioma. Ao mudar como a síntese é pedida, invalide o cache junto.

## Ao mexer no player

O acompanhamento roda quadro a quadro enquanto toca; depender de `timeupdate`
faz o início sair corrido. Qualquer avanço de tópico dispara o respiro, nunca o
incremento exato de um. A velocidade é reaplicada no `loadedmetadata` e no
`play`, com `defaultPlaybackRate` junto.
