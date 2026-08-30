"""Costura de MP3: limpa cabecalhos e mede duracao contando frames.

Cada resposta da API vem como um MP3 completo: tag ID3 e um frame Xing que
declara a duracao daquele trecho. Concatenados crus, o player le o Xing do
primeiro trecho, acredita que o arquivo inteiro dura 18 segundos e recusa
qualquer seek alem disso. Por isso todo trecho e limpo antes de emendar.
"""

from __future__ import annotations

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
AMOSTRAGENS = [44100, 48000, 32000, 0]
AMOSTRAS_POR_FRAME = 1152  # MPEG-1 Layer III


def _tamanho_id3(dados: bytes) -> int:
    if dados[:3] != b"ID3" or len(dados) < 10:
        return 0
    corpo = ((dados[6] & 0x7F) << 21 | (dados[7] & 0x7F) << 14
             | (dados[8] & 0x7F) << 7 | (dados[9] & 0x7F))
    return 10 + corpo


def _ler_frame(dados: bytes, i: int) -> tuple[int, int] | None:
    """Devolve (tamanho, amostragem) do frame que comeca em i, ou None."""
    if i + 4 > len(dados) or dados[i] != 0xFF or (dados[i + 1] & 0xE0) != 0xE0:
        return None
    versao = (dados[i + 1] >> 3) & 0x03   # 3 = MPEG-1
    camada = (dados[i + 1] >> 1) & 0x03   # 1 = Layer III
    bitrate = BITRATES[(dados[i + 2] >> 4) & 0x0F]
    amostragem = AMOSTRAGENS[(dados[i + 2] >> 2) & 0x03]
    padding = (dados[i + 2] >> 1) & 0x01
    if versao != 3 or camada != 1 or bitrate == 0 or amostragem == 0:
        return None
    return 144 * bitrate * 1000 // amostragem + padding, amostragem


def limpar(dados: bytes) -> bytes:
    """Remove a tag ID3 e o frame Xing/Info do inicio do trecho."""
    inicio = _tamanho_id3(dados)
    frame = _ler_frame(dados, inicio)
    if frame:
        tamanho, _ = frame
        miolo = dados[inicio:inicio + tamanho]
        if b"Xing" in miolo or b"Info" in miolo:  # frame de metadados, nao de audio
            inicio += tamanho
    return dados[inicio:]


def duracao(dados: bytes) -> float:
    """Segundos de audio, contados frame a frame."""
    i, amostras, amostragem = 0, 0, 44100
    while i < len(dados):
        frame = _ler_frame(dados, i)
        if frame is None:
            i += 1
            continue
        tamanho, amostragem = frame
        amostras += AMOSTRAS_POR_FRAME
        i += tamanho
    return amostras / amostragem
