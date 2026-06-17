from src.preprocessing.news_cleaner import normalize_naver_news_items


# 네이버 뉴스 응답을 README 4-2 구조로 정규화 검증
def test_normalizes_naver_news_items():
    raw_items = [
        {
            "title": "금리 <b>인상</b> 이후 동작구 아파트 매수세 둔화",
            "originallink": "https://example.com/news/1",
            "link": "https://n.news.naver.com/article/001/0000000001",
            "description": "동작구 아파트 <b>매매</b> 시장에서 관망세가 나타났다.",
            "pubDate": "Mon, 01 Jan 2024 09:00:00 +0900",
        }
    ]
    parsed_query = {
        "region": "동작구",
        "dong": None,
        "policy_type": "interest_rate",
    }

    news_items = normalize_naver_news_items(raw_items, parsed_query=parsed_query)

    assert len(news_items) == 1
    assert news_items[0]["title"] == "금리 인상 이후 동작구 아파트 매수세 둔화"
    assert news_items[0]["url"] == "https://example.com/news/1"
    assert news_items[0]["published_date"] == "2024-01-01"
    assert news_items[0]["news_site"] == "example.com"
    assert news_items[0]["region_tags"] == ["동작구"]
    assert news_items[0]["policy_tags"] == ["interest_rate"]
    assert news_items[0]["market_signal"] == "거래 위축"
    assert news_items[0]["summary"] == "동작구 아파트 매매 시장에서 관망세가 나타났다."


# 네이버 뉴스 중복 URL 제거 검증
def test_removes_duplicate_naver_news_items():
    raw_items = [
        {
            "title": "뉴스 1",
            "originallink": "https://example.com/news/1",
            "description": "내용",
            "pubDate": "Mon, 01 Jan 2024 09:00:00 +0900",
        },
        {
            "title": "뉴스 1 중복",
            "originallink": "https://example.com/news/1",
            "description": "내용",
            "pubDate": "Mon, 01 Jan 2024 09:00:00 +0900",
        },
    ]

    news_items = normalize_naver_news_items(raw_items)

    assert len(news_items) == 1
