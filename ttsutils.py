from io import BytesIO
import base64

from gtts import gTTS


def text_to_speech_bytes(text: str) -> bytes:
    """テキストを音声 (mp3) バイト列に変換"""
    buf = BytesIO()
    gTTS(text=text, lang="ja", slow=False).write_to_fp(buf)
    return buf.getvalue()


def text_to_data_url(text: str) -> str:
    """
    Outputs data:audio/mpeg;base64,... formed audio.
    """
    audio_data = text_to_speech_bytes(text)
    return "data:audio/mpeg;base64," + base64.b64encode(audio_data).decode()
