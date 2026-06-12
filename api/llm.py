# -*- coding: utf-8 -*-
"""
LLM 客户端 — 支持 Ollama 本地模型和 OpenAI 兼容 API
用于生成读书讨论、摘抄、报告的真实内容
"""
import json
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """发送对话，返回文本回复"""
        ...

    def generate_topic(self, book_title: str, tag_type: str,
                       chapters: list[str] = None,
                       book_author: str = "") -> Optional[dict]:
        """
        根据书籍信息生成一条任务提交内容

        Args:
            book_title: 书名
            tag_type: "0"=讨论, "5"=报告, "6"=摘抄
            chapters: 章节标题列表
            book_author: 作者

        Returns:
            {"title": "...", "content": "...", "yanwen": "..."} 或 None
        """
        chapter_hints = ""
        if chapters:
            sample = chapters[:8]
            chapter_hints = "章节列表: " + ", ".join(sample)

        prompts = {
            "0": {
                "system": "你是一名大学生，正在完成英语阅读课的讨论作业。请根据书籍内容写出真实的读后感讨论帖。用英文写作，语气自然像学生，不要用 AI 腔。只返回 JSON，不要其他文字。",
                "user": f"""书名: {book_title}
{chapter_hints}
请写一条讨论帖 (80-150词)，要有具体内容（提到书中情节或观点），语气自然。
返回格式: {{"title": "讨论标题", "content": "讨论正文"}}""",
            },
            "5": {
                "system": "你是一名大学生，正在完成英语阅读课的报告作业。请根据书籍写出简短的读书报告。用英文写作，语气自然像学生，不要用 AI 腔。只返回 JSON，不要其他文字。",
                "user": f"""书名: {book_title}
{chapter_hints}
请写一篇读书报告 (120-180词)，包含对主题的分析和个人感受。
返回格式: {{"title": "报告标题", "content": "报告正文"}}""",
            },
            "6": {
                "system": "你是一名大学生，正在完成英语阅读课的摘抄作业。请根据书籍写一条摘抄。用英文写作，语气自然像学生，不要用 AI 腔。只返回 JSON，不要其他文字。",
                "user": f"""书名: {book_title}
{chapter_hints}
请做一条摘抄：1) 摘抄一段"原文"（根据你对这本书的了解编一段合理的英文段落，30-60词）2) 写一段赏析点评 (40-80词)
返回格式: {{"title": "摘抄标题", "yanwen": "原文段落", "content": "赏析点评"}}""",
            },
        }

        prompt = prompts.get(tag_type)
        if not prompt:
            print(f"    [WARN] 未知任务类型: {tag_type}")
            return None

        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

        for attempt in range(2):
            try:
                response = self.chat(messages)
                return self._parse_json_response(response, tag_type)
            except Exception as e:
                print(f"    [WARN] LLM 调用失败 (尝试 {attempt+1}/2): {e}")
                if attempt == 0:
                    time.sleep(5)

        return None

    def generate_reading_passage(self, book_title: str,
                                 chapters: list[str] = None,
                                 book_author: str = "") -> Optional[dict]:
        """
        生成一段朗读文本 — 模仿书中段落的风格，不是讨论帖

        Returns:
            {"title": "章节标题", "content": "朗读段落文本"}
        """
        chapter_hints = ""
        if chapters:
            chapter_hints = "章节: " + ", ".join(chapters[:6])

        messages = [
            {"role": "system", "content": "你正在朗读一本英文书的一段原文。请写一段像是从这本书中摘录的英文段落，用于朗读练习。语言流畅自然，像是在读书中的内容。只返回 JSON，不要其他文字。"},
            {"role": "user", "content": f"书名: {book_title}\n{chapter_hints}\n请写一段像是从这本书中摘出的英文段落（60-100词），适合朗读。要听起来像书中的原文。\n返回格式: {{\"title\": \"段落所属章节名\", \"content\": \"朗读的段落文本\"}}"},
        ]

        for attempt in range(2):
            try:
                response = self.chat(messages)
                result = self._parse_json_response(response, "reading")
                if result:
                    return result
            except Exception as e:
                print(f"    [WARN] LLM 失败 (尝试 {attempt+1}/2): {e}")
                if attempt == 0:
                    time.sleep(5)
        return None

    def generate_reply(self, book_title: str, topic_title: str = "",
                       chapters: list[str] = None) -> Optional[str]:
        """
        生成一条讨论回复（40-80词，对话语气，无需标题）

        Args:
            book_title: 书名
            topic_title: 被回复的主题标题（可选，让回复更有针对性）
            chapters: 章节列表

        Returns:
            回复文本，或 None
        """
        chapter_hints = ""
        if chapters:
            chapter_hints = "章节: " + ", ".join(chapters[:6])
        topic_hint = f'你正在回复主题「{topic_title}」' if topic_title else ''

        messages = [
            {"role": "system", "content": "你是一名大学生，正在英语阅读课论坛上回复同学的讨论帖。用英文写一段简短自然的回复（40-80词），像真实的学生对话，不要 AI 腔。只返回回复文本，不要 JSON、不要标题。"},
            {"role": "user", "content": f"书名: {book_title}\n{chapter_hints}\n{topic_hint}\n请写一段回复，表达你的看法或补充观点（40-80词，直接回复即可，不要格式）。"},
        ]

        for attempt in range(2):
            try:
                text = self.chat(messages).strip()
                # 去掉模型可能多余输出的引号或标记
                text = text.strip('"').strip("'").strip()
                if len(text.split()) >= 15:
                    return text
                print(f"    [WARN] 回复太短 ({len(text.split())}词), 重试")
            except Exception as e:
                print(f"    [WARN] LLM 失败 (尝试 {attempt+1}/2): {e}")
                if attempt == 0:
                    time.sleep(5)
        return None

    def _parse_json_response(self, text: str, tag_type: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""
        text = text.strip()

        # 处理多行 JSON 对象（模型可能把 title 和 content 分成两个对象）
        if '\n{' in text:
            merged = {}
            for line in text.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        merged.update(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            if merged:
                try:
                    self._validate(merged, tag_type)
                    return merged
                except ValueError:
                    pass

        # 尝试直接解析
        try:
            result = json.loads(text)
            self._validate(result, tag_type)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试提取 ```json ... ``` 代码块
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1))
                self._validate(result, tag_type)
                return result
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试提取第一个 {...} 对象
        m = re.search(r'\{[^{}]*"title"[^{}]*\}', text, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
                self._validate(result, tag_type)
                return result
            except (json.JSONDecodeError, ValueError):
                pass

        print(f"    [WARN] 无法解析 LLM 返回: {text[:100]}...")
        return None

    @staticmethod
    def _validate(result: dict, tag_type: str):
        """验证返回结果包含必要字段"""
        if "title" not in result or "content" not in result:
            raise ValueError("缺少 title 或 content 字段")
        if tag_type == "6" and "yanwen" not in result:
            raise ValueError("摘抄需要 yanwen 字段")
        # reading 不需要 yanwen，只需要 title+content
        # 确保内容不太短
        if len(result.get("content", "").split()) < 20:
            raise ValueError("内容太短")


class OllamaClient(LLMClient):
    """Ollama 本地模型客户端"""

    def __init__(self, model: str = "qwen2.5:7b",
                 base_url: str = "http://localhost:11434",
                 timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def chat(self, messages: list[dict]) -> str:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


class OpenAIClient(LLMClient):
    """OpenAI 兼容 API 客户端"""

    def __init__(self, model: str = "gpt-4o",
                 base_url: str = "https://api.openai.com/v1",
                 api_key: str = "",
                 timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages: list[dict]) -> str:
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.8,
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def create_llm_client(backend: str = "ollama", **kwargs) -> Optional[LLMClient]:
    """工厂函数：根据配置创建 LLM 客户端"""
    if backend == "ollama":
        return OllamaClient(
            model=kwargs.get("model", "qwen2.5:7b"),
            base_url=kwargs.get("base_url", "http://localhost:11434"),
        )
    elif backend in ("openai", "openai_compatible"):
        return OpenAIClient(
            model=kwargs.get("model", "gpt-4o"),
            base_url=kwargs.get("base_url", "https://api.openai.com/v1"),
            api_key=kwargs.get("api_key", ""),
        )
    elif backend == "none":
        return None
    else:
        print(f"未知 LLM 后端: {backend}，将跳过任务提交")
        return None
