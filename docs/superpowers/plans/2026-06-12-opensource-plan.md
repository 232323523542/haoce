# 好策开源化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将好策阅读平台自动化工具变为 GitHub 开源项目，支持首次运行引导、三种 LLM 后端、三种 TTS 后端、跨平台移植。

**Architecture:** 保持现有 api/ 包结构不变。main.py 新增首次引导向导（setup_wizard），config 解析扩展 [tts] 段。tts.py 重构为后端路由（api/qwen/none），硬编码路径改为 shutil.which + tempfile。

**Tech Stack:** Python 3.10+, requests, qwen-tts, soundfile, torch, configparser

---

### Task 1: 更新 .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 写入新的 .gitignore**

```gitignore
__pycache__/
*.pyc
*.pyo
config.ini
config.ini.bak
*.wav
*.mp3
.DS_Store
*.egg-info/
dist/
build/
```

- [ ] **Step 2: 把 config.ini 从 git 追踪中移除（保留本地文件）**

```bash
git rm --cached config.ini
```

- [ ] **Step 3: 提交**

```bash
git add .gitignore
git commit -m "chore: 更新 .gitignore，排除敏感文件和临时产物"
```

---

### Task 2: 创建 config.example.ini

**Files:**
- Create: `config.example.ini`

- [ ] **Step 1: 写入配置模板**

```ini
[account]
; 好策注册手机号
phone =
; 好策登录密码
password =

[reading]
; 每章模拟阅读时长（秒），默认120秒=2分钟
duration_per_chapter = 120
; 请求最小间隔（秒）
min_interval = 3
; 要阅读的书ID列表，逗号分隔（留空则处理所有书）
book_list =
; 是否只处理未读完的书
only_unfinished = true

[llm]
; LLM 后端: openai | ollama | none（none=跳过讨论/摘抄/报告）
backend = openai
; 模型名
model = gpt-4o
; API 地址（Ollama 通常是 http://localhost:11434）
base_url = https://api.openai.com/v1
; API Key（Ollama 后端不用填）
api_key =

[tts]
; TTS 后端: api | qwen | none（none=不提交朗读音频）
backend =
; API Key（qwen 后端不用填）
api_key =
; API 地址（qwen 后端不用填）
base_url =
; 本地模型路径（api 后端不用填）
model_path =
; 自定义 ffmpeg 路径，留空自动从系统 PATH 查找
ffmpeg_path =
```

- [ ] **Step 2: 提交**

```bash
git add config.example.ini
git commit -m "feat: 添加 config.example.ini 配置模板"
```

---

### Task 3: 创建 requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: 从 pyproject.toml 提取依赖写入**

```
requests>=2.25
qwen-tts>=0.1
soundfile>=0.12
torch>=2.7
torchaudio>=2.7
ollama
```

- [ ] **Step 2: 提交**

```bash
git add requirements.txt
git commit -m "feat: 添加 requirements.txt"
```

---

### Task 4: 创建 LICENSE

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: 写入 MIT 许可证**

```
MIT License

Copyright (c) 2026 ZhuanZ1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: 提交**

```bash
git add LICENSE
git commit -m "feat: 添加 MIT LICENSE"
```

---

### Task 5: 创建 README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写入 README**

````markdown
# 好策自动阅读

好策(HaoCe)阅读平台自动化工具，支持模拟阅读、讨论、摘抄、报告、朗读全自动提交。

## 功能

- **模拟阅读** — 自动上报阅读时长和章节进度
- **讨论** — AI 生成讨论主题帖 + 回复，引用真实章节内容
- **摘抄** — AI 生成原文摘抄 + 赏析点评
- **报告** — AI 生成读书报告
- **朗读** — TTS 生成语音朗读并上传

## 安装

1. 安装 Python 3.10+

2. 下载本项目

```bash
git clone https://github.com/ZhuanZ1/haoce.git
cd haoce
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. （可选）安装 ffmpeg，用于本地 TTS 音频转换

- Windows: `winget install ffmpeg` 或从 https://ffmpeg.org 下载
- Mac: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

## 使用

```bash
python main.py
```

首次运行会进入配置引导：
1. 选择 LLM 后端（OpenAI API / 本地 Ollama / 跳过）
2. 选择 TTS 后端（TTS API / 本地 Qwen3-TTS / 跳过）
3. 输入好策账号密码

配置完成后每次启动直接选书选任务即可。

### LLM 配置说明

