# backend/services/audio_extractor.py
import os
from pathlib import Path

import yt_dlp

BASE_DIR = Path(__file__).resolve().parents[2]  # project root
AUDIO_DIR = BASE_DIR / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def extract_youtube_audio(video_id: str) -> str:
    """
    Download audio for a YouTube video and return the local file path.
    Output: data/audio/<video_id>.mp3
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    out_tmpl = str(AUDIO_DIR / f"{video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp will convert to mp3 via postprocessor
        audio_path = AUDIO_DIR / f"{video_id}.mp3"

    if not audio_path.exists():
        raise RuntimeError(f"Audio file not found at {audio_path}")

    return str(audio_path)
