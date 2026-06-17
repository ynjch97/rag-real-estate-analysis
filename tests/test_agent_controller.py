from src.agents.controller import analyze_with_agent
from src.agents.controller import _build_region_year_summary
from src.agents.task_planner import (
    TASK_FORECAST,
    TASK_POLICY_IMPACT,
    TASK_PRICE_CAUSE,
    TASK_REGION_COMPARISON,
    plan_agent_task,
)


# 정책 영향 분석 질문 계획 검증
def test_plans_policy_impact_task():
    plan = plan_agent_task("이번 금리 인상으로 영등포구 집값에 미친 영향")

    assert plan.task_type == TASK_POLICY_IMPACT
    assert plan.parsed_query["region"] == "영등포구"
    assert plan.parsed_query["policy_type"] == "interest_rate"
    assert plan.retrieval_steps == ["policy", "news", "price"]


# 지역 비교 질문 계획 검증
def test_plans_region_comparison_task():
    plan = plan_agent_task("올해 마포구와 은평구 중 어디 집값이 더 올랐어?")

    assert plan.task_type == TASK_REGION_COMPARISON
    assert plan.regions == ["마포구", "은평구"]
    assert plan.retrieval_steps == ["price", "news"]


# 가격 상승 원인 질문 계획 검증
def test_plans_price_cause_task():
    plan = plan_agent_task("올해 강남구 집값 왜 올랐어?")

    assert plan.task_type == TASK_PRICE_CAUSE
    assert plan.regions == ["강남구"]
    assert plan.retrieval_steps == ["policy", "news", "price"]


# 전망 질문 계획 검증
def test_plans_forecast_task():
    plan = plan_agent_task("강서구 내년에 집값 어떨 것 같아?")

    assert plan.task_type == TASK_FORECAST
    assert plan.regions == ["강서구"]
    assert plan.retrieval_steps == ["price", "news", "policy"]


# 정책 영향 분석 workflow 라우팅 검증
def test_agent_routes_policy_impact_task(monkeypatch):
    def fake_analyze_market_impact(query):
        return {
            "answer": "ok",
            "parsed_query": {"query": query},
            "policies": [],
            "news": [],
            "monthly_metrics": [],
            "market_summary": {},
            "context": "",
        }

    monkeypatch.setattr("src.agents.controller.analyze_market_impact", fake_analyze_market_impact)

    result = analyze_with_agent("이번 금리 인상으로 영등포구 집값에 미친 영향")

    assert result["answer"] == "ok"
    assert result["agent_plan"]["task_type"] == TASK_POLICY_IMPACT
    assert result["parsed_query"]["task_type"] == TASK_POLICY_IMPACT


# 전망 질문 최근 가용 연도 fallback 검증
def test_agent_forecast_uses_latest_available_year(monkeypatch):
    def fake_retrieve_or_collect_transactions(region, acc_year, dong=None, transaction_type=None):
        if acc_year == 2025:
            return [
                {
                    "transaction_id": "tx_001",
                    "region_code": "11500",
                    "sido": "서울",
                    "sigungu": "강서구",
                    "dong": "화곡동",
                    "apartment_name": "테스트",
                    "contract_date": "2025-01-01",
                    "price": 500000000,
                    "area_m2": 50.0,
                    "floor": 5,
                    "built_year": 2010,
                    "transaction_type": "매매",
                },
                {
                    "transaction_id": "tx_002",
                    "region_code": "11500",
                    "sido": "서울",
                    "sigungu": "강서구",
                    "dong": "화곡동",
                    "apartment_name": "테스트",
                    "contract_date": "2025-12-01",
                    "price": 550000000,
                    "area_m2": 50.0,
                    "floor": 6,
                    "built_year": 2010,
                    "transaction_type": "매매",
                },
            ]
        return []

    monkeypatch.setattr("src.agents.controller.retrieve_or_collect_transactions", fake_retrieve_or_collect_transactions)
    monkeypatch.setattr("src.agents.controller.retrieve_news_documents", lambda parsed_query, query=None: [])
    monkeypatch.setattr("src.agents.controller.retrieve_policy_documents", lambda parsed_query, query=None: [])

    result = analyze_with_agent("강서구 내년에 집값 어떨 것 같아?")

    assert result["parsed_query"]["task_type"] == TASK_FORECAST
    assert result["market_summary"]["base_year"] == 2025
    assert result["market_summary"]["price_summary"]["price_change_rate"] == 10.0


# 연간 변화율은 초반/후반 ㎡당 가격 기준으로 계산 검증
def test_build_region_year_summary_uses_price_per_m2_windows(monkeypatch):
    transactions = []
    for month, price_per_m2 in (
        ("01", 10_000_000),
        ("02", 11_000_000),
        ("03", 12_000_000),
        ("10", 13_000_000),
        ("11", 14_000_000),
        ("12", 15_000_000),
    ):
        for index in range(2):
            transactions.append(
                {
                    "transaction_id": f"tx_{month}_{index}",
                    "region_code": "11680",
                    "sido": "서울",
                    "sigungu": "강남구",
                    "dong": "대치동",
                    "apartment_name": "테스트",
                    "contract_date": f"2026-{month}-01",
                    "price": price_per_m2 * 50,
                    "area_m2": 50.0,
                    "floor": 5,
                    "built_year": 2010,
                    "transaction_type": "매매",
                }
            )

    monkeypatch.setattr("src.agents.controller.retrieve_or_collect_transactions", lambda **kwargs: transactions)

    summary = _build_region_year_summary("강남구", 2026, {"transaction_type": "sale", "region": "강남구"})

    assert summary["comparison_basis"] == "초반 3개월 평균 ㎡당 가격 대비 후반 3개월 평균 ㎡당 가격"
    assert summary["price_change_rate"] == 27.27