| 后端 | 说明 | 前置条件 |
|------|------|---------|
| OpenAI API | 付费，最省心 | 注册 OpenAI 获取 API Key |
| 本地 Ollama | 免费 | 安装 Ollama，下载模型 |
| 跳过 | 不提交讨论/摘抄/报告 | 无 |

### TTS 配置说明

| 后端 | 说明 | 前置条件 |
|------|------|---------|
| TTS API | 付费，通用 TTS 接口 | API Key + 接口地址 |
| 本地 Qwen3-TTS | 免费，音质好 | NVIDIA 显卡 4GB+ 显存，下载模型 |
| 跳过 | 朗读只提交文本，不上传音频 | 无 |

## 配置

配置保存在 `config.ini`（首次运行自动生成），也可手动复制 `config.example.ini` 为 `config.ini` 后修改。

```ini
[account]
phone = 13800138000
password = your_password

[llm]
backend = openai
model = gpt-4o
base_url = https://api.openai.com/v1
api_key = sk-your-key-here

[tts]
backend = qwen
model_path = ~/.cache/modelscope/hub/models/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign

[reading]
duration_per_chapter = 120
min_interval = 3
```

## 本地 TTS 模型下载

如果选择本地 Qwen3-TTS：

```python
from modelscope import snapshot_download
snapshot_download("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
```

或在 `config.ini` 的 `[tts]` 段设置 `model_path` 指向已有模型目录。

## 免责声明

本工具仅供学习研究使用。使用者应遵守好策平台的使用条款，自行承担使用风险。

## License

