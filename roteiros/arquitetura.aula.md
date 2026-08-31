# Por dentro do narrador
Os arquivos, as pastas e como uma peça chama a outra.

## O mapa do projeto
figura: figuras/arq-mapa.svg
- Tudo mora na raiz :: Os módulos em Python ficam todos soltos na raiz do projeto, um arquivo por responsabilidade, sem pasta de código-fonte e sem nenhuma biblioteca instalada.
- Três pastas ao lado :: Ao lado deles ficam três pastas: as skills, que são as instruções que eu leio; os hooks, que o Claude Code dispara sozinho; e os roteiros, com os textos e desenhos das aulas.
- Nada de dependência :: São dois mil seiscentas e quarenta e duas linhas ao todo, usando só a biblioteca padrão do Python. Não existe nada para instalar antes de usar.

## Duas casas: código e dados
figura: figuras/arq-duas-casas.svg
- O código é descartável :: Como plugin, o código roda de dentro do cache do Claude Code, numa pasta que leva o número da versão no nome e é reescrita a cada atualização.
- Os dados são seus :: Por isso nada que você precise manter mora junto do código. A chave, os áudios, o histórico e o cache vivem na sua pasta pessoal, dentro do diretório do Claude.
- Um só decide onde :: E um único módulo, o de configuração, decide todos esses caminhos. Nenhum outro arquivo escreve ao lado do próprio código.

## config: a fundação
figura: figuras/arq-config.svg
- Aponta as pastas :: O módulo de configuração é a base de que todos os outros dependem. Ele calcula onde ficam a pasta de dados, a saída de áudio, o cache e o arquivo que liga a narração automática.
- Lê o ambiente :: Ele também carrega o arquivo de ambiente, do mais específico para o mais geral, ignorando valor em branco, para que a chave vazia recém-instalada não apague a chave de verdade.
- Se explica sozinho :: Rodando esse módulo direto no terminal, ele imprime de onde veio a configuração, qual voz, qual modelo e se a chave existe, sem nunca mostrar a chave e sem gastar um crédito.

## speak: o coração da narração
figura: figuras/arq-speak.svg
- O maior dos módulos :: Com quatrocentas e cinquenta linhas, é o arquivo central: faz a extração do texto, a quebra em pedaços, a chamada à síntese e ainda expõe a linha de comando que todas as skills usam.
- Uma etapa puxa a outra :: Ele tira a marcação do markdown ou do agá tê ême ele, corta o texto em fronteira de frase, insere as pausas depois do corte e manda cada pedaço para a nuvem com o vizinho anterior e o seguinte por contexto.
- Ele orquestra os outros :: No fim, chama o costurador para emendar, o tocador para reproduzir e o histórico para anotar. Os três só existem porque ele os chama.

## O cache e a costura do áudio
figura: figuras/arq-cache.svg
- Cache pelo conteúdo :: Antes de pedir qualquer áudio, o programa calcula uma assinatura do trecho, que inclui o texto, a voz, o modelo, a velocidade e até os trechos vizinhos. Se já existe áudio com aquela assinatura, ele reaproveita e não cobra nada.
- O módulo do formato :: Cada resposta da nuvem volta como um arquivo de áudio completo, com etiqueta e com um cabeçalho que declara a duração só daquele pedaço.
- Sem limpar, não avança :: Emendados crus, o tocador acredita que o arquivo inteiro dura o tempo do primeiro pedaço e recusa pular adiante. Por isso um módulo pequeno, de sessenta linhas, tira esses cabeçalhos e conta a duração real quadro a quadro.

## O som e o registro
figura: figuras/arq-som.svg
- O tocador é bobo de propósito :: O reprodutor abre o arquivo, espera acabar e fecha. Ele não tem pausa nem barra, porque a narração roda como tarefa em segundo plano e encerrar essa tarefa já derruba o som.
- Ou entrega ao sistema :: Quando você quer controle de verdade, ele apenas entrega o arquivo ao programa de áudio do computador, e a pausa, o volume e a barra passam a ser de lá.
- O histórico se poda :: Cada narração vira uma linha de registro com data, origem, duração e voz. O arquivo não cresce sem limite: passando de cinquenta narrações, as mais antigas saem da lista e o áudio delas é apagado do disco.

## A vídeo-aula
figura: figuras/arq-aula.svg
- Um roteiro vira slides :: O gerador de aula lê um roteiro em markdown, onde cada título de segundo nível é um slide e cada item é um tópico, com o rótulo curto de um lado e a frase narrada do outro.
- Tempo de cada caractere :: Ele usa um endereço diferente da nuvem, que devolve o instante em que cada letra é falada. É daí que sai o momento exato de acender cada tópico e cada parte do desenho.
- Um arquivo só, autossuficiente :: O resultado é despejado num modelo de página com oitocentas linhas, que traz o áudio embutido dentro do próprio arquivo e o controle de ritmo no navegador de quem assiste.

## Skills e hooks: como eu descubro tudo isso
figura: figuras/arq-skills.svg
- Quatro skills me instruem :: A pasta de skills tem quatro instruções: ler em voz alta, repetir uma narração antiga, gerar a vídeo-aula e ligar a narração automática. São elas que eu carrego quando você pede alguma dessas coisas.
- Dois ganchos na abertura :: Os dois ganchos rodam quando a sessão começa. Um prepara sua pasta de dados e sincroniza a barra de estado; o outro injeta a instrução de narrar, mas só quando o interruptor está ligado.
- Gancho nenhum sintetiza :: Nenhum dos dois gera áudio. Eles injetam texto, e quem escreve o roteiro falado sou eu. Se a resposta crua fosse direto para a fala, você ouviria caminho de arquivo e nome de variável.

## O interruptor e a barra
figura: figuras/arq-interruptor.svg
- Um arquivo vazio decide :: A narração automática é ligada por um arquivo vazio na pasta de dados. Ele existindo, o gancho fala; não existindo, o gancho sai calado.
- Vale já na conversa :: Como o gancho só age na abertura da sessão, ligar e desligar também imprime o texto que passa a valer, e a skill me manda seguir o que saiu. Assim a mudança vale na conversa em andamento.
- A barra roda de fora :: A barra de estado é o único arquivo que repete a regra dos caminhos, porque ela roda de uma cópia fora do plugin: o endereço do cache muda a cada versão e quebraria sua configuração.

## Testes e o resto
figura: figuras/arq-testes.svg
- Cinquenta e seis testes :: O arquivo de testes é o segundo maior do projeto, com mais de quinhentas linhas. Roda em poucos segundos, sem rede e sem chave, trocando a síntese por uma função de mentira.
- Os arquivos de apoio :: Existem ainda os pequenos: o exemplo de configuração, os dois arquivos que declaram o plugin e o mercado onde ele aparece, o leia-me, a licença e as instruções para quem mexe no código.
- E o que dá para ignorar :: Restam os que nem valem uma olhada: os arquivos de comportamento do repositório e a pasta de código compilado, que o Python cria sozinho e que fica de fora do controle de versão.
