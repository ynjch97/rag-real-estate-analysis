import argparse

import uvicorn

from src.workflows.market_impact_workflow import analyze_market_impact


# API 서버 실행
def run_api(host: str, port: int) -> None:
    uvicorn.run("src.api.main:app", host=host, port=port)


# 터미널 대화형 분석 실행
def run_cli() -> None:
    print("RAG 기반 부동산 의사결정 시스템")
    print("종료하려면 exit 또는 quit 입력")

    while True:
        query = input("\n질문을 입력하세요: ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            print("질문을 입력하세요.")
            continue

        result = analyze_market_impact(query)
        print("\n" + result["answer"])


# 실행 옵션 파싱
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG 기반 부동산 의사결정 시스템 실행")
    parser.add_argument("--mode", choices=["api", "cli"], default="cli", help="실행 모드")
    parser.add_argument("--host", default="127.0.0.1", help="API 서버 host")
    parser.add_argument("--port", type=int, default=8000, help="API 서버 port")
    return parser.parse_args()


# 실행 모드에 따라 API 또는 CLI 시작
def main() -> None:
    args = parse_args()
    if args.mode == "api":
        run_api(args.host, args.port)
    else:
        run_cli()


if __name__ == "__main__":
    main()
