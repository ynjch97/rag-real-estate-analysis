from src.preprocessing.policy_cleaner import normalize_ecos_interest_rate_items, normalize_korea_policy_news_items


# ECOS 금리 통계 항목을 정책 구조로 정규화 검증
def test_normalizes_ecos_interest_rate_items():
    raw_items = [
        {
            "STAT_CODE": "121Y006",
            "STAT_NAME": "예금은행 대출금리(신규취급액 기준)",
            "ITEM_CODE": "BECBLA02",
            "ITEM_NAME": "가계대출",
            "START_TIME": "200301",
            "END_TIME": "202505",
            "UNIT_NAME": "연%",
        }
    ]

    policies = normalize_ecos_interest_rate_items(raw_items)

    assert len(policies) == 1
    assert policies[0]["policy_id"] == "ecos_121Y006_BECBLA02"
    assert policies[0]["title"] == "예금은행 대출금리(신규취급액 기준) - 가계대출"
    assert policies[0]["published_date"] == "2025-05"
    assert policies[0]["effective_date"] == "2025-05"
    assert policies[0]["policy_type"] == "interest_rate"
    assert policies[0]["region_tags"] == ["전국"]
    assert "금리" in policies[0]["keywords"]
    assert policies[0]["source"] == "ECOS"


# 정책브리핑 정책뉴스를 정책 구조로 정규화 검증
def test_normalizes_korea_policy_news_items():
    raw_items = [
        {
            "url": "https://www.korea.kr/news/policyNewsView.do?newsId=1",
            "title": "주택 공급 확대 방안 발표",
            "subtitle": "국토교통부, 도심 공급 기반 강화",
            "published_date": "2026-05-22",
            "ministry": "국토교통부",
            "content": "정부는 주택 공급과 재건축 제도 개선을 추진한다.",
        }
    ]

    policies = normalize_korea_policy_news_items(raw_items)

    assert len(policies) == 1
    assert policies[0]["policy_id"].startswith("korea_policy_")
    assert policies[0]["title"] == "주택 공급 확대 방안 발표"
    assert policies[0]["published_date"] == "2026-05-22"
    assert policies[0]["effective_date"] == "2026-05-22"
    assert policies[0]["policy_type"] == "supply_policy"
    assert "주택" in policies[0]["keywords"]
    assert policies[0]["source"] == "KoreaPolicyBriefing"
    assert policies[0]["ministry"] == "국토교통부"
