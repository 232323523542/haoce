# -*- coding: utf-8 -*-
"""
好策(HaoCe) 阅读平台自动阅读脚本
"""
import configparser
import io
import os
import sys
import time
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from api.base import HaoceAPI, HaoceAccount
from api.llm import create_llm_client


def input_str(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def load_config(path: str = "config.ini") -> dict:
    c = configparser.ConfigParser()
    c.read(path, encoding="utf-8")
    cfg = {
        "phone": "", "password": "", "skip_reading": False,
        "llm_backend": "ollama", "llm_model": "qwen2.5:7b",
        "llm_base_url": "http://localhost:11434", "llm_api_key": "",
        "tts_backend": "", "tts_api_key": "", "tts_base_url": "",
        "tts_model_path": "", "tts_ffmpeg_path": "",
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


def setup_wizard() -> dict:
    """首次运行引导"""
    cfg = load_config("")

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


def parse_discuss_req(desc: str):
    import re
    topics = replies = 0
    for pat in [r'发帖\s*(\d+)\s*次', r'发布\s*(\d+)\s*次\s*主题', r'(\d+)\s*次\s*主题帖']:
        m = re.search(pat, desc)
        if m: topics = int(m.group(1)); break
    for pat in [r'回复\D*?(\d+)\s*次', r'回帖\D*?(\d+)\s*次']:
        m = re.search(pat, desc)
        if m: replies = int(m.group(1)); break
    return topics, replies


def main():
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
    # 透传完整 TTS 配置
    api.config = {
        "tts": {
            "backend": cfg["tts_backend"],
            "api_key": cfg["tts_api_key"],
            "base_url": cfg["tts_base_url"],
            "model_path": cfg["tts_model_path"],
            "ffmpeg_path": cfg["tts_ffmpeg_path"],
        }
    }

    print("\n登录中...")
    if not api.login(): print("登录失败"); sys.exit(1)

    user = api.get_user_info()
    print(f"{user.get('name','?')} | {user.get('school','?')}")

    books = api.get_book_list()
    if not books: print("无书籍"); return

    # 收集任务信息
    entries = []
    print("\n加载中...")
    for b in books:
        bid = b["book_id"]
        title = b.get("book_id_merge", {}).get("book", bid)
        try:
            d = api.get_book_detail(bid)
        except Exception:
            continue
        bi = d.get("book", {})
        bj = d.get("bookJoin", {})
        tasks = {}
        # 朗读
        n = int(bi.get("tag_3_config", 0))
        if n: tasks["朗读"] = f"{int(bj.get('tag_3_cnt',0))}/{n}"
        # 摘抄
        n = int(bi.get("tag_6_config", 0))
        if n: tasks["摘抄"] = f"{int(bj.get('tag_6_cnt',0))}/{n}"
        # 报告
        n = int(bi.get("tag_5_config", 0))
        if n: tasks["报告"] = f"{int(bj.get('tag_5_cnt',0))}/{n}"
        # 讨论
        tn, cn = parse_discuss_req(d.get("task", {}).get("0", ""))
        if tn or cn: tasks["讨论"] = f"帖{int(bj.get('topic_cnt',0))}/{tn} 回{int(bj.get('comment_cnt',0))}/{cn}"
        if tasks:
            entries.append((bid, title, tasks))

    if not entries:
        print("没有待处理任务"); return

    # 选书
    print()
    for i, (bid, title, tasks) in enumerate(entries):
        tstr = "  ".join(f"{k}({v})" for k, v in tasks.items())
        print(f"  {i+1}. {title}")
        print(f"     {tstr}")
    print(f"  0. 退出")

    while True:
        s = input_str("\n选书: ")
        if s == "0": print("再见"); return
        try:
            idx = int(s) - 1
            if 0 <= idx < len(entries):
                bid, title, tasks = entries[idx]
                break
        except ValueError:
            pass
        print("无效")

    # 选任务
    tag_map = {"朗读": "3", "摘抄": "6", "报告": "5", "讨论": "0"}

    while True:
        # 刷新任务进度
        try:
            d = api.get_book_detail(bid)
        except Exception:
            d = {}
        bj = d.get("bookJoin", {})
        bi = d.get("book", {})
        tasks = {}
        n = int(bi.get("tag_3_config", 0))
        if n: tasks["朗读"] = f"{int(bj.get('tag_3_cnt',0))}/{n}"
        n = int(bi.get("tag_6_config", 0))
        if n: tasks["摘抄"] = f"{int(bj.get('tag_6_cnt',0))}/{n}"
        n = int(bi.get("tag_5_config", 0))
        if n: tasks["报告"] = f"{int(bj.get('tag_5_cnt',0))}/{n}"
        tn, cn = parse_discuss_req(d.get("task", {}).get("0", ""))
        if tn or cn: tasks["讨论"] = f"帖{int(bj.get('topic_cnt',0))}/{tn} 回{int(bj.get('comment_cnt',0))}/{cn}"

        tag_keys = list(tasks.keys())
        print(f"\n{title}")
        for i, name in enumerate(tag_keys):
            print(f"  {i+1}. {name} ({tasks[name]})")
        print(f"  0. 返回")

        while True:
            s = input_str("\n选任务: ")
            if s == "0": break
            try:
                idx = int(s) - 1
                if 0 <= idx < len(tag_keys):
                    name = tag_keys[idx]
                    break
            except ValueError:
                pass
            print("无效")

        if s == "0":
            break

        tag_id = tag_map.get(name)
        if not tag_id:
            print(f"未知任务: {name}")
            continue

        print(f"\n开始: {title} / {name}")
        print("-" * 40)

        try:
            api.auto_complete_tasks(bid, target_tag=tag_id)
        except Exception as e:
            print(f"出错: {e}")
            traceback.print_exc()

        print("\n处理完毕\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断")
