from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, Sources
from src.agents.controller import analyze_with_agent


app = FastAPI(title="RAG Real Estate Decision API")


# 채팅 화면 표시
@app.get("/", response_class=HTMLResponse)
def chat_page() -> str:
    return _build_chat_page()


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

    result = analyze_with_agent(query)
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
        agent_plan=result.get("agent_plan", {}),
    )


# 브라우저 채팅 화면 HTML 생성
def _build_chat_page() -> str:
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAG 부동산 분석</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f4ef;
      --panel: #ffffff;
      --text: #242424;
      --muted: #666666;
      --line: #d8d2c7;
      --accent: #0f6b5f;
      --accent-strong: #0a4f46;
      --danger: #a33b2f;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif;
    }

    main {
      width: min(960px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }

    header {
      margin-bottom: 18px;
    }

    h1 {
      margin: 0 0 6px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }

    .chat-shell {
      display: grid;
      gap: 14px;
    }

    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }

    input {
      width: 100%;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px 13px;
      color: var(--text);
      font-size: 15px;
      outline: none;
    }

    input:focus {
      border-color: var(--accent);
    }

    button {
      border: 0;
      border-radius: 6px;
      padding: 0 18px;
      background: var(--accent);
      color: #ffffff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover {
      background: var(--accent-strong);
    }

    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }

    .result-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .result-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }

    .panel-title {
      display: flex;
      align-items: center;
      min-height: 42px;
      border-bottom: 1px solid var(--line);
      padding: 0 14px;
      font-size: 14px;
      font-weight: 700;
      color: var(--accent-strong);
      background: #fbfaf7;
    }

    .output {
      min-height: 180px;
      max-height: 280px;
      overflow: auto;
      white-space: pre-wrap;
      padding: 16px;
      font-family: Consolas, "Malgun Gothic", monospace;
      font-size: 14px;
      line-height: 1.65;
    }

    .placeholder {
      color: var(--muted);
    }

    .error {
      color: var(--danger);
    }

    @media (max-width: 640px) {
      main {
        width: min(100vw - 20px, 960px);
        padding: 18px 0;
      }

      form {
        grid-template-columns: 1fr;
      }

      button {
        height: 44px;
      }

      .output {
        min-height: 180px;
        max-height: 320px;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>RAG 기반 부동산 의사결정 시스템</h1>
      <p class="subtitle">질문을 입력하고 Enter를 누르면 분석 결과가 아래 박스에 표시됩니다.</p>
    </header>

    <section class="chat-shell">
      <form id="chat-form">
        <input id="query-input" type="text" autocomplete="off" placeholder="예: 강서구 내년에 집값 어떨 것 같아?" />
        <button id="submit-button" type="submit">분석</button>
      </form>

      <div class="result-grid">
        <section class="result-panel">
          <div class="panel-title">1. 결론 요약</div>
          <div id="summary-output" class="output placeholder">아직 분석 결과가 없습니다.</div>
        </section>

        <section class="result-panel">
          <div class="panel-title">2. 질문 해석</div>
          <div id="question-output" class="output placeholder">아직 분석 결과가 없습니다.</div>
        </section>

        <section class="result-panel">
          <div class="panel-title">3. 근거 및 상세 분석</div>
          <div id="detail-output" class="output placeholder">아직 분석 결과가 없습니다.</div>
        </section>
      </div>
    </section>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const input = document.getElementById("query-input");
    const summaryOutput = document.getElementById("summary-output");
    const questionOutput = document.getElementById("question-output");
    const detailOutput = document.getElementById("detail-output");
    const button = document.getElementById("submit-button");
    const sectionTitles = [
      "질문 해석",
      "결론 요약",
      "정책 근거",
      "관련 뉴스 요약",
      "시세 변화 데이터",
      "정책과 시세의 관계 해석",
      "불확실성 및 추가 확인 필요 사항",
      "참고 출처"
    ];

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) {
        input.focus();
        return;
      }

      setLoading("분석 중입니다...");
      button.disabled = true;

      try {
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json; charset=utf-8"
          },
          body: JSON.stringify({ query })
        });

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || `HTTP ${response.status}`);
        }

        const data = await response.json();
        renderResult(data);
      } catch (error) {
        setError(`오류가 발생했습니다.\\n${error.message}`);
      } finally {
        button.disabled = false;
        input.focus();
      }
    });

    function renderResult(data) {
      const answer = data.answer || "";
      setPanelText(summaryOutput, extractSection(answer, "결론 요약") || "결론 요약이 없습니다.");
      setPanelText(questionOutput, buildQuestionBox(data, answer));
      setPanelText(detailOutput, buildDetailBox(answer));
    }

    function buildQuestionBox(data, answer) {
      const questionSection = extractSection(answer, "질문 해석") || "질문 해석이 없습니다.";
      const plan = data.agent_plan || {};
      const parsedQuery = data.parsed_query || {};
      const sources = data.sources || {};
      const marketSummary = data.market_summary || {};
      const taskType = plan.task_type || parsedQuery.task_type || "미확인";
      const retrievalSteps = Array.isArray(plan.retrieval_steps) ? plan.retrieval_steps.join(" → ") : "미확인";
      const reasoningStrategy = plan.reasoning_strategy || "미확인";
      const dataList = buildRetrievedDataList(sources, marketSummary);

      return [
        questionSection,
        "",
        "[Agent Controller]",
        `- 질문 유형 판단: ${taskType}`,
        `- 검색 순서 결정: ${retrievalSteps}`,
        `- 추론 전략: ${reasoningStrategy}`,
        "- 조회한 데이터 목록:",
        dataList
      ].join("\\n");
    }

    function buildRetrievedDataList(sources, marketSummary) {
      const policySources = Array.isArray(sources.policies) && sources.policies.length ? sources.policies.join(", ") : "없음";
      const newsSources = Array.isArray(sources.news) && sources.news.length ? sources.news.join(", ") : "없음";
      const priceSources = formatPriceDataList(marketSummary);

      return [
        `  - 정책: ${policySources}`,
        `  - 뉴스: ${newsSources}`,
        `  - 시세: ${priceSources}`
      ].join("\\n");
    }

    function formatPriceDataList(marketSummary) {
      if (Array.isArray(marketSummary.regions) && marketSummary.regions.length) {
        return marketSummary.regions
          .map((item) => `${item.region || "지역 미확인"} ${item.acc_year || ""}`.trim())
          .join(", ");
      }
      if (marketSummary.region || marketSummary.acc_year || marketSummary.policy_month) {
        return `${marketSummary.region || "지역 미확인"} ${marketSummary.acc_year || marketSummary.policy_month || ""}`.trim();
      }
      if (marketSummary.price_summary && marketSummary.price_summary.region) {
        return `${marketSummary.price_summary.region} ${marketSummary.price_summary.acc_year || ""}`.trim();
      }
      return "없음";
    }

    function buildDetailBox(answer) {
      const titles = [
        "정책 근거",
        "관련 뉴스 요약",
        "시세 변화 데이터",
        "정책과 시세의 관계 해석",
        "불확실성 및 추가 확인 필요 사항",
        "참고 출처"
      ];
      const sections = titles
        .map((title) => {
          const content = extractSection(answer, title);
          return content ? `[${title}]\\n${content}` : "";
        })
        .filter(Boolean);

      return sections.length ? sections.join("\\n\\n") : "상세 분석 내용이 없습니다.";
    }

    function extractSection(answer, title) {
      const startToken = `[${title}]`;
      const startIndex = answer.indexOf(startToken);
      if (startIndex < 0) {
        return "";
      }

      const contentStart = startIndex + startToken.length;
      const nextIndexes = sectionTitles
        .filter((sectionTitle) => sectionTitle !== title)
        .map((sectionTitle) => answer.indexOf(`[${sectionTitle}]`, contentStart))
        .filter((index) => index >= 0);
      const contentEnd = nextIndexes.length ? Math.min(...nextIndexes) : answer.length;
      return answer.slice(contentStart, contentEnd).trim();
    }

    function setPanelText(panel, text) {
      panel.className = "output";
      panel.textContent = text;
    }

    function setLoading(text) {
      [summaryOutput, questionOutput, detailOutput].forEach((panel) => {
        panel.className = "output placeholder";
        panel.textContent = text;
      });
    }

    function setError(text) {
      [summaryOutput, questionOutput, detailOutput].forEach((panel) => {
        panel.className = "output error";
        panel.textContent = text;
      });
    }
  </script>
</body>
</html>
"""
