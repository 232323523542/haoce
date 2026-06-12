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
2. 选择 TTS 后端（TTS API / 本地 TTS / 跳过）
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
| 本地 TTS | 免费，音质好 | NVIDIA 显卡 4GB+ 显存，下载模型 |
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

如果选择本地 TTS：

```python
from modelscope import snapshot_download
snapshot_download("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
```

或在 `config.ini` 的 `[tts]` 段设置 `model_path` 指向已有模型目录。

## 免责声明

本工具仅供学习研究使用。使用者应遵守好策平台的使用条款，自行承担使用风险。

## License

MIT
