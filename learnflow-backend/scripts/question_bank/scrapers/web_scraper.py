"""多源网页爬虫 — 从公开题库网站抓取题目数据"""
import json
import os
import re
import time
import random
import requests
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
]


class BaseScraper:
    """爬虫基类"""

    def __init__(self, rate_limit: float = 1.0):
        self.session = requests.Session()
        self.rate_limit = rate_limit
        self.last_request = 0

    def _get(self, url: str, **kwargs) -> requests.Response:
        """限速 GET 请求"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed + random.uniform(0, 0.5))
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", random.choice(USER_AGENTS))
        resp = self.session.get(url, headers=headers, timeout=15, **kwargs)
        self.last_request = time.time()
        return resp

    def save(self, data: list, filename: str):
        os.makedirs(DATA_DIR, exist_ok=True)
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 保存 {len(data)} 条到 {filename}")


class Shijuan1Scraper(BaseScraper):
    """第一试卷网爬虫 (shijuan1.com)"""

    BASE = "https://www.shijuan1.com"

    def search_papers(self, keyword: str, page: int = 1) -> list[dict]:
        """搜索试卷列表"""
        url = f"{self.BASE}/search.asp"
        results = []
        try:
            resp = self._get(url, params={"keyword": keyword, "page": page})
            if resp.status_code != 200:
                print(f"  ⚠ 请求失败: {resp.status_code}")
                return results
            # 简单解析试卷链接
            pattern = r'<a[^>]*href="(/a/[^"]+)"[^>]*>([^<]+)</a>'
            for match in re.finditer(pattern, resp.text):
                results.append({"url": self.BASE + match.group(1), "title": match.group(2).strip()})
        except Exception as e:
            print(f"  ⚠ 搜索错误: {e}")
        return results

    def scrape_questions_from_paper(self, paper_url: str) -> list[dict]:
        """从试卷页面抓取题目"""
        questions = []
        try:
            resp = self._get(paper_url)
            if resp.status_code != 200:
                return questions
            # 尝试提取题目文本
            text = re.sub(r'<[^>]+>', '\n', resp.text)
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
            # 检测题目行（通常包含数字序号）
            for line in lines:
                if re.match(r'^\d+[\.、）\)]\s*.{3,}', line):
                    questions.append({"content": line, "topic": "未知", "answer": "", "source": "shijuan1"})
        except Exception as e:
            print(f"  ⚠ 抓取页面错误: {e}")
        return questions


class GithubDatasetScraper(BaseScraper):
    """GitHub 开源题库数据集下载器"""

    def fetch_raw_file(self, raw_url: str) -> Optional[str]:
        """下载原始数据文件"""
        try:
            resp = self._get(raw_url)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"  ⚠ 下载失败: {e}")
        return None

    def parse_csv_questions(self, text: str, topic_default: str = "数学") -> list[dict]:
        """解析CSV格式的题目数据"""
        questions = []
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return questions
        # 检测表头
        header = lines[0].lower()
        col_map = {}
        for col_name, keywords in [("content", ["题目", "question", "content", "题干"]),
                                     ("answer", ["答案", "answer", "正确答案"]),
                                     ("explanation", ["解析", "explanation", "分析"]),
                                     ("topic", ["知识点", "topic", "tag"])]:
            for i, h in enumerate(header.split(',')):
                h_clean = h.strip().strip('"').strip()
                if any(k in h_clean for k in keywords):
                    col_map[col_name] = i
                    break
        if "content" not in col_map:
            # 尝试把第一列当题目
            col_map["content"] = 0

        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) <= max(col_map.values(), default=0):
                continue
            q = {
                "content": parts[col_map.get("content", 0)].strip().strip('"'),
                "answer": parts[col_map.get("answer", -1)].strip().strip('"') if "answer" in col_map else "",
                "explanation": parts[col_map.get("explanation", -1)].strip().strip('"') if "explanation" in col_map else "",
                "topic": parts[col_map.get("topic", -1)].strip().strip('"') if "topic" in col_map else topic_default,
            }
            if len(q["content"]) > 3:
                questions.append(q)
        return questions

    def parse_json_questions(self, text: str) -> list[dict]:
        """解析JSON格式的题目"""
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # 常见 key: data, items, questions, results
                for key in ["data", "items", "questions", "results"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
        except json.JSONDecodeError:
            pass
        return []


def run_scrapers():
    """运行全部爬虫"""
    print("🔍 开始网页抓取...")

    # Shijuan1Scraper (可能需要)
    scraper = Shijuan1Scraper(rate_limit=2.0)
    papers = scraper.search_papers("小学数学")
    print(f"  shijuan1 搜索到 {len(papers)} 个试卷")

    # 统计
    all_scraped = []
    print(f"\n📊 爬取统计: 共 {len(all_scraped)} 道外部题目")
    return all_scraped


if __name__ == "__main__":
    run_scrapers()
