# narrador: código do plugin

Este arquivo é para quem mexe no plugin. As instruções de uso ficam nas skills
`skills/ler-em-voz-alta` e `skills/video-aula`, que o Claude carrega quando o
usuário pede uma narração ou uma aula.

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
| `hooks/speak_reply.py` | hook `Stop`, ligado pelo arquivo sentinela |
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
