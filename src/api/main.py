from typing import Any

from fastapi import FastAPI, HTTPException

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, Sources
from src.workflows.market_impact_workflow import analyze_market_impact


app = FastAPI(title="RAG Real Estate Decision API")


# 서버 상태 확인
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


# 부동산 시장 영향 분석 요청 처리
@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be blank")

    result = analyze_market_impact(query)
    return _to_analyze_response(result)


# workflow 결과를 API 응답 모델로 변환
def _to_analyze_response(result: dict[str, Any]) -> AnalyzeResponse:
    return AnalyzeResponse(
        answer=result["answer"],
        parsed_query=result["parsed_query"],
        market_summary=result["market_summary"],
        sources=Sources(
            policies=[policy["policy_id"] for policy in result["policies"]],
            news=[news["news_id"] for news in result["news"]],
        ),
        context=result["context"],
    )
