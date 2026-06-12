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

- **API**：买个 key 填进去就行
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

## 免责声明

本内容 100% 由 AI 生成，建议搭配 Claude Code 等 AI 编程助手使用，仅供学习。

**使用本工具可能违反好策平台的用户协议，导致账号被暂停或封禁，作者不承担任何责任。**

本工具仅供以下用途：

- 学习 Python 网络编程和逆向工程
- 研究 TTS 语音合成技术
- 了解自动化测试的工程实践

**严禁用于:**

- 提交学校课程的学分任务，这属于学术欺诈
- 任何形式的商业代刷服务
- 干扰平台正常运营

使用本工具即表示你已阅读并同意自行承担所有后果。

## License

MIT
