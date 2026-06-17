from src.analysis.answer_generator import generate_market_impact_answer


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    # LLM 호출 결과 반환
    def invoke(self, messages):
        return FakeResponse(
            "\n".join(
                [
                    "[질문 해석]",
                    "- 지역/기간: 성동구 / 전 6개월, 후 6개월",
                    "",
                    "[결론 요약]",
                    "- LLM 생성 답변",
                    "",
                    "[정책 근거]",
                    "- 정책 근거",
                    "",
                    "[관련 뉴스 요약]",
                    "- 뉴스 요약",
                    "",
                    "[시세 변화 데이터]",
                    "- 시세 데이터",
                    "",
                    "[정책과 시세의 관계 해석]",
                    "- 관계 해석",
                    "",
                    "[불확실성 및 추가 확인 필요 사항]",
                    "- 추가 확인 필요",
                    "",
                    "[참고 출처]",
                    "- 참고 출처",
                ]
            )
        )


# OpenAI 키가 있으면 LLM 답변을 우선 사용
def test_generate_market_impact_answer_uses_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("src.analysis.answer_generator.ChatOpenAI", FakeChatOpenAI)

    answer = generate_market_impact_answer(
        parsed_query={"region": "성동구", "months_before": 6, "months_after": 6},
        policies=[],
        news_items=[],
        market_summary={},
        context="[질문 해석]\n- 테스트",
    )

    assert "LLM 생성 답변" in answer
    assert "[결론 요약]" in answer


# OpenAI 키가 없으면 템플릿 답변 사용
def test_generate_market_impact_answer_falls_back_without_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    answer = generate_market_impact_answer(
        parsed_query={"region": "성동구", "months_before": 6, "months_after": 6},
        policies=[],
        news_items=[],
        market_summary={},
        context="[질문 해석]\n- 테스트",
    )

    assert "[결론 요약]" in answer
    assert "성동구" in answer
