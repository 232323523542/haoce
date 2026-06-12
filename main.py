# -*- coding: utf-8 -*-
"""
好策(HaoCe) 阅读平台自动阅读脚本
交互式菜单 — 选书、选任务、实时进度
"""
import configparser
import io
import sys
import time
import traceback

# 修复 Windows 控制台 GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

from api.base import HaoceAPI, HaoceAccount
from api.llm import create_llm_client

TAG_NAMES = {"0": "讨论", "3": "朗读", "5": "报告", "6": "摘抄"}


def parse_discuss_requirement(task_desc: str) -> tuple:
    """从讨论任务描述中解析需求: (发帖数, 回复数)"""
    import re
    topics = replies = 0
    for pat in [r'发帖\s*(\d+)\s*次', r'发布\s*(\d+)\s*次\s*主题', r'(\d+)\s*次\s*主题帖']:
        m = re.search(pat, task_desc)
        if m:
            topics = int(m.group(1))
            break
    for pat in [r'回复\D*?(\d+)\s*次', r'回帖\D*?(\d+)\s*次']:
        m = re.search(pat, task_desc)
        if m:
            replies = int(m.group(1))
            break
    if topics == 0 or replies == 0:
        nums = [int(m.group(1)) for m in re.finditer(r'(\d+)\s*次', task_desc)]
        nums = [n for n in nums if n > 0]
        if len(nums) >= 2:
            topics = topics or min(nums)
            replies = replies or max(nums)
        elif len(nums) == 1 and replies == 0:
            replies = nums[0]
    return topics, replies


def load_config(config_path: str = "config.ini") -> dict:
    cfg = {
        "phone": "", "password": "",
        "duration_per_chapter": 120, "min_interval": 3.0,
        "skip_reading": False, "skip_tasks": False,
        "llm_backend": "ollama", "llm_model": "qwen2.5:7b",
        "llm_base_url": "http://localhost:11434/v1", "llm_api_key": "",
    }
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    if config.has_section("account"):
        cfg["phone"] = config.get("account", "phone", fallback="").strip()
        cfg["password"] = config.get("account", "password", fallback="").strip()
    if config.has_section("reading"):
        cfg["duration_per_chapter"] = config.getint("reading", "duration_per_chapter", fallback=120)
        cfg["min_interval"] = config.getfloat("reading", "min_interval", fallback=3.0)
        cfg["skip_reading"] = config.getboolean("reading", "skip_reading", fallback=False)
        cfg["skip_tasks"] = config.getboolean("reading", "skip_tasks", fallback=False)
    if config.has_section("llm"):
        cfg["llm_backend"] = config.get("llm", "backend", fallback="ollama").strip()
        cfg["llm_model"] = config.get("llm", "model", fallback="qwen2.5:7b").strip()
        cfg["llm_base_url"] = config.get("llm", "base_url", fallback="http://localhost:11434/v1").strip()
        cfg["llm_api_key"] = config.get("llm", "api_key", fallback="").strip()
    return cfg


def input_credential(prompt: str, default: str = "") -> str:
    """读取一行输入，去掉首尾空白"""
    try:
        val = input(prompt).strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def select_book(books: list[dict], api: HaoceAPI) -> dict | None:
    """显示书单，让用户选一本"""
    # 先获取每本书的详情和任务进度
    book_info_list = []
    print("正在获取书籍详情...")
    for b in books:
        bid = b["book_id"]
        merge = b.get("book_id_merge", {})
        title = merge.get("book", bid)

        try:
            detail = api.get_book_detail(bid)
        except Exception:
            book_info_list.append({"id": bid, "title": title, "tasks": {}, "error": True})
            continue

        book_info = detail.get("book", {})
        bj = detail.get("bookJoin", {})
        task_info = {}

        # 讨论 - 从任务描述解析真正的要求数（不是平台总计数）
        task_desc = detail.get("task", {}).get("0", "")
        topic_need, comment_need = parse_discuss_requirement(task_desc)
        topic_done = int(bj.get("topic_cnt", 0))
        comment_done = int(bj.get("comment_cnt", 0))
        if topic_need or comment_need:
            task_info["讨论"] = f"发帖{topic_done}/{topic_need} 回复{comment_done}/{comment_need}"

        # 朗读/报告/摘抄
        for tid, name in [("3", "朗读"), ("5", "报告"), ("6", "摘抄")]:
            need = int(book_info.get(f"tag_{tid}_config", 0))
            current = int(bj.get(f"tag_{tid}_cnt", 0))
            if need > 0:
                task_info[name] = f"{current}/{need}"

        book_info_list.append({"id": bid, "title": title, "tasks": task_info})

    print("\n书单:")
    for i, bi in enumerate(book_info_list):
        task_str = " | ".join(f"{k}:{v}" for k, v in bi["tasks"].items())
        expired = "该任务提交时间已截止" if "该任务提交时间已截止" in str(bi.get("error", "")) else ""
        note = f" [{expired}]" if expired else ""
        print(f"  [{i+1}] {bi['title']}{note}")
        if task_str:
            print(f"      {task_str}")

    print(f"  [0] 退出")
    print()

    while True:
        choice = input_credential("选书 (序号): ")
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(book_info_list):
                return book_info_list[idx]
        except ValueError:
            pass
        print("无效选项，请重试")


