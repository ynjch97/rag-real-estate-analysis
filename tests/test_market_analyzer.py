from src.prices.market_analyzer import calculate_monthly_metrics, summarize_before_after
from src.prices.price_retriever import retrieve_transactions


def test_calculates_monthly_metrics():
    transactions = retrieve_transactions(region="성동구", start_date="2024-01-01", end_date="2024-02-29")
    metrics = calculate_monthly_metrics(transactions)

    assert metrics == [
        {
            "month": "2024-01",
            "region": "성동구",
            "avg_price": 1410000000,
            "median_price": 1410000000,
            "price_per_m2": 16607774,
            "transaction_count": 1,
            "mom_change_rate": None,
        },
        {
            "month": "2024-02",
            "region": "성동구",
            "avg_price": 1320000000,
            "median_price": 1320000000,
            "price_per_m2": 22073579,
            "transaction_count": 1,
            "mom_change_rate": -6.38,
        },
    ]


def test_summarizes_before_after_policy_month():
    transactions = retrieve_transactions(region="강남구")
    metrics = calculate_monthly_metrics(transactions)
    summary = summarize_before_after(metrics, region="강남구", policy_month="2024-03")

    assert summary["region"] == "강남구"
    assert summary["policy_month"] == "2024-03"
    assert summary["before_month_count"] == 6
    assert summary["after_month_count"] == 6
    assert summary["before_avg_price"] == 2873333333
    assert summary["after_avg_price"] == 2978333333
    assert summary["price_change_rate"] == 3.65