MIT
````

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "feat: 添加 README.md"
```

---

### Task 6: 重构 tts.py — 后端路由 + 硬编码路径修复

**Files:**
- Modify: `api/tts.py` (全部重写)

- [ ] **Step 1: 重写 tts.py**

```python
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
    """TTS API 后端：调 OpenAI 兼容 TTS 接口"""
    import requests
    tts_cfg = config.get("tts", {})
    base_url = tts_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = tts_cfg.get("api_key", "")
    model = tts_cfg.get("model", "tts-1")
    try:
        resp = requests.post(
            f"{base_url}/audio/speech",
            json={
                "model": model,
                "input": text,
                "voice": "alloy",
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

    try:
        prompt = f"A {voice}, reading an English passage aloud at a natural steady clear pace."
        wavs, sr = model.generate_voice_design(
            text=text, language="English", instruct=prompt,
        )
        wav_path = tempfile.mktemp(suffix=".wav")
        sf.write(wav_path, wavs[0], sr)
        print(f"    [TTS] WAV saved ({len(wavs[0])/sr:.1f}s)")

        mp3_path = tempfile.mktemp(suffix=".mp3")
        if os.path.exists(wav_path) and _wav_to_mp3(wav_path, mp3_path, config):
            with open(mp3_path, "rb") as f:
                mp3_data = f.read()
            print(f"    [TTS] MP3 ({len(mp3_data)} bytes)")
            return mp3_data, wav_path
    except Exception as e:
        print(f"    [TTS] Generate failed: {e}")

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
```

- [ ] **Step 2: 提交**

```bash
git add api/tts.py
git commit -m "refactor: tts.py 支持 api/qwen/none 三种后端，硬编码路径改用 shutil.which + tempfile"
```

---

### Task 7: 更新 base.py — 透传 config 到 TTS

**Files:**
- Modify: `api/base.py:406-465` (submit_reading_aloud 方法)
- Modify: `api/base.py:783` (auto_complete_tasks 中朗读部分的 TTS 跳过逻辑)

- [ ] **Step 1: 给 HaoceAPI 添加 config 属性**

在 `__init__` 方法中加入 `self.config = None`:

```python
# 在 __init__ 末尾加一行
self.config = None  # 由 main.py 设置，透传给 TTS
```

- [ ] **Step 2: 修改 submit_reading_aloud，透传 config**

将 `api/base.py:420` 行附近的 `from api.tts import generate_reading_audio` 之后的调用改为：

```python
        if amr_data is None:
            amr_data, _ = generate_reading_audio(text, voice_instruct=voice, config=self.config)
```

- [ ] **Step 3: 朗读任务跳过 TTS=none 的情况**

在 `auto_complete_tasks` 的 `tid == "3"` 分支中，`submit_reading_aloud` 调用前加入判断。找到约第 837 行附近的 `ok = self.submit_reading_aloud(...)`:

```python
                        tts_backend = (self.config or {}).get("tts", {}).get("backend", "none")
                        if tts_backend == "none":
                            print("    [SKIP] TTS 未配置，仅提交文本")
                            passage = passage or text
                            resp = self.create_topic(
                                book_id=book_id, tag_id="3",
                                title=passage_title, content=passage,
                            )
                            ok = resp.get("error", -1) == 0
                        else:
                            ok = self.submit_reading_aloud(
                                book_id=book_id, text=passage, title=passage_title)
```

- [ ] **Step 4: 提交**

```bash
git add api/base.py
git commit -m "feat: base.py 透传 config 到 TTS，支持 tts=none 跳过音频"
```

---

### Task 8: 更新 main.py — 首次引导 + config 扩展

**Files:**
- Modify: `main.py:25-41` (load_config 函数)
- Modify: `main.py:56-76` (main 函数开头)

- [ ] **Step 1: 扩展 load_config 支持 [tts] 段**

```python
def load_config(path: str = "config.ini") -> dict:
    c = configparser.ConfigParser()
    c.read(path, encoding="utf-8")
    cfg = {
        "phone": "", "password": "",
        "llm_backend": "ollama", "llm_model": "qwen2.5:7b",
        "llm_base_url": "http://localhost:11434", "llm_api_key": "",
        "tts_backend": "", "tts_api_key": "", "tts_base_url": "",
        "tts_model_path": "", "tts_ffmpeg_path": "",
        "skip_reading": False,
    }
    if c.has_section("account"):
        cfg["phone"] = c.get("account", "phone", fallback="").strip()
        cfg["password"] = c.get("account", "password", fallback="").strip()
    if c.has_section("reading"):
        cfg["skip_reading"] = c.getboolean("reading", "skip_reading", fallback=False)
    if c.has_section("llm"):
        cfg["llm_backend"] = c.get("llm", "backend", fallback="ollama").strip()
        cfg["llm_model"] = c.get("llm", "model", fallback="qwen2.5:7b").strip()
        cfg["llm_base_url"] = c.get("llm", "base_url", fallback="http://localhost:11434").strip()
        cfg["llm_api_key"] = c.get("llm", "api_key", fallback="").strip()
    if c.has_section("tts"):
        cfg["tts_backend"] = c.get("tts", "backend", fallback="").strip()
        cfg["tts_api_key"] = c.get("tts", "api_key", fallback="").strip()
        cfg["tts_base_url"] = c.get("tts", "base_url", fallback="").strip()
        cfg["tts_model_path"] = c.get("tts", "model_path", fallback="").strip()
        cfg["tts_ffmpeg_path"] = c.get("tts", "ffmpeg_path", fallback="").strip()
    return cfg


def save_config(cfg: dict, path: str = "config.ini"):
    """保存配置到文件"""
    c = configparser.ConfigParser()
    c["account"] = {"phone": cfg["phone"], "password": cfg["password"]}
    c["reading"] = {
        "duration_per_chapter": "120",
        "min_interval": "3",
    }
    c["llm"] = {
        "backend": cfg["llm_backend"],
        "model": cfg["llm_model"],
        "base_url": cfg["llm_base_url"],
        "api_key": cfg["llm_api_key"],
    }
    c["tts"] = {
        "backend": cfg["tts_backend"],
        "api_key": cfg["tts_api_key"],
        "base_url": cfg["tts_base_url"],
        "model_path": cfg["tts_model_path"],
        "ffmpeg_path": cfg["tts_ffmpeg_path"],
    }
    with open(path, "w", encoding="utf-8") as f:
        c.write(f)
    print(f"配置已保存到 {path}")
```

- [ ] **Step 2: 添加 setup_wizard 函数**

```python
def setup_wizard() -> dict:
    """首次运行引导"""
    cfg = load_config("")  # 获取默认值

    print("=" * 50)
    print("好策自动阅读 v1.0 — 首次配置")
    print("=" * 50)

    # 1) LLM
    print("\n[1/3] LLM 后端 (讨论/摘抄/报告):")
    print("  [1] OpenAI 兼容 API (推荐，需API Key)")
    print("  [2] 本地 Ollama (免费，需自行安装模型)")
    print("  [3] 跳过 (不提交讨论/摘抄/报告)")
    while True:
        s = input_str("选择 (1-3): ")
        if s == "1":
            cfg["llm_backend"] = "openai"
            cfg["llm_api_key"] = input_str("API Key: ")
            cfg["llm_base_url"] = input_str("API 地址 [https://api.openai.com/v1]: ") or "https://api.openai.com/v1"
            cfg["llm_model"] = input_str("模型名 [gpt-4o]: ") or "gpt-4o"
            break
        elif s == "2":
            cfg["llm_backend"] = "ollama"
            cfg["llm_base_url"] = input_str("Ollama 地址 [http://localhost:11434]: ") or "http://localhost:11434"
            cfg["llm_model"] = input_str("模型名 [qwen2.5:7b]: ") or "qwen2.5:7b"
            break
        elif s == "3":
            cfg["llm_backend"] = "none"
            break
        print("无效")

    # 2) TTS
    print("\n[2/3] TTS 后端 (朗读配音):")
    print("  [1] TTS API (需提供 API Key 和接口地址)")
    print("  [2] 本地 TTS (免费，需 NVIDIA 显卡 4GB+ 显存)")
    print("  [3] 跳过 (不提交朗读任务)")
    while True:
        s = input_str("选择 (1-3): ")
        if s == "1":
            cfg["tts_backend"] = "api"
            cfg["tts_api_key"] = input_str("TTS API Key: ")
            cfg["tts_base_url"] = input_str("TTS API 地址 [https://api.openai.com/v1]: ") or "https://api.openai.com/v1"
            break
        elif s == "2":
            cfg["tts_backend"] = "qwen"
            cfg["tts_model_path"] = input_str("模型路径 (回车用默认): ") or ""
            break
        elif s == "3":
            cfg["tts_backend"] = "none"
            break
        print("无效")

    # 3) 账号
    print("\n[3/3] 好策账号:")
    cfg["phone"] = input_str("手机号: ")
    cfg["password"] = input_str("密码: ")

    save_config(cfg)
    return cfg
```

- [ ] **Step 3: 修改 main() 开头，检测 config.ini 是否存在**

将 `main.py:56-81` 替换为：

```python
def main():
    import os
    if not os.path.exists("config.ini"):
        cfg = setup_wizard()
        print("\n按回车开始使用...")
        input()
    else:
        cfg = load_config()

    print("\n" + "=" * 40)
    print("好策自动阅读")
    print("=" * 40)

    # 账号
    saved_phone = cfg["phone"]
    if saved_phone:
        print(f"\n已存账号: {saved_phone}")
        phone = input_str("输入手机号 (回车用已存账号): ")
        if phone == "":
            phone = saved_phone
            password = cfg["password"]
        else:
            password = input_str("密码: ")
    else:
        phone = input_str("手机号: ")
        password = input_str("密码: ")
    if not phone or not password:
        print("手机号和密码不能为空"); sys.exit(1)

    # LLM
    llm = create_llm_client(backend=cfg["llm_backend"], model=cfg["llm_model"],
                            base_url=cfg["llm_base_url"], api_key=cfg["llm_api_key"])
    api = HaoceAPI(HaoceAccount(phone, password), llm_client=llm)
    # 透传完整 config 给 TTS
    api.config = {
        "tts": {
            "backend": cfg["tts_backend"],
            "api_key": cfg["tts_api_key"],
            "base_url": cfg["tts_base_url"],
            "model_path": cfg["tts_model_path"],
            "ffmpeg_path": cfg["tts_ffmpeg_path"],
        }
    }
```

- [ ] **Step 4: 提交**

```bash
git add main.py
git commit -m "feat: 添加首次运行引导向导，扩展 config 支持 TTS 段"
```

---

### Task 9: 最终验证

- [ ] **Step 1: 检查 git 状态**

```bash
cd C:/Users/ZhuanZ1/Desktop/ai1/haoce
git status
```

确保 config.ini 不在 staged 中，config.ini.bak 被 .gitignore 忽略。

- [ ] **Step 2: 验证 Python 语法**

```bash
python -m py_compile main.py api/base.py api/llm.py api/tts.py
```

- [ ] **Step 3: 提交（如有残留改动）**

```bash
git add -A
git status
```

---

### Task 10: 从 git 历史中清除 config.ini 的敏感信息

**Files:**
- 操作：git filter-branch 或 git filter-repo

- [ ] **Step 1: 检查 config.ini 在哪些 commit 中存在**

```bash
git log --all --full-history -- config.ini
```

- [ ] **Step 2: 使用 git filter-branch 清除**

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.ini" \
  --prune-empty --tag-name-filter cat -- --all
```

- [ ] **Step 3: 清理引用**

```bash
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```
