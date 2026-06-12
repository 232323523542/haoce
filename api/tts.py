# -*- coding: utf-8 -*-
"""
TTS 语音合成 — Qwen3-TTS 本地模型
生成朗读任务的音频
"""
import os
import subprocess
from typing import Optional

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

# 单例缓存模型
_tts_model: Optional[Qwen3TTSModel] = None

# 默认模型路径
DEFAULT_MODEL_PATH = os.path.expanduser(
    "~/.cache/modelscope/hub/models/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
)

# ffmpeg 路径
_FFMPEG = "C:/tmp/ffmpeg/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe"


def _get_model(model_path: str = None) -> Optional[Qwen3TTSModel]:
    global _tts_model
    if _tts_model is not None:
        return _tts_model
    path = model_path or DEFAULT_MODEL_PATH
    if not os.path.isdir(path):
        print(f"    [TTS] Model not found: {path}")
        return None
    try:
        print("    [TTS] Loading Qwen3-TTS model...")
        _tts_model = Qwen3TTSModel.from_pretrained(
            path, device_map="cuda:0", dtype=torch.bfloat16,
        )
        vram = torch.cuda.memory_allocated(0) / 1e9
        print(f"    [TTS] Model ready, VRAM: {vram:.1f} GB")
        return _tts_model
    except Exception as e:
        print(f"    [TTS] Load failed: {e}")
        return None


def _wav_to_amr(wav_path: str, output_path: str) -> bool:
    """用 ffmpeg 将 WAV 转为 AMR-NB (8000Hz, mono, 12.2kbps)"""
    if not os.path.exists(_FFMPEG):
        print(f"    [TTS] ffmpeg not found: {_FFMPEG}")
        return False
    try:
        subprocess.run([
            _FFMPEG, "-i", wav_path,
            "-af", "volume=3.0",
            "-ar", "8000", "-ac", "1",
            "-c:a", "libopencore_amrnb", "-b:a", "12.2k",
            output_path, "-y",
        ], check=True, capture_output=True, timeout=120)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [TTS] ffmpeg error: {e.stderr.decode()[:200] if e.stderr else e}")
        return False


def _wav_to_mp3(wav_path: str, output_path: str) -> bool:
    """用 ffmpeg 将 WAV 转为 MP3 (44.1kHz, mono, 128kbps)"""
    if not os.path.exists(_FFMPEG):
        return False
    try:
        subprocess.run([
            _FFMPEG, "-i", wav_path,
            "-af", "volume=3.0",
            "-ar", "44100", "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", "128k",
            output_path, "-y",
        ], check=True, capture_output=True, timeout=120)
        return True
    except subprocess.CalledProcessError:
        return False


def generate_reading_audio(text: str, voice_instruct: str = "natural young male voice",
                           model_path: str = None):
    """
    生成朗读音频

    Returns:
        (amr_bytes, wav_path_or_None)
    """
    model = _get_model(model_path)
    wav_path = None

    if model is not None:
        try:
            prompt = f"A {voice_instruct}, reading an English passage aloud at a natural steady clear pace."
            wavs, sr = model.generate_voice_design(
                text=text, language="English", instruct=prompt,
            )
            wav_path = "C:/tmp/tts_reading.wav"
            sf.write(wav_path, wavs[0], sr)
            print(f"    [TTS] WAV saved ({len(wavs[0])/sr:.1f}s)")
        except Exception as e:
            print(f"    [TTS] Generate failed: {e}")

    # WAV → MP3 / AMR 转换
    mp3_path = "C:/tmp/tts_reading.mp3"
    amr_path = "C:/tmp/tts_reading.amr"
    mp3_data = None
    amr_data = None

    if wav_path and os.path.exists(wav_path) and os.path.exists(_FFMPEG):
        if _wav_to_mp3(wav_path, mp3_path):
            with open(mp3_path, "rb") as f:
                mp3_data = f.read()
            print(f"    [TTS] MP3 ({len(mp3_data)} bytes)")
        if _wav_to_amr(wav_path, amr_path):
            with open(amr_path, "rb") as f:
                amr_data = f.read()

    if mp3_data or amr_data:
        return mp3_data, amr_data, wav_path

    # 兜底
    print(f"    [TTS] WARNING: using silence fallback")
    return None, _make_silence_amr(), wav_path


def _make_silence_amr(duration_sec: int = 30) -> bytes:
    """兜底: 生成静音 AMR (仅在 ffmpeg 不可用时使用)"""
    header = b"\x23\x21\x41\x4d\x52\x0a"  # #!AMR\n
    frame_count = duration_sec * 50
    sid_frame = bytes([
        0x00, 0x06, 0x98, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    return header + sid_frame * frame_count
