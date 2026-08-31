#!/usr/bin/env python3
"""Testes do narrador. Rode com: python testes.py

So stdlib, e nenhuma chamada de rede: tudo aqui e funcao pura ou arquivo em
pasta temporaria. A sintese e substituida por uma funcao de mentira, entao
rodar os testes nao gasta credito nem precisa da chave.

O MP3 usado nos testes e montado a mao, frame por frame, para nao depender de
audio gravado nem da maquina de quem roda.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import aula  # noqa: E402
import config  # noqa: E402
import historico  # noqa: E402
import mp3  # noqa: E402
import narrar  # noqa: E402
import speak  # noqa: E402

# --------------------------------------------------------------------------- #
# MP3 de mentira: MPEG-1 Layer III, 128 kbps, 44100 Hz, sem padding
# --------------------------------------------------------------------------- #
CABECALHO = bytes([0xFF, 0xFB, 0x90, 0x00])
TAMANHO_FRAME = 144 * 128000 // 44100  # 417 bytes
DURACAO_FRAME = 1152 / 44100           # ~26 ms


def frame(recheio: bytes = b"") -> bytes:
    corpo = recheio + b"\x00" * (TAMANHO_FRAME - len(CABECALHO) - len(recheio))
    return CABECALHO + corpo


def id3(tamanho_corpo: int = 21) -> bytes:
    """Tag ID3v2 com o tamanho em syncsafe (7 bits por byte)."""
    n = tamanho_corpo
    corpo = bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])
    return b"ID3\x04\x00\x00" + corpo + b"\x00" * tamanho_corpo


def mp3_completo(frames: int = 3) -> bytes:
    """Como a API responde: tag ID3, frame Xing de metadados, e o audio."""
    return id3() + frame(b"Xing") + frame() * frames


class TestMp3(unittest.TestCase):
    def test_limpar_tira_id3_e_xing(self):
        limpo = mp3.limpar(mp3_completo(frames=3))
        self.assertEqual(limpo, frame() * 3)

    def test_limpar_nao_tira_frame_de_audio(self):
        so_audio = frame() * 2
        self.assertEqual(mp3.limpar(so_audio), so_audio)

    def test_duracao_conta_frames(self):
        self.assertAlmostEqual(mp3.duracao(frame() * 10), 10 * DURACAO_FRAME, places=6)

    def test_duracao_de_vazio(self):
        self.assertEqual(mp3.duracao(b""), 0.0)


class TestEmenda(unittest.TestCase):
    def test_emenda_soma_as_duracoes(self):
        partes = [mp3_completo(frames=4), mp3_completo(frames=6)]
        emendado = speak.emendar(partes, "mp3_44100_128")
        self.assertAlmostEqual(mp3.duracao(emendado), 10 * DURACAO_FRAME, places=6)

    def test_emenda_nao_deixa_xing_no_arquivo(self):
        emendado = speak.emendar([mp3_completo(), mp3_completo()], "mp3_44100_128")
        self.assertNotIn(b"Xing", emendado)
        self.assertNotIn(b"ID3", emendado)

    def test_trecho_unico_fica_intacto(self):
        um = mp3_completo()
        self.assertEqual(speak.emendar([um], "mp3_44100_128"), um)

    def test_formato_que_nao_e_mp3_passa_cru(self):
        partes = [b"\x01\x02", b"\x03"]
        self.assertEqual(speak.emendar(partes, "pcm_44100"), b"\x01\x02\x03")


class TestExtracao(unittest.TestCase):
    def test_markdown_perde_marcacao(self):
        texto = speak.markdown_to_text(
            "# Titulo\n\nUm **negrito** e um [link](http://x.com).\n\n"
            "```python\nprint('nao le isso')\n```\n"
        )
        self.assertIn("Titulo", texto)
        self.assertIn("Um negrito e um link", texto)
        self.assertNotIn("nao le isso", texto)
        self.assertNotIn("http", texto)

    def test_markdown_perde_front_matter(self):
        texto = speak.markdown_to_text("---\ntitle: x\n---\nCorpo.\n")
        self.assertNotIn("title", texto)
        self.assertIn("Corpo", texto)

    def test_html_perde_script_e_decodifica_entidade(self):
        texto = speak.html_to_text("<p>Caf&eacute; &amp; leite</p><script>ruido()</script>")
        self.assertIn("Café & leite", texto)
        self.assertNotIn("ruido", texto)

    def test_extract_le_arquivo_pela_extensao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "nota.md"
            arquivo.write_text("# Oi\n\nTexto `codigo` aqui.", encoding="utf-8")
            texto = speak.extract(str(arquivo))
        self.assertEqual(texto, "Oi\n\nTexto codigo aqui.")

    def test_extract_aceita_texto_direto(self):
        self.assertEqual(speak.extract("apenas um texto"), "apenas um texto")

    def test_normalize_junta_espacos_e_linhas(self):
        self.assertEqual(speak.normalize("a  b\n\n\n\nc  "), "a b\n\nc")


class TestPausas(unittest.TestCase):
    def test_insere_break_entre_frases(self):
        self.assertIn('<break time="2.0s" />', speak.add_pauses("Um. Dois.", 2))

    def test_nao_quebra_decimal(self):
        self.assertNotIn("break", speak.add_pauses("O valor 3.14 basta.", 2))

    def test_nao_poe_break_no_fim(self):
        self.assertEqual(speak.add_pauses("Fim.", 2), "Fim.")

    def test_pausa_zero_nao_mexe_no_texto(self):
        self.assertEqual(speak.add_pauses("Um. Dois.", 0), "Um. Dois.")


class TestChunking(unittest.TestCase):
    def test_texto_curto_vira_um_chunk(self):
        self.assertEqual(speak.chunks("Curto.", 100), ["Curto."])

    def test_respeita_o_limite(self):
        texto = " ".join(f"Frase numero {i}." for i in range(200))
        for pedaco in speak.chunks(texto, 200):
            self.assertLessEqual(len(pedaco), 200)

    def test_corta_em_fronteira_de_frase(self):
        texto = "Primeira frase aqui. Segunda frase aqui. Terceira frase aqui."
        for pedaco in speak.chunks(texto, 40):
            self.assertTrue(pedaco.endswith((".", "!", "?")), pedaco)

    def test_frase_gigante_sem_pontuacao_e_fatiada(self):
        pedacos = speak.chunks("a" * 250, 100)
        self.assertEqual(len(pedacos), 3)
        self.assertEqual("".join(pedacos), "a" * 250)

    def test_nada_se_perde(self):
        texto = " ".join(f"Frase {i}." for i in range(60))
        juntado = " ".join(speak.chunks(texto, 120)).replace("\n\n", " ")
        self.assertEqual(sorted(juntado.split()), sorted(texto.split()))


class TestVelocidade(unittest.TestCase):
    def test_vazio_vira_padrao(self):
        self.assertEqual(speak.ler_velocidade(None), 1.0)
        self.assertEqual(speak.ler_velocidade(""), 1.0)

    def test_valor_valido(self):
        self.assertEqual(speak.ler_velocidade("0.9"), 0.9)
        self.assertEqual(speak.ler_velocidade(1.2), 1.2)

    def test_texto_nao_passa(self):
        with self.assertRaises(SystemExit):
            speak.ler_velocidade("rapido")

    def test_fora_da_faixa_nao_passa(self):
        for valor in ("0.5", "2.0"):
            with self.assertRaises(SystemExit):
                speak.ler_velocidade(valor)


class TestCache(unittest.TestCase):
    """A sintese e substituida: conta as chamadas em vez de falar com a API."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.cache_original = speak.CACHE_DIR
        self.synthesize_original = speak.synthesize
        self.chamadas = 0
        speak.CACHE_DIR = Path(self.pasta.name)

        def falso(*_args, **_kwargs):
            self.chamadas += 1
            return b"audio-" + str(self.chamadas).encode()

        speak.synthesize = falso

    def tearDown(self):
        speak.CACHE_DIR = self.cache_original
        speak.synthesize = self.synthesize_original
        self.pasta.cleanup()

    def sintetizar(self, texto="oi", **kwargs):
        return speak.sintetizar(texto, "voz", "modelo", "mp3_44100_128", 1.0,
                                "pt", None, None, **kwargs)

    def test_segunda_vez_vem_do_cache(self):
        primeiro, do_cache = self.sintetizar()
        self.assertFalse(do_cache)
        segundo, do_cache = self.sintetizar()
        self.assertTrue(do_cache)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(self.chamadas, 1)

    def test_texto_diferente_e_outra_entrada(self):
        self.sintetizar("um")
        self.sintetizar("outro")
        self.assertEqual(self.chamadas, 2)

    def test_no_cache_sempre_sintetiza(self):
        self.sintetizar(usar_cache=False)
        _, do_cache = self.sintetizar(usar_cache=False)
        self.assertFalse(do_cache)
        self.assertEqual(self.chamadas, 2)
        self.assertEqual(list(Path(self.pasta.name).iterdir()), [])

    def test_cache_sem_permissao_nao_derruba_a_narracao(self):
        speak.CACHE_DIR = Path(self.pasta.name) / "arquivo-no-lugar-da-pasta"
        speak.CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        speak.CACHE_DIR.write_bytes(b"")  # mkdir vai falhar aqui
        audio, do_cache = self.sintetizar()
        self.assertTrue(audio)
        self.assertFalse(do_cache)


