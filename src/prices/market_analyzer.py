from collections import defaultdict
from statistics import mean, median
from typing import Any


# 거래 목록을 월별/지역별로 묶어서 평균가, 중위값, ㎡당 가격, 거래 건수, 전월 대비 변화율을 계산
def calculate_monthly_metrics(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped_transactions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for transaction in transactions:
        month = transaction["contract_date"][:7]
        region = transaction["sigungu"]
        grouped_transactions[(month, region)].append(transaction)

    previous_avg_price_by_region: dict[str, float] = {}
    metrics: list[dict[str, Any]] = []

    for month, region in sorted(grouped_transactions):
        monthly_transactions = grouped_transactions[(month, region)]
        prices = [float(transaction["price"]) for transaction in monthly_transactions]
        price_per_m2_values = [
            float(transaction["price"]) / float(transaction["area_m2"])
            for transaction in monthly_transactions
            if float(transaction["area_m2"]) > 0
        ]

        avg_price = mean(prices)
        previous_avg_price = previous_avg_price_by_region.get(region)
        mom_change_rate = _calculate_change_rate(avg_price, previous_avg_price)
        previous_avg_price_by_region[region] = avg_price

        metrics.append(
            {
                "month": month,
                "region": region,
                "avg_price": round(avg_price),
                "median_price": round(median(prices)),
                "price_per_m2": round(mean(price_per_m2_values)),
                "transaction_count": len(monthly_transactions),
                "mom_change_rate": mom_change_rate,
            }
        )

    return metrics


# 정책 기준 월을 중심으로 전후 기간의 평균 가격과 거래량 변화를 요약
def summarize_before_after(
    monthly_metrics: list[dict[str, Any]],
    region: str,
    policy_month: str,
    months_before: int = 6,
    months_after: int = 6,
) -> dict[str, float | int | None]:
    region_metrics = [metric for metric in monthly_metrics if metric["region"] == region]
    before = [metric for metric in region_metrics if metric["month"] < policy_month][-months_before:]
    after = [metric for metric in region_metrics if metric["month"] >= policy_month][:months_after]

    before_prices = [float(metric["avg_price"]) for metric in before]
    after_prices = [float(metric["avg_price"]) for metric in after]
    before_counts = [int(metric["transaction_count"]) for metric in before]
    after_counts = [int(metric["transaction_count"]) for metric in after]

    before_avg_price = _safe_mean(before_prices)
    after_avg_price = _safe_mean(after_prices)
    before_avg_count = _safe_mean(before_counts)
    after_avg_count = _safe_mean(after_counts)

    return {
        "region": region,
        "policy_month": policy_month,
        "before_month_count": len(before),
        "after_month_count": len(after),
        "before_avg_price": _round_optional(before_avg_price),
        "after_avg_price": _round_optional(after_avg_price),
        "price_change_rate": _calculate_change_rate(after_avg_price, before_avg_price),
        "before_avg_transaction_count": _round_optional(before_avg_count),
        "after_avg_transaction_count": _round_optional(after_avg_count),
        "transaction_count_change_rate": _calculate_change_rate(after_avg_count, before_avg_count),
    }


# 이전 값 대비 현재 값의 변화율을 퍼센트로 계산
def _calculate_change_rate(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


# 값 목록이 비어 있으면 None, 값이 있으면 평균을 반환
def _safe_mean(values: list[float] | list[int]) -> float | None:
    if not values:
        return None
    return mean(values)


# None은 그대로 두고, 숫자 값만 반올림해서 정수로 변환
def _round_optional(value: float | None) -> int | None:
    if value is None:
        return None
    return round(value)