def select_tasks(book: dict) -> list[str] | None:
    """显示任务类型，支持多选。返回选中的 tag_id 列表"""
    tasks = book.get("tasks", {})
    if not tasks:
        print(f"\n  [{book['title']}] 没有待完成的任务")
        return None

    # 构建选项列表
    options = []
    tag_map = {}

    # 检查是否有未完成的朗读/报告/摘抄任务
    for tag_id, name in [("6", "摘抄"), ("5", "报告"), ("3", "朗读")]:
        key = f"{name}"
        if key in tasks:
            options.append(f"[{len(options)+1}] {name} ({tasks[key]})")
            tag_map[str(len(options))] = tag_id

    # 讨论
    if "讨论" in tasks:
        options.append(f"[{len(options)+1}] 讨论 ({tasks['讨论']})")
        tag_map[str(len(options))] = "0"

    if not options:
        print(f"\n  [{book['title']}] 所有任务已完成")
        return None

    print(f"\n任务类型 ({book['title']}):")
    for opt in options:
        print(f"  {opt}")
    print(f"  [a] 全部任务")
    print(f"  [0] 返回")

    while True:
        choice = input_credential("\n选任务 (多选用逗号分隔，如 1,2,3): ").lower()
        if choice == "0":
            return None
        if choice == "a":
            return list(tag_map.values())

        # 解析多选
        selected = []
        parts = [p.strip() for p in choice.replace("，", ",").split(",")]
        all_valid = True
        for p in parts:
            if p in tag_map:
                selected.append(tag_map[p])
            else:
                all_valid = False
        if all_valid and selected:
            return selected
        print("无效选项，请重试")


def main():
    cfg = load_config()

    print("=" * 50)
    print("好策阅读平台 - 自动阅读脚本")
    print("=" * 50)
    print()

    # Step 1: 询问账号
    phone = cfg["phone"]
    password = cfg["password"]
    if not phone:
        phone = input_credential("手机号: ")
    else:
        print(f"手机号: {phone}")
        print("密码: ****** (来自 config.ini)")
    if not password and not cfg["password"]:
        password = input_credential("密码: ")
    if not password:
        password = cfg["password"]

    if not phone or not password:
        print("手机号和密码不能为空")
        sys.exit(1)

    # Step 2: 初始化 LLM
    llm_client = create_llm_client(
        backend=cfg["llm_backend"], model=cfg["llm_model"],
        base_url=cfg["llm_base_url"], api_key=cfg["llm_api_key"],
    )
    if llm_client:
        print(f"LLM: {cfg['llm_backend']}/{cfg['llm_model']}")

    api = HaoceAPI(HaoceAccount(phone, password), llm_client=llm_client)

    # Step 3: 登录
    print("\n正在登录...")
    if not api.login():
        print("登录失败")
        sys.exit(1)

    user_info = api.get_user_info()
    print(f"用户: {user_info.get('name', '?')}  学校: {user_info.get('school', '?')}")

    # Step 4: 选书
    books = api.get_book_list()
    if not books:
        print("没有找到任何书籍")
        return

    while True:
        book = select_book(books, api)
        if book is None:
            print("再见!")
            break

        # Step 5: 选任务
        selected_tags = select_tasks(book)
        if selected_tags is None:
            continue

        print(f"\n开始处理: {book['title']}")
        print(f"任务类型: {', '.join(TAG_NAMES.get(t, t) for t in selected_tags)}")
        print("-" * 40)

        try:
            for tag in selected_tags:
                api.auto_complete_tasks(book["id"], target_tag=tag)
        except Exception as e:
            print(f"\n处理出错: {e}")
            traceback.print_exc()

        print(f"\n{'=' * 50}")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序异常: {e}")
        traceback.print_exc()
