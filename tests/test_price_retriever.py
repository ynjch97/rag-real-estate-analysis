from src.prices.price_retriever import retrieve_transactions


def test_retrieves_transactions_by_region():
    transactions = retrieve_transactions(region="성동구")

    assert len(transactions) == 12
    assert {transaction["sigungu"] for transaction in transactions} == {"성동구"}


def test_retrieves_transactions_by_date_range():
    transactions = retrieve_transactions(
        region="강남구",
        start_date="2024-03-01",
        end_date="2024-04-30",
    )

    assert [transaction["transaction_id"] for transaction in transactions] == ["tx_031", "tx_032"]


def test_retrieves_transactions_by_transaction_type():
    transactions = retrieve_transactions(region="광진구", transaction_type="전세")

    assert transactions == []


def test_retrieves_transactions_by_dong():
    transactions = retrieve_transactions(region="성동구", dong="성수동1가")

    assert transactions
    assert {transaction["sigungu"] for transaction in transactions} == {"성동구"}
    assert {transaction["dong"] for transaction in transactions} == {"성수동1가"}
