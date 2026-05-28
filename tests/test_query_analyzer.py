from src.retrieval.query_analyzer import analyze_query


def test_extracts_policy_impact_query_for_interest_rate_and_region():
    parsed = analyze_query("이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘")

    assert parsed.region == "성동구"
    assert parsed.event_keyword == "금리 인상"
    assert parsed.policy_type == "interest_rate"
    assert parsed.intent == "policy_impact"
    assert parsed.property_type == "apartment"
    assert parsed.transaction_type == "sale"
    assert parsed.months_before == 6
    assert parsed.months_after == 6


def test_extracts_loan_regulation_for_dsr_query():
    parsed = analyze_query("DSR 대출 규제가 강남구 매매 시장에 어떤 영향을 줬어?")

    assert parsed.region == "강남구"
    assert parsed.event_keyword == "대출 규제"
    assert parsed.policy_type == "loan_regulation"
    assert parsed.intent == "policy_impact"


def test_extracts_supply_policy_for_reconstruction_query():
    parsed = analyze_query("광진구 재건축 공급 정책 이후 아파트 가격 변화 분석")

    assert parsed.region == "광진구"
    assert parsed.event_keyword == "공급 정책"
    assert parsed.policy_type == "supply_policy"
    assert parsed.intent == "policy_impact"


def test_uses_defaults_when_region_or_policy_is_missing():
    parsed = analyze_query("서울 아파트 시장 분위기 알려줘")

    assert parsed.region is None
    assert parsed.event_keyword is None
    assert parsed.policy_type is None
    assert parsed.intent == "general_search"
    assert parsed.property_type == "apartment"
    assert parsed.transaction_type == "sale"


def test_returns_dict_for_workflow_inputs():
    parsed = analyze_query("성동구 전세 시장에 금리가 미친 영향").to_dict()

    assert parsed["region"] == "성동구"
    assert parsed["transaction_type"] == "jeonse"
    assert parsed["months_before"] == 6
