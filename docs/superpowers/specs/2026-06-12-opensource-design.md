# 好策自动阅读 — 开源化设计文档

## 概述

将好策阅读平台自动化工具变为 GitHub 开源项目，面向普通学生用户，零门槛安装使用。

## 目标用户

任何好策平台的学生用户，无需编程知识。第一次运行时有中文引导，之后只需选书选任务。

## 文件结构

```
haoce/
  main.py                  # 入口，含首次引导 + 选书选任务
  config.example.ini       # 配置模板（占位符，无真实凭据）
  requirements.txt         # pip 依赖
  pyproject.toml           # 已有
  README.md                # 项目文档 + 安装使用指南
  LICENSE                  # MIT
  .gitignore               # 排除 config.ini, *.wav, *.mp3, config.ini.bak
  api/
    __init__.py
    base.py                # 好策 API 封装
    llm.py                 # LLM 客户端 (ollama / openai)
    tts.py                 # TTS 模块 (api / qwen / none)
```

## 首次运行引导

```
config.ini 不存在时自动触发

  "好策自动阅读 v1.0"
  "首次使用，请完成配置"
  ↓
  1) LLM 选择 (讨论/摘抄/报告):
     [1] OpenAI 兼容 API (推荐，需API Key)
     [2] 本地 Ollama (免费，需自行安装模型)
     [3] 跳过 (不提交讨论/摘抄/报告)
  ↓
  2) TTS 选择 (朗读配音):
     [1] TTS API (需提供 API Key 和接口地址)
     [2] 本地 TTS (免费，需 NVIDIA 显卡 4GB+ 显存)
     [3] 跳过 (不提交朗读任务)
  ↓
  输入好策账号密码
  ↓
  保存 config.ini → 登录 → 选书选任务
```

后续启动检测到 config.ini 存在则直接进入登录页。

## config.ini 结构

```ini
[account]
phone =                # 好策注册手机号
password =             # 好策登录密码

[llm]
backend = openai       # openai | ollama | none
model = gpt-4o
base_url = https://api.openai.com/v1
api_key =              # OpenAI API Key (ollama 后端不用填)

[tts]
backend =              # api | qwen | none
api_key =              # TTS API Key (qwen 后端不用填)
base_url =             # TTS API 地址 (qwen 后端不用填)
model_path =           # 本地模型路径 (api 后端不用填)
ffmpeg_path =          # 自定义 ffmpeg 路径，留空自动查找

[reading]
duration_per_chapter = 120
min_interval = 3
```

- config.ini 不提交到 git
- config.example.ini 作为模板提交，所有敏感字段留空

## tts.py 重构

### 后端路由

```python
def generate_reading_audio(text, voice="natural young male voice", config=None):
    backend = config["tts"]["backend"] if config else "none"
    if backend == "api":
        return _tts_api(text, voice, config)
    elif backend == "qwen":
        return _tts_qwen(text, voice, config)
    else:
        return None, None
```

- `_tts_api()`: 调 OpenAI 兼容 TTS API，返回 MP3 字节
- `_tts_qwen()`: 现有 Qwen3-TTS + ffmpeg 转 MP3
- `none`: 返回 (None, None)，朗读只提交文本

### 硬编码路径修复

| 改前 | 改后 |
|------|------|
| `_FFMPEG = "C:/tmp/ffmpeg/..."` | `shutil.which("ffmpeg")` |
| `wav_path = "C:/tmp/tts_reading.wav"` | `tempfile.mktemp(suffix=".wav")` |
| `mp3_path = "C:/tmp/tts_reading.mp3"` | `tempfile.mktemp(suffix=".mp3")` |

找不到 ffmpeg 则在启动时提示用户安装。

## base.py 改动

- `submit_reading_aloud` 签名不变，内部调用 tts 时透传 config
- `auto_complete_tasks` 在 target_tag="3" 且 tts backend="none" 时跳过

## llm.py 改动

- `load_config` 增加 `[tts]` 段解析
- 现有逻辑不变

## main.py 改动

- `load_config` 检测 config.ini 是否存在
- 不存在则进入首次引导流程（LLM + TTS + 账号）
- 存在则直接登录（保留临时输入他人账号密码的功能）
- 任务完成后回到选任务页面（已完成）

## 需创建的新文件

| 文件 | 内容 |
|------|------|
| `README.md` | 项目介绍、安装步骤、配置说明、使用指南、免责声明 |
| `LICENSE` | MIT 许可证 |
| `requirements.txt` | requests, qwen-tts, soundfile, torch 等 |
| `config.example.ini` | 同上结构，所有字段留空或默认值 |
| `.gitignore` | __pycache__, *.pyc, config.ini, config.ini.bak, *.wav, *.mp3, dist, build |

## 需排除的文件

- `config.ini` 从 git 追踪中移除（已备份为 config.ini.bak，加入 .gitignore）
- `__pycache__/` 目录
