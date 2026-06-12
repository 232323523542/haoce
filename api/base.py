# -*- coding: utf-8 -*-
"""
好策(HaoCe)阅读平台 API 封装
逆向工程自 haoce.com 移动端/Web端
"""
import hashlib
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass
class HaoceAccount:
    phone: str
    password: str


class HaoceSession:
    """会话管理"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    def json_request(self, url: str, data: dict = None) -> dict:
        """发送 JSON 格式的 API 请求"""
        headers = {
            "X-Display": "json",
            "LOGINUA": "PC",
        }
        if data:
            resp = self.session.post(url, headers=headers, data=data)
        else:
            resp = self.session.get(url, headers=headers)
        return resp.json()

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.session.post(url, **kwargs)


class HaoceAPI:
    """好策 API 封装"""

    BASE_URL = "https://www.haoce.com"

    def __init__(self, account: HaoceAccount):
        self.account = account
        self.http = HaoceSession()
        self.uid: Optional[str] = None
        self.name: Optional[str] = None
        self._rate_last = 0.0
        self._rate_min_interval = 1.0

    def rate_limit(self, min_interval: float = None):
        """请求频率控制"""
        if min_interval is None:
            min_interval = self._rate_min_interval
        elapsed = time.time() - self._rate_last
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed + random.uniform(0, 0.5))
        self._rate_last = time.time()

    def login(self) -> bool:
        """登录好策平台"""
        resp = self.http.session.post(
            f"{self.BASE_URL}/index/login/post",
            headers={"X-Display": "json", "LOGINUA": "PC"},
            data={"openid": self.account.phone, "psw": self.account.password},
        )
        result = resp.json()
        if result.get("error") != 0:
            print(f"登录失败: {result.get('error_des')} ({result.get('error')})")
            return False

        redirect_msg = result.get("redirect", {}).get("msg", "")
        print(f"登录成功: {redirect_msg}")
        return True

    def get_user_info(self) -> dict:
        """获取用户信息"""
        resp = self.http.json_request(f"{self.BASE_URL}/")
        data = resp.get("data", {})
        cu = data.get("_cu", {})
        self.uid = cu.get("uid", "")
        self.name = cu.get("name", "")
        return cu

    def get_book_list(self) -> list[dict]:
        """获取书单列表"""
        resp = self.http.json_request(f"{self.BASE_URL}/book/index")
        data = resp.get("data", {})
        return data.get("booksJoin", [])

    def get_book_detail(self, book_id: str) -> dict:
        """获取书籍详情（含 ISBN 信息、novel_id 等）"""
        resp = self.http.json_request(
            f"{self.BASE_URL}/app/bookOne/detail/{book_id}"
        )
        return resp.get("data", {})

    def get_novel_info(self, novel_id: str, book_id: str) -> dict:
        """
        获取小说( novel 类型) 的章节列表和签名盐值
        返回: {novel: {chapter: [...]}, mslad, mslad2}
        """
        resp = self.http.json_request(
            f"{self.BASE_URL}/book/novel/listV2?id={novel_id}&book_id={book_id}"
        )
        return resp.get("data", {})

    def get_chapter_content(self, cp_id: str, novel_name: str, book_id: str) -> dict:
        """获取章节内容"""
        resp = self.http.json_request(
            f"{self.BASE_URL}/book/novel/chapter/{cp_id}",
            data={"novel": novel_name, "book_id": book_id},
        )
        return resp.get("data", {})

    def get_view_data(self, novel_id: str) -> dict:
        """获取阅读进度数据 (每个章节的 dtime)"""
        resp = self.http.json_request(
            f"{self.BASE_URL}/book/novel/getView/{novel_id}"
        )
        return resp.get("data", {})

    def report_time(self, novel_id: str, book_id: str, seconds: int) -> dict:
        """
        上报阅读时长
        GET /book/novel/time/{novel_id}?time={seconds}&book_id={book_id}
        """
        resp = self.http.json_request(
            f"{self.BASE_URL}/book/novel/time/{novel_id}"
            f"?time={seconds}&book_id={book_id}"
        )
        return resp

    def do_view_v2(self, novel_id: str, book_id: str, cp_id: str,
                   page: int, page_count: int, mslad: str, mslad2: str,
                   start_time: str) -> dict:
        """
        上报章节阅读视图 (带 MD5 签名)
        模拟 readerFull 中的 doViewV2 逻辑
        """
        timestamp = str(int(time.time()))
        cp_view = {
            "book_id": book_id,
            "cp_id": cp_id,
            "novel_id": novel_id,
            "page": page,
            "page_count": page_count,
        }

        # 按 key 排序构建签名字符串
        md5_array = dict(cp_view)
        sorted_keys = sorted(md5_array.keys())
        sorted_str = "&".join(f"{k}={md5_array[k]}" for k in sorted_keys)

        # sigin = MD5(timestamp + MD5(sorted_str) + mslad)
        inner_md5 = hashlib.md5(sorted_str.encode()).hexdigest()
        sigin = hashlib.md5(
            (timestamp + inner_md5 + mslad).encode()
        ).hexdigest()

        cp_view["sigin"] = sigin
        cp_view["sigin2"] = sorted_str
        cp_view["sigin3"] = timestamp + sorted_str + mslad
        cp_view["timestamp"] = timestamp
        cp_view["timestamp2"] = mslad2
        cp_view["start_time"] = start_time

        resp = self.http.json_request(
            f"{self.BASE_URL}/book/novel/doViewV2",
            data=cp_view,
        )
        return resp

    def simulate_reading(self, book: dict, duration_per_chapter: int = 120,
                         min_interval: float = 3.0) -> bool:
        """
        模拟阅读一本 novel 类型的书

        Args:
            book: booksJoin 中的书籍条目
            duration_per_chapter: 每个章节模拟阅读的秒数
            min_interval: 请求之间的最小间隔（秒）
        """
        book_id = book["book_id"]
        title = book.get("book_id_merge", {}).get("book", book_id)

        # 获取书籍详情，检查是否为 novel 类型
        self.rate_limit(min_interval)
        detail = self.get_book_detail(book_id)
        book_info = detail.get("book", {})
        isbn = book_info.get("isbn", {}) or {}

        novel_id = isbn.get("novel_id", 0)
        if not novel_id or int(novel_id) <= 0:
            print(f"  [{title}] 不是 novel 类型书籍 (novel_id={novel_id}), 跳过")
            return False

        novel_id = str(novel_id)
        print(f"\n开始模拟阅读: {title} (novel_id={novel_id})")

        # 获取小说信息
        self.rate_limit(min_interval)
        novel_data = self.get_novel_info(novel_id, book_id)
        if not novel_data:
            print("  获取小说信息失败")
            return False

        novel = novel_data.get("novel", {})
        chapters = novel.get("chapter", [])
        mslad = novel_data.get("mslad", "")
        mslad2 = novel_data.get("mslad2", "")
        novel_name = novel.get("novel", "")

        print(f"  共 {len(chapters)} 章, mslad={mslad[:16]}...")

        # 获取当前进度
        self.rate_limit(min_interval)
        view_data = self.get_view_data(novel_id)
        vlist = view_data.get("vList", {})

        for i, ch in enumerate(chapters):
            cp_id = ch["cp_id"]
            chapter_title = ch.get("chapter", f"Chapter {i+1}")
            page_count = int(ch.get("word", 1000)) // 200 + 1  # 估算页数

            # 检查当前进度
            current_dtime = 0
            if cp_id in vlist:
                current_dtime = int(vlist[cp_id].get("dtime", 0))

            if current_dtime >= duration_per_chapter:
                print(f"  [{i+1}/{len(chapters)}] {chapter_title} - 已完成 ({current_dtime}s), 跳过")
                continue

            need_time = duration_per_chapter - current_dtime
            print(f"  [{i+1}/{len(chapters)}] {chapter_title} - "
                  f"当前进度 {current_dtime}s, 需要补充 {need_time}s")

            # 先加载章节内容
            self.rate_limit(min_interval)
            self.get_chapter_content(cp_id, novel_name, book_id)

            # 上报阅读时长
            self.rate_limit(min_interval)
            self.report_time(novel_id, book_id, duration_per_chapter)

            # 上报章节视图 (带签名)
            self.rate_limit(min_interval)
            self.do_view_v2(
                novel_id=novel_id,
                book_id=book_id,
                cp_id=cp_id,
                page=page_count,
                page_count=page_count,
                mslad=mslad,
                mslad2=mslad2,
                start_time=mslad2,
            )

            print(f"    已上报: time={duration_per_chapter}s, page={page_count}")

            # 模拟真实阅读间隔
            time.sleep(random.uniform(2, 5))

        print(f"  [{title}] 模拟阅读完成")
        return True

    def simulate_pdf_reading(self, book: dict, minutes: int = 30) -> bool:
        """
        模拟 PDF 类型书籍的阅读

        PDF 书籍通过 apppdf.haoce.com 的 PDF.js 查看器阅读。
        阅读进度追踪方式待进一步研究（可能通过 PDF viewer 回传页面数）。

        目前先尝试通过 /book/book 端点访问。
        """
        book_id = book["book_id"]
        title = book.get("book_id_merge", {}).get("book", book_id)

        detail = self.get_book_detail(book_id)
        book_info = detail.get("book", {})
        pdf_file = book_info.get("book_pdf", "")
        isbn = book_info.get("isbn", {}) or {}
        if not pdf_file:
            pdf_file = isbn.get("book_pdf", "")

        if not pdf_file:
            print(f"  [{title}] 没有 PDF 文件, 跳过")
            return False

        novel_id = isbn.get("novel_id", 0)
        if novel_id and int(novel_id) > 0:
            # 其实有 novel_id，用 novel 模式
            print(f"  [{title}] 有 novel_id={novel_id}, 使用 novel 模式")
            return self.simulate_reading(book, minutes * 60)

        print(f"  [{title}] PDF 类型书籍")
        print(f"    PDF: {pdf_file}")

        # PDF 书籍的阅读进度追踪机制待逆向
        # 可能需要通过 apppdf.haoce.com 的 viewer 上报
        print(f"    (PDF 阅读进度上报 API 待进一步研究)")
        return False
