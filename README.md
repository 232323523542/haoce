# 好策自动阅读

好策（haoce.com）阅读任务自动完成脚本。

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)

## 能做什么

- 自动上报阅读时长和进度
- 自动完成讨论（发帖 + 回复）
- 自动完成摘抄
- 自动完成报告
- 自动完成朗读（TTS 生成音频上传）

## 安装

装好 Python 3.10+，然后：

```bash
git clone https://github.com/232323523542/haoce.git
cd haoce
pip install -r requirements.txt
```

需要 ffmpeg（本地 TTS 用）：

- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

## 使用

```bash
python main.py
```

第一次运行会让你选 LLM 和 TTS 怎么配，之后直接选书选任务。

### LLM（讨论/摘抄/报告用）

- **OpenAI API**：买个 key 填进去就行
- **Ollama 本地**：免费，装好 Ollama 下个模型就能用
- **跳过**：不提交讨论/摘抄/报告

### TTS（朗读配音用）

- **TTS API**：买个 key 填进去
- **本地 TTS**：免费，需要 NVIDIA 显卡 4GB 以上显存
- **跳过**：不做朗读任务

## 依赖

```
requests
qwen-tts
soundfile
torch
torchaudio
ollama
```

## 免责

仅供学习，用了后果自负。

## License

MIT
