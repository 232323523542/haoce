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

    def _parse_json_response(self, text: str, tag_type: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""
        text = text.strip()
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
