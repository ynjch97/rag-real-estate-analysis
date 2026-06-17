import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen


KOREA_POLICY_NEWS_LIST_URL = "https://www.korea.kr/news/policyNewsList.do?smenu=EDS01"
KOREA_POLICY_BASE_URL = "https://www.korea.kr"


# 정책브리핑 정책뉴스 목록 URL 생성
def build_korea_policy_news_list_url(page: int = 1, base_url: str = KOREA_POLICY_NEWS_LIST_URL) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}pageIndex={page}"


# 정책브리핑 정책뉴스 원천 데이터 수집
def fetch_korea_policy_news_raw(
    page: int = 1,
    max_items: int = 10,
    opener: Callable[[Request], Any] = urlopen,
) -> list[dict[str, Any]]:
    list_url = build_korea_policy_news_list_url(page=page)
    list_html = _fetch_html(list_url, opener=opener)
    article_urls = extract_policy_news_links(list_html, base_url=KOREA_POLICY_BASE_URL)[:max_items]
    rows: list[dict[str, Any]] = []

    for article_url in article_urls:
        detail_html = _fetch_html(article_url, opener=opener)
        rows.append(parse_korea_policy_news_detail(detail_html, article_url))

    return rows


# 정책브리핑 정책뉴스 상세 링크 추출
def extract_policy_news_links(html_text: str, base_url: str = KOREA_POLICY_BASE_URL) -> list[str]:
    parser = _PolicyNewsLinkParser()
    parser.feed(html_text)

    links = []
    for href in parser.links:
        if "policyNewsView.do" not in href or "newsId=" not in href:
            continue
        links.append(urljoin(base_url, href))

    return list(dict.fromkeys(links))


# 정책브리핑 정책뉴스 상세 HTML 파싱
def parse_korea_policy_news_detail(html_text: str, url: str) -> dict[str, Any]:
    text = _html_to_text(html_text)
    title = _extract_heading(html_text, "h1") or _extract_title_tag(html_text)
    subtitle = _extract_heading(html_text, "h2")
    published_date = _extract_published_date(text)
    ministry = _extract_ministry(text, published_date)
    content = _extract_content_text(text, title)

    return {
        "url": url,
        "title": title,
        "subtitle": subtitle,
        "published_date": published_date,
        "ministry": ministry,
        "content": content,
    }


# 정책브리핑 원천 데이터 JSONL 저장
def save_raw_policy_news(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# URL HTML 조회
def _fetch_html(url: str, opener: Callable[[Request], Any] = urlopen) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with opener(request) as response:
        raw = response.read()

    return raw.decode("utf-8", errors="replace")


# HTML 제목 태그 추출
def _extract_heading(html_text: str, tag_name: str) -> str | None:
    pattern = rf"<{tag_name}[^>]*>(.*?)</{tag_name}>"
    match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    return _clean_text(match.group(1))


# HTML title 태그 추출
def _extract_title_tag(html_text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    title = _clean_text(match.group(1))
    return title.split("|")[0].split("-")[0].strip() or None


# 본문 텍스트에서 발행일 추출
def _extract_published_date(text: str) -> str | None:
    match = re.search(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if match is None:
        return None
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


# 발행일 주변 텍스트에서 부처명 추출
def _extract_ministry(text: str, published_date: str | None) -> str | None:
    if published_date is None:
        return None

    dotted_date = published_date.replace("-", ".")
    index = text.find(dotted_date)
    if index < 0:
        return None

    nearby_text = text[index:index + 80]
    match = re.search(r"(국토교통부|기획재정부|금융위원회|한국은행|교육부|행정안전부|국무조정실|보건복지부|고용노동부|산업통상부)", nearby_text)
    if match is None:
        return None
    return match.group(1)


# 본문 텍스트 추출
def _extract_content_text(text: str, title: str | None) -> str:
    if title and title in text:
        text = text[text.find(title) + len(title):]

    blocked_markers = ("본문듣기", "글자크기", "인쇄하기", "목록")
    for marker in blocked_markers:
        text = text.replace(marker, " ")

    return re.sub(r"\s+", " ", text).strip()


# HTML을 일반 텍스트로 변환
def _html_to_text(html_text: str) -> str:
    without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    return _clean_text(without_tags)


# HTML 태그와 엔티티 제거
def _clean_text(value: Any) -> str:
    unescaped = html.unescape(str(value or ""))
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


class _PolicyNewsLinkParser(HTMLParser):
    # 정책뉴스 링크 수집
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    # a 태그 href 수집
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.links.append(href)
