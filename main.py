# -*- coding: utf-8 -*-
"""
好策(HaoCe) 阅读平台自动阅读脚本
支持 novel 类型书籍的自动阅读（模拟翻页 + 上报阅读时长）
"""
import configparser
import sys
import time
import traceback

from api.base import HaoceAPI, HaoceAccount


def parse_config(config_path: str) -> dict:
    """解析配置文件"""
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    cfg = {
        "phone": "",
        "password": "",
        "duration_per_chapter": 120,
        "min_interval": 3.0,
        "book_list": None,
        "only_unfinished": True,
    }

    if config.has_section("account"):
        cfg["phone"] = config.get("account", "phone", fallback="").strip()
        cfg["password"] = config.get("account", "password", fallback="").strip()

    if config.has_section("reading"):
        cfg["duration_per_chapter"] = config.getint("reading", "duration_per_chapter", fallback=120)
        cfg["min_interval"] = config.getfloat("reading", "min_interval", fallback=3.0)
        book_list_str = config.get("reading", "book_list", fallback="").strip()
        if book_list_str:
            cfg["book_list"] = [b.strip() for b in book_list_str.split(",") if b.strip()]
        cfg["only_unfinished"] = config.getboolean("reading", "only_unfinished", fallback=True)

    return cfg


def main():
    """主程序入口"""
    config_path = "config.ini"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    cfg = parse_config(config_path)

    if not cfg["phone"] or not cfg["password"]:
        print("请先在 config.ini 中配置手机号和密码")
        sys.exit(1)

    print("=" * 50)
    print("好策阅读平台 - 自动阅读脚本")
    print("=" * 50)

    api = HaoceAPI(HaoceAccount(cfg["phone"], cfg["password"]))

    # 登录
    print("\n正在登录...")
    if not api.login():
        print("登录失败, 请检查账号密码")
        sys.exit(1)

    # 获取用户信息
    user_info = api.get_user_info()
    print(f"当前用户: {user_info.get('name', '?')} "
          f"(UID: {user_info.get('uid', '?')}) "
          f"学校: {user_info.get('school', '?')}")

    # 获取书单
    print("\n正在获取书单...")
    books = api.get_book_list()
    if not books:
        print("没有找到任何书籍")
        return

    print(f"共 {len(books)} 本书:")
    for book in books:
        merge = book.get("book_id_merge", {})
        title = merge.get("book", "未知")
        book_id = book["book_id"]
        finish = book.get("finish", "0")
        read_time = int(book.get("time", 0))
        status = "已完成" if finish == "1" else f"未完成 ({read_time}s)"
        print(f"  [{book_id}] {title} - {status}")

    # 过滤要阅读的书籍
    target_books = books
    if cfg["book_list"]:
        target_books = [
            b for b in books
            if b["book_id"] in cfg["book_list"]
        ]
        if not target_books:
            print(f"未找到指定的书籍 (筛选: {cfg['book_list']})")
            return

    if cfg["only_unfinished"]:
        target_books = [
            b for b in target_books
            if b.get("finish", "0") != "1"
        ]

    if not target_books:
        print("所有书已完成, 无需阅读")
        return

    print(f"\n待处理: {len(target_books)} 本")

    # 逐本处理
    for book in target_books:
        merge = book.get("book_id_merge", {})
        title = merge.get("book", "未知")

        try:
            # 先尝试 novel 模式
            detail = api.get_book_detail(book["book_id"])
            book_info = detail.get("book", {})
            isbn = book_info.get("isbn", {}) or {}
            novel_id = isbn.get("novel_id", 0)

            if novel_id and int(novel_id) > 0:
                api.simulate_reading(
                    book,
                    duration_per_chapter=cfg["duration_per_chapter"],
                    min_interval=cfg["min_interval"],
                )
            else:
                # PDF 模式
                pdf_file = book_info.get("book_pdf", "")
                if pdf_file:
                    print(f"\n[{title}] PDF 类型书籍")
                    print(f"  PDF: {pdf_file}")
                    print(f"  PDF 阅读进度上报 API 待进一步逆向研究")
                    print(f"  提示: PDF 书籍通过 apppdf.haoce.com 的 PDF.js 查看器阅读")
                else:
                    print(f"\n[{title}] 未知类型书籍, 跳过")

        except Exception as e:
            print(f"\n[{title}] 处理出错: {e}")
            traceback.print_exc()
            continue

        # 书与书之间的间隔
        time.sleep(3)

    print("\n" + "=" * 50)
    print("所有书籍处理完毕")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序异常: {e}")
        traceback.print_exc()