class TestAssinatura(unittest.TestCase):
    CAMPOS = ["text", "voice", "model", "fmt", "speed", "language", "prev", "nxt"]
    BASE = ("texto", "voz", "modelo", "mp3_44100_128", 1.0, "pt", None, None)

    def chave(self, **troca):
        campos = dict(zip(self.CAMPOS, self.BASE))
        campos.update(troca)
        return speak.assinatura(**campos)

    def test_mesma_entrada_mesma_chave(self):
        self.assertEqual(self.chave(), self.chave())

    def test_cada_campo_muda_a_chave(self):
        for campo, valor in [("text", "outro"), ("voice", "outra"), ("model", "m2"),
                             ("fmt", "mp3_44100_64"), ("speed", 0.9),
                             ("language", "en"), ("prev", "antes"), ("nxt", "depois")]:
            with self.subTest(campo=campo):
                self.assertNotEqual(self.chave(), self.chave(**{campo: valor}))


class TestRoteiroDaAula(unittest.TestCase):
    ROTEIRO = """# Titulo da aula
Subtitulo em uma linha.

## Primeiro slide
- Rotulo :: Frase narrada inteira.
- So o rotulo

## Slide sem topico

## Segundo slide
- Outro rotulo :: Outra frase.
"""

    def test_parse(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "aula.md"
            arquivo.write_text(self.ROTEIRO, encoding="utf-8")
            titulo, subtitulo, slides = aula.parse_roteiro(arquivo)

        self.assertEqual(titulo, "Titulo da aula")
        self.assertEqual(subtitulo, "Subtitulo em uma linha.")
        self.assertEqual([s["titulo"] for s in slides],
                         ["Primeiro slide", "Segundo slide"])  # slide vazio sai
        topicos = slides[0]["topicos"]
        self.assertEqual(topicos[0]["narracao"], "Frase narrada inteira.")
        self.assertEqual(topicos[1]["narracao"], "So o rotulo")  # sem ::, narra o rotulo

    def test_roteiro_vazio_para_o_programa(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "vazio.md"
            arquivo.write_text("# So o titulo\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                aula.parse_roteiro(arquivo)

    def test_pontuar(self):
        self.assertEqual(aula.pontuar("Sem ponto"), "Sem ponto.")
        for pronto in ("Com ponto.", "Pergunta?", "Grito!", "Dois pontos:"):
            self.assertEqual(aula.pontuar(pronto), pronto)


class TestEnv(unittest.TestCase):
    def test_valor_vazio_nao_define_nada(self):
        """O .env semeado vem com a chave em branco; ela nao pode vencer a real."""
        with tempfile.TemporaryDirectory() as pasta:
            semeado = Path(pasta) / "semeado.env"
            semeado.write_text("NARRADOR_TESTE_CHAVE=\n", encoding="utf-8")
            real = Path(pasta) / "real.env"
            real.write_text("NARRADOR_TESTE_CHAVE=valor\n", encoding="utf-8")

            original = config.arquivos_de_env
            os.environ.pop("NARRADOR_TESTE_CHAVE", None)
            try:
                config.arquivos_de_env = lambda: [semeado, real]
                config.carregar_env()
                self.assertEqual(os.environ.get("NARRADOR_TESTE_CHAVE"), "valor")
            finally:
                config.arquivos_de_env = original
                os.environ.pop("NARRADOR_TESTE_CHAVE", None)

    def test_comentario_e_aspas(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / ".env"
            arquivo.write_text('# comentario\nNARRADOR_TESTE_VOZ="abc"\n', encoding="utf-8")
            original = config.arquivos_de_env
            os.environ.pop("NARRADOR_TESTE_VOZ", None)
            try:
                config.arquivos_de_env = lambda: [arquivo]
                config.carregar_env()
                self.assertEqual(os.environ.get("NARRADOR_TESTE_VOZ"), "abc")
            finally:
                config.arquivos_de_env = original
                os.environ.pop("NARRADOR_TESTE_VOZ", None)


class TestInterruptor(unittest.TestCase):
    """narrar.py de ponta a ponta, com a pasta de dados em lugar temporario."""

    def rodar(self, *argumentos, pasta, chave="sk-de-mentira", casa=None):
        ambiente = dict(os.environ, NARRADOR_HOME=pasta, ELEVENLABS_API_KEY=chave)
        if casa:
            # os dois nomes: Path.home() le USERPROFILE no Windows e HOME no resto
            ambiente.update(HOME=casa, USERPROFILE=casa)
        return subprocess.run(
            [sys.executable, str(RAIZ / "narrar.py"), *argumentos],
            capture_output=True, text=True, encoding="utf-8", env=ambiente,
        )

    def test_ciclo_completo(self):
        with tempfile.TemporaryDirectory() as pasta:
            sentinela = Path(pasta) / "narrar-respostas"

            saida = self.rodar(pasta=pasta)
            self.assertIn("DESLIGADA", saida.stdout)
            self.assertFalse(sentinela.exists())

            self.rodar("on", pasta=pasta)
            self.assertTrue(sentinela.exists())
            self.assertIn("LIGADA", self.rodar(pasta=pasta).stdout)

            saida = self.rodar("off", pasta=pasta)
            self.assertFalse(sentinela.exists())
            self.assertIn("DESLIGADA", saida.stdout)

    def test_ligar_sem_chave_nao_liga(self):
        """Narracao ligada sem chave falharia em toda resposta: melhor nao ligar."""
        with tempfile.TemporaryDirectory() as pasta:
            saida = self.rodar("on", pasta=pasta, chave=" ")
            self.assertEqual(saida.returncode, 1)
            self.assertFalse((Path(pasta) / "narrar-respostas").exists())
            self.assertIn("falta a chave", saida.stdout)

    def test_off_repetido_nao_e_erro(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertEqual(self.rodar("off", pasta=pasta).returncode, 0)

    def test_argumento_desconhecido(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = self.rodar("talvez", pasta=pasta)
            self.assertEqual(saida.returncode, 2)
            self.assertIn("desconhecido", saida.stderr)

    def barra(self, casa: str, comando: str) -> None:
        settings = Path(casa) / ".claude"
        settings.mkdir(parents=True, exist_ok=True)
        (settings / "settings.json").write_text(
            json.dumps({"statusLine": {"type": "command", "command": comando}}),
            encoding="utf-8",
        )

    def test_ligar_sugere_a_barra_de_estado(self):
        """Sugestao, nunca escrita: o settings do usuario e dele."""
        with tempfile.TemporaryDirectory() as pasta, \
                tempfile.TemporaryDirectory() as casa:
            saida = self.rodar("on", pasta=pasta, casa=casa)
            self.assertIn("statusLine", saida.stdout)
            self.assertIn("statusline.py", saida.stdout)
            self.assertFalse((Path(casa) / ".claude" / "settings.json").exists())

    def test_barra_ja_configurada_nao_vira_ruido(self):
        with tempfile.TemporaryDirectory() as pasta, \
                tempfile.TemporaryDirectory() as casa:
            self.barra(casa, 'python "/qualquer/lugar/statusline.py"')
            self.assertNotIn("statusLine", self.rodar("on", pasta=pasta, casa=casa).stdout)

    def test_outra_barra_ainda_recebe_a_sugestao(self):
        with tempfile.TemporaryDirectory() as pasta, \
                tempfile.TemporaryDirectory() as casa:
            self.barra(casa, "meu-script-de-barra")
            self.assertIn("statusLine", self.rodar("on", pasta=pasta, casa=casa).stdout)

    def test_ligar_imprime_a_instrucao_com_o_caminho_do_speak(self):
        """Ligar num comando so: a confirmacao e as regras saem juntas."""
        with tempfile.TemporaryDirectory() as pasta:
            saida = self.rodar("on", pasta=pasta)
            self.assertIn("LIGADA", saida.stdout)
            self.assertIn("speak.py", saida.stdout)


class TestBarraDeEstado(unittest.TestCase):
    ENTRADA = ('{"workspace":{"current_dir":"C:/x/projeto"},'
               '"model":{"display_name":"Opus 5"}}')

    def rodar(self, entrada: str, pasta: str) -> str:
        ambiente = dict(os.environ, NARRADOR_HOME=pasta)
        saida = subprocess.run(
            [sys.executable, str(RAIZ / "statusline.py")],
            input=entrada, capture_output=True, text=True,
            encoding="utf-8", env=ambiente,
        )
        return saida.stdout.strip()

    def test_mostra_o_estado_da_narracao(self):
        with tempfile.TemporaryDirectory() as pasta:
            linha = self.rodar(self.ENTRADA, pasta)
            self.assertIn("projeto", linha)
            self.assertIn("Opus 5", linha)
            self.assertIn("sem narrar", linha)

            (Path(pasta) / "narrar-respostas").touch()
            self.assertIn("narrando", self.rodar(self.ENTRADA, pasta))

    def test_json_quebrado_nao_quebra_a_barra(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertTrue(self.rodar("isso nao e json", pasta))


class TestHistorico(unittest.TestCase):
    """Cada teste tem seu proprio historico, numa pasta temporaria."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.pasta.name)
        self.arquivo_original = historico.ARQUIVO
        self.dados_original = config.DADOS
        self.maximo_original = os.environ.get("NARRADOR_HISTORICO_MAX")
        historico.ARQUIVO = self.raiz / "historico.jsonl"
        config.DADOS = self.raiz

    def tearDown(self):
        historico.ARQUIVO = self.arquivo_original
        config.DADOS = self.dados_original
        if self.maximo_original is None:
            os.environ.pop("NARRADOR_HISTORICO_MAX", None)
        else:
            os.environ["NARRADOR_HISTORICO_MAX"] = self.maximo_original
        self.pasta.cleanup()

    def narracao(self, nome: str) -> Path:
        arquivo = self.raiz / f"{nome}.mp3"
        arquivo.write_bytes(mp3_completo())
        historico.registrar(arquivo, nome, 100, 12.3, "voz", "modelo", 1.0)
        return arquivo

    def test_registra_e_le_do_mais_novo_para_o_mais_velho(self):
        self.narracao("primeira")
        self.narracao("segunda")
        recentes = historico.recentes()
        self.assertEqual([i["origem"] for i in recentes], ["segunda", "primeira"])

    def test_item_conta_do_fim(self):
        self.narracao("primeira")
        self.narracao("segunda")
        self.assertEqual(historico.item(1)["origem"], "segunda")
        self.assertEqual(historico.item(2)["origem"], "primeira")
        self.assertIsNone(historico.item(3))
        self.assertIsNone(historico.item(0))

    def test_poda_apaga_o_audio_que_saiu(self):
        os.environ["NARRADOR_HISTORICO_MAX"] = "2"
        velha = self.narracao("velha")
        self.narracao("meio")
        self.narracao("nova")
        self.assertFalse(velha.exists())
        self.assertEqual(len(historico.ler()), 2)

    def test_linha_corrompida_e_ignorada(self):
        self.narracao("boa")
        with historico.ARQUIVO.open("a", encoding="utf-8") as f:
            f.write("isso nao e json\n")
        self.assertEqual(len(historico.ler()), 1)

    def test_historico_vazio(self):
        self.assertEqual(historico.recentes(), [])
        self.assertIn("Nenhuma narracao", historico.formatar([]))

    def test_formatar_avisa_audio_sumido(self):
        arquivo = self.narracao("sumida")
        arquivo.unlink()
        self.assertIn("audio apagado", historico.formatar(historico.recentes()))


class TestAbrir(unittest.TestCase):
    """O --abrir so entrega o arquivo ao sistema; aqui testamos as recusas."""

    def rodar(self, pasta: str, *argumentos) -> subprocess.CompletedProcess:
        ambiente = dict(os.environ, NARRADOR_HOME=pasta)
        return subprocess.run(
            [sys.executable, str(RAIZ / "speak.py"), *argumentos],
            capture_output=True, text=True, encoding="utf-8", env=ambiente,
        )

    def test_sem_historico(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = self.rodar(pasta, "--abrir")
            self.assertEqual(saida.returncode, 1)
            self.assertIn("Nao existe narracao", saida.stdout + saida.stderr)

    def test_audio_ja_apagado(self):
        with tempfile.TemporaryDirectory() as pasta:
            linha = {
                "quando": "2026-01-01 10:00:00",
                "arquivo": str(Path(pasta) / "sumiu.mp3"),
                "origem": "nota.md", "caracteres": 10, "duracao": 3.0,
                "voz": "v", "modelo": "m", "velocidade": 1.0,
            }
            (Path(pasta) / "historico.jsonl").write_text(
                json.dumps(linha) + "\n", encoding="utf-8")
            saida = self.rodar(pasta, "--abrir", "1")
            self.assertEqual(saida.returncode, 1)
            self.assertIn("saiu do disco", saida.stdout + saida.stderr)


class TestInterpretadorPortavel(unittest.TestCase):
    """`python` nao existe em Linux nem em macOS; `python3` falta em Windows."""

    def hooks(self) -> list[dict]:
        dados = json.loads((RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        return [h for grupo in dados["hooks"].values()
                for entrada in grupo for h in entrada["hooks"]]

    def test_hooks_escolhem_o_interpretador(self):
        for hook in self.hooks():
            comando = hook["command"]
            self.assertNotIn("args", hook, "args liga o exec form e ignora o fallback")
            self.assertIn("command -v python3", comando)
            self.assertIn("python", comando)

    def test_instrucao_cita_o_interpretador_em_uso(self):
        self.assertIn(sys.executable, narrar.instrucao())


class TestResumo(unittest.TestCase):
    def test_texto_curto_inteiro(self):
        self.assertEqual(speak.resumo("Uma frase curta."), "Uma frase curta.")

    def test_texto_longo_cortado(self):
        resumo = speak.resumo("palavra " * 50, limite=30)
        self.assertLessEqual(len(resumo), 30)
        self.assertTrue(resumo.endswith("…"))

    def test_quebra_de_linha_vira_espaco(self):
        self.assertEqual(speak.resumo("uma\nduas\n\ntres"), "uma duas tres")


if __name__ == "__main__":
    unittest.main(verbosity=2)
