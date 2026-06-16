# -*- coding: utf-8 -*-
"""
TTS 语音合成 — 支持 api / qwen / none 三种后端
"""
import os
import shutil
import subprocess
import tempfile
from typing import Optional

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

_tts_model: Optional[Qwen3TTSModel] = None

DEFAULT_MODEL_PATH = os.path.expanduser(
    "~/.cache/modelscope/hub/models/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
)


def _get_ffmpeg(config: dict = None) -> Optional[str]:
    """查找 ffmpeg 路径：config 指定 → 系统 PATH"""
    custom = (config or {}).get("tts", {}).get("ffmpeg_path", "")
    if custom and os.path.exists(custom):
        return custom
    found = shutil.which("ffmpeg")
    if found:
        return found
    return None


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


def _wav_to_mp3(wav_path: str, output_path: str, config: dict = None) -> bool:
    """用 ffmpeg 将 WAV 转为 MP3 (44.1kHz, mono, 128kbps)"""
    ffmpeg = _get_ffmpeg(config)
    if not ffmpeg:
        print("    [TTS] ffmpeg not found, install ffmpeg or set ffmpeg_path in config.ini")
        return False
    try:
        subprocess.run([
            ffmpeg, "-i", wav_path,
            "-af", "volume=3.0",
            "-ar", "44100", "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", "128k",
            output_path, "-y",
        ], check=True, capture_output=True, timeout=120)
        return True
    except subprocess.CalledProcessError:
        return False


def _tts_api(text: str, voice: str, config: dict) -> tuple:
    """TTS API 后端：调 OpenAI 兼容 TTS 接口

    注意：OpenAI TTS API 只接受预设音色名（alloy/echo/fable/onyx/nova/shimmer），
    不能传自然语言描述。voice 参数（自然语言）只对 qwen 后端有意义，
    这里通过 config[tts][voice] 让用户配置 OpenAI 预设音色。
    """
    import requests
    tts_cfg = config.get("tts", {})
    base_url = tts_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = tts_cfg.get("api_key", "")
    model = tts_cfg.get("model", "tts-1")
    api_voice = tts_cfg.get("voice", "alloy")
    try:
        resp = requests.post(
            f"{base_url}/audio/speech",
            json={
                "model": model,
                "input": text,
                "voice": api_voice,
                "response_format": "mp3",
                "speed": 1.0,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        resp.raise_for_status()
        print(f"    [TTS] API MP3 ({len(resp.content)} bytes)")
        return resp.content, None
    except Exception as e:
        print(f"    [TTS] API failed: {e}")
        return None, None


def _tts_qwen(text: str, voice: str, config: dict) -> tuple:
    """本地 Qwen3-TTS 后端：生成 WAV → ffmpeg 转 MP3"""
    tts_cfg = config.get("tts", {})
    model_path = tts_cfg.get("model_path", "") or None
    model = _get_model(model_path)
    if model is None:
        return None, None

    wav_path = None
    mp3_path = None
    try:
        prompt = f"A {voice}, reading an English passage aloud at a natural steady clear pace."
        wavs, sr = model.generate_voice_design(
            text=text, language="English", instruct=prompt,
        )
        # 用 NamedTemporaryFile 替代已弃用的 mktemp，避免竞态与文件泄漏
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        sf.write(wav_path, wavs[0], sr)
        print(f"    [TTS] WAV saved ({len(wavs[0])/sr:.1f}s)")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name
        if os.path.exists(wav_path) and _wav_to_mp3(wav_path, mp3_path, config):
            with open(mp3_path, "rb") as f:
                mp3_data = f.read()
            print(f"    [TTS] MP3 ({len(mp3_data)} bytes)")
            return mp3_data, wav_path
    except Exception as e:
        print(f"    [TTS] Generate failed: {e}")
    finally:
        # 清理临时文件：mp3 一定删；wav 仅在转换成功时保留返回路径外也清理
        # 注：成功路径下调用方只拿到 wav_path 字符串，文件已不再需要（MP3 已读入内存）
        if mp3_path and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError:
                pass

    return None, None


def generate_reading_audio(text: str, voice_instruct: str = "natural young male voice",
                           config: dict = None):
    """
    生成朗读音频

    Returns:
        (mp3_bytes_or_None, wav_path_or_None)
    """
    if config is None:
        config = {}
    backend = config.get("tts", {}).get("backend", "none")

    if backend == "api":
        return _tts_api(text, voice_instruct, config)
    elif backend == "qwen":
        return _tts_qwen(text, voice_instruct, config)
    else:
        return None, None
