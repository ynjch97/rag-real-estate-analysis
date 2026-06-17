from src.preprocessing.policy_cleaner import normalize_ecos_interest_rate_items


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
