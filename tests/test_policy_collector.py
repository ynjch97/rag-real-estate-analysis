import json

from src.collectors.policy_collector import (
    build_korea_policy_news_list_url,
    extract_policy_news_links,
    fetch_korea_policy_news_raw,
    parse_korea_policy_news_detail,
    save_raw_policy_news,
)


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.text.encode("utf-8")


# 정책브리핑 정책뉴스 목록 URL 생성 검증
def test_builds_korea_policy_news_list_url():
    url = build_korea_policy_news_list_url(page=2)

    assert url == "https://www.korea.kr/news/policyNewsList.do?smenu=EDS01&pageIndex=2"


# 정책브리핑 정책뉴스 검색어 URL 생성 검증
def test_builds_korea_policy_news_list_url_with_search_keyword():
    url = build_korea_policy_news_list_url(page=1, search_keyword="부동산")

    assert url == "https://www.korea.kr/news/policyNewsList.do?smenu=EDS01&pageIndex=1&srchKeyword=%EB%B6%80%EB%8F%99%EC%82%B0"


# 정책브리핑 정책뉴스 상세 링크 추출 검증
def test_extracts_policy_news_links():
    html = """
    <a href="/news/policyNewsView.do?newsId=148964990">정책뉴스 A</a>
    <a href="https://www.korea.kr/news/policyNewsView.do?newsId=148964991">정책뉴스 B</a>
    <a href="/news/other.do?newsId=1">무시</a>
    """

    links = extract_policy_news_links(html)

    assert links == [
        "https://www.korea.kr/news/policyNewsView.do?newsId=148964990",
        "https://www.korea.kr/news/policyNewsView.do?newsId=148964991",
    ]


# 정책브리핑 정책뉴스 상세 HTML 파싱 검증
def test_parses_korea_policy_news_detail():
    html = """
    <html>
      <head><title>주택 공급 확대 - 정책뉴스</title></head>
      <body>
        <h1>주택 공급 확대 방안 발표</h1>
        <h2>국토교통부, 도심 공급 기반 강화</h2>
        <p>2026.05.22 국토교통부</p>
        <p>정부는 주택 공급과 재건축 제도 개선을 추진한다.</p>
      </body>
    </html>
    """

    row = parse_korea_policy_news_detail(html, "https://www.korea.kr/news/policyNewsView.do?newsId=1")

    assert row["title"] == "주택 공급 확대 방안 발표"
    assert row["subtitle"] == "국토교통부, 도심 공급 기반 강화"
    assert row["published_date"] == "2026-05-22"
    assert row["ministry"] == "국토교통부"
    assert "주택 공급" in row["content"]


# 정책브리핑 정책뉴스 원천 데이터 수집 검증
def test_fetches_korea_policy_news_raw_with_fake_opener():
    list_html = '<a href="/news/policyNewsView.do?newsId=148964990">정책뉴스 A</a>'
    detail_html = """
    <h1>대출 규제 개선</h1>
    <h2>금융위원회, 실수요자 부담 완화</h2>
    <p>2026.05.22 금융위원회</p>
    <p>대출 규제와 금융 지원 관련 정책을 발표했다.</p>
    """

    def fake_opener(request):
        if "policyNewsList.do" in request.full_url:
            return FakeResponse(list_html)
        return FakeResponse(detail_html)

    rows = fetch_korea_policy_news_raw(max_items=1, opener=fake_opener)

    assert len(rows) == 1
    assert rows[0]["title"] == "대출 규제 개선"
    assert rows[0]["ministry"] == "금융위원회"


# 정책브리핑 정책뉴스 관련 키워드 필터링 검증
def test_fetches_only_real_estate_policy_news_with_fake_opener():
    list_html = """
    <a href="/news/policyNewsView.do?newsId=148964990">정책뉴스 A</a>
    <a href="/news/policyNewsView.do?newsId=148964991">정책뉴스 B</a>
    """
    unrelated_detail_html = """
    <h1>디지털 교육 확대</h1>
    <h2>교육부, 학교 인프라 개선</h2>
    <p>2026.05.22 교육부</p>
    <p>AI 교과서와 학교 네트워크 개선을 추진한다.</p>
    """
    real_estate_detail_html = """
    <h1>주택 공급 확대</h1>
    <h2>국토교통부, 수도권 공급 기반 강화</h2>
    <p>2026.05.22 국토교통부</p>
    <p>정부는 부동산 시장 안정을 위해 주택 공급을 확대한다.</p>
    """

    def fake_opener(request):
        if "policyNewsList.do" in request.full_url:
            assert "srchKeyword=%EB%B6%80%EB%8F%99%EC%82%B0" in request.full_url
            return FakeResponse(list_html)
        if "148964990" in request.full_url:
            return FakeResponse(unrelated_detail_html)
        return FakeResponse(real_estate_detail_html)

    rows = fetch_korea_policy_news_raw(max_items=2, search_keyword="부동산", opener=fake_opener)

    assert len(rows) == 1
    assert rows[0]["title"] == "주택 공급 확대"


# 정책브리핑 공통 본문 키워드 오탐 제외 검증
def test_excludes_unrelated_policy_news_even_if_body_has_real_estate_menu_text():
    list_html = '<a href="/news/policyNewsView.do?newsId=148964990">정책뉴스 A</a>'
    detail_html = """
    <h1>공정거래 위반 신고포상금 확대</h1>
    <h2>공정거래위원회, 신고 제도 개선</h2>
    <p>2026.06.17 공정거래위원회</p>
    <p>사이트 이동경로 정책뉴스 국토교통부 부동산 주택 아파트 뉴스 목록</p>
    """

    def fake_opener(request):
        if "policyNewsList.do" in request.full_url:
            return FakeResponse(list_html)
        return FakeResponse(detail_html)

    rows = fetch_korea_policy_news_raw(max_items=1, search_keyword="부동산", opener=fake_opener)

    assert rows == []


# 정책브리핑 원천 데이터 JSONL 저장 검증
def test_saves_raw_policy_news(tmp_path):
    output_path = tmp_path / "policy_news.jsonl"
    save_raw_policy_news(output_path, [{"title": "정책뉴스"}])

    assert output_path.read_text(encoding="utf-8").strip() == json.dumps({"title": "정책뉴스"}, ensure_ascii=False)
