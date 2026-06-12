# -*- coding: utf-8 -*-
"""
好策(HaoCe) 阅读平台自动阅读脚本
"""
import configparser
import io
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
    cfg = {"phone": "", "password": "", "skip_reading": False,
           "llm_backend": "ollama", "llm_model": "qwen2.5:7b",
           "llm_base_url": "http://localhost:11434/v1", "llm_api_key": ""}
    if c.has_section("account"):
        cfg["phone"] = c.get("account", "phone", fallback="").strip()
        cfg["password"] = c.get("account", "password", fallback="").strip()
    if c.has_section("reading"):
        cfg["skip_reading"] = c.getboolean("reading", "skip_reading", fallback=False)
    if c.has_section("llm"):
        cfg["llm_backend"] = c.get("llm", "backend", fallback="ollama").strip()
        cfg["llm_model"] = c.get("llm", "model", fallback="qwen2.5:7b").strip()
        cfg["llm_base_url"] = c.get("llm", "base_url", fallback="http://localhost:11434/v1").strip()
        cfg["llm_api_key"] = c.get("llm", "api_key", fallback="").strip()
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
    cfg = load_config()

    print("=" * 40)
    print("好策自动阅读")

    # 账号
    phone = cfg["phone"] or input_str("手机号: ")
    password = cfg["password"] or input_str("密码: ")
    if not phone or not password:
        print("手机号和密码不能为空"); sys.exit(1)

    # LLM
    llm = create_llm_client(backend=cfg["llm_backend"], model=cfg["llm_model"],
                            base_url=cfg["llm_base_url"], api_key=cfg["llm_api_key"])
    api = HaoceAPI(HaoceAccount(phone, password), llm_client=llm)

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
    tag_keys = list(tasks.keys())
    print(f"\n{title}")
    for i, name in enumerate(tag_keys):
        print(f"  {i+1}. {name} ({tasks[name]})")
    print(f"  0. 返回")

    while True:
        s = input_str("\n选任务: ")
        if s == "0": return
        try:
            idx = int(s) - 1
            if 0 <= idx < len(tag_keys):
                name = tag_keys[idx]
                break
        except ValueError:
            pass
        print("无效")

    # 映射
    tag_map = {"朗读": "3", "摘抄": "6", "报告": "5", "讨论": "0"}
    tag_id = tag_map.get(name)
    if not tag_id: print(f"未知任务: {name}"); return

    print(f"\n开始: {title} / {name}")
    print("-" * 40)

    try:
        api.auto_complete_tasks(bid, target_tag=tag_id)
    except Exception as e:
        print(f"出错: {e}")
        traceback.print_exc()

    print("\n处理完毕")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断")
