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

    .output {
      min-height: 520px;
      max-height: calc(100vh - 190px);
      overflow: auto;
      white-space: pre-wrap;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
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
        min-height: 460px;
        max-height: none;
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

      <div id="output" class="output placeholder">아직 분석 결과가 없습니다.</div>
    </section>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const input = document.getElementById("query-input");
    const output = document.getElementById("output");
    const button = document.getElementById("submit-button");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) {
        input.focus();
        return;
      }

      output.className = "output";
      output.textContent = "분석 중입니다...";
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
        output.textContent = data.answer || "응답 내용이 없습니다.";
      } catch (error) {
        output.className = "output error";
        output.textContent = `오류가 발생했습니다.\\n${error.message}`;
      } finally {
        button.disabled = false;
        input.focus();
      }
    });
  </script>
</body>
</html>
"""
