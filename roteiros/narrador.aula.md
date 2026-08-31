# Como funciona o narrador
Uma aula narrada sobre o projeto que lê seus arquivos em voz alta.

## O que é
figura: figuras/o-que-e.svg
- Lê arquivos em voz alta :: Este projeto lê em voz alta arquivos de texto, markdown ou HTML, usando a síntese de voz da ElevenLabs.
- Um script, sem dependências :: É um único script em Python, que usa apenas a biblioteca padrão. Não existe nada para instalar.
- Chamado pelo Claude :: Na prática, você pede para eu ler alguma coisa, e eu chamo o script por baixo.

## A configuração
figura: figuras/configuracao.svg
- A chave da API :: Toda a configuração fica num arquivo de ambiente, começando pela chave da sua conta na ElevenLabs.
- Voz, idioma e velocidade :: Ali também ficam a voz escolhida, o idioma, a velocidade da fala e a pausa entre as frases.
- Nada disso vai no comando :: O script lê essas preferências sozinho, então nenhum desses valores precisa ser digitado a cada vez.

## Etapa um: extração
figura: figuras/extracao.svg
- Markdown perde a marcação :: Do markdown, o script remove blocos de código, links, imagens e símbolos de ênfase, deixando só a prosa.
- HTML perde as tags :: Do HTML, ele remove scripts, estilos e todas as tags, e traduz os caracteres especiais.
- Sobra o que se fala :: No fim dessa etapa sobra apenas o texto que faz sentido ouvir.

## Etapa dois: quebra em pedaços
figura: figuras/chunking.svg
- Um pedido tem limite :: A API não aceita um documento inteiro de uma vez, então o texto é dividido.
- Sempre em fim de frase :: A divisão acontece em fronteira de parágrafo ou de frase, nunca no meio de uma palavra.
- Contexto na emenda :: Cada pedido leva junto o final do trecho anterior e o começo do próximo, para que a emenda entre eles não soe cortada.

## Etapa três: a fala
figura: figuras/a-fala.svg
- A pausa é uma etiqueta :: Depois de cada ponto final o script insere uma etiqueta de silêncio, que a ElevenLabs interpreta como uma pausa de verdade.
- Idioma travado :: O idioma vai explícito no pedido, porque um documento com termos em inglês faz o modelo escolher o idioma errado sozinho.
- Um áudio só :: Os pedaços voltam como áudio e são emendados num arquivo único.

## Etapa quatro: o som
figura: figuras/o-som.svg
- Toca e fica guardado :: No Windows a reprodução usa o player nativo do sistema, e o arquivo fica na pasta de dados, anotado no histórico.
- Ouvir de novo é de graça :: Como o áudio foi guardado, repetir uma narração antiga é só abri-la no seu player, sem gastar créditos.
- Erro não deixa lixo :: Se a API falhar no meio, nada é escrito em disco, para você não encontrar um arquivo vazio depois.

## Histórico e replay
figura: figuras/historico.svg
- Cada narração fica anotada :: Toda vez que eu narro, o áudio vai para a pasta de dados com uma linha de registro: quando foi, de onde veio, quanto durou e com que voz.
- Você escolhe numa lista :: Ao pedir para ouvir de novo, eu mostro as últimas quatro e você escolhe qual quer.
- Abre no seu programa de áudio :: A escolhida abre no player do computador, com a barra, a pausa e o volume que ele já tem, sem gastar crédito nenhum.

## O roteiro antes do áudio
figura: figuras/roteiro.svg
- Documento técnico cansa o ouvido :: Um leia-me foi escrito para os olhos. Tabela, comando e endereço de site viram ruído quando são falados.
- Eu reescrevo antes :: Então, antes de narrar documentação, eu escrevo um roteiro em prosa e narro o roteiro, não o arquivo original.
- Você ouve a ideia :: O resultado é mais curto, mais barato em créditos, e muito mais fácil de acompanhar.

## Narração automática
figura: figuras/narracao-automatica.svg
- Também vale para o que eu respondo :: Ligado o modo automático, no fim de cada resposta eu escrevo um roteiro dela e narro o roteiro, nunca o texto da tela. A narração corre em segundo plano, e você a encerra quando quiser silêncio.
- Desligado por padrão :: Ele só age enquanto um arquivo específico existir na pasta de dados. Um comando liga, outro desliga, e vale já na conversa em andamento.
- Custa créditos :: Fica desligado porque cada resposta narrada consome créditos da sua conta.

## O que segura tudo isso
figura: figuras/testes.svg
- Cinquenta e seis testes :: O projeto tem uma bateria de testes que roda em poucos segundos, sem rede e sem chave nenhuma.
- Áudio de mentira :: A síntese é trocada por uma função falsa, e o arquivo de som usado nos testes é montado ali mesmo, pedaço por pedaço.
- Nada de surpresa cara :: Assim dá para mexer na quebra do texto ou na emenda do áudio e descobrir o erro na hora, e não no meio de uma narração já paga.

## Esta aula
figura: figuras/esta-aula.svg
- Slides e áudio no mesmo lugar :: Esta página foi gerada pelo próprio projeto, a partir de um roteiro parecido com os outros.
- Tempo exato de cada frase :: A ElevenLabs devolve o instante de cada caractere falado, então cada tópico acende exatamente quando é dito.
- Tudo dentro da página :: O áudio viaja embutido no arquivo, então basta abrir o endereço para assistir.
