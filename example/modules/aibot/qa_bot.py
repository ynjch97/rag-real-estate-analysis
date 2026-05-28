"""
qa_system.py - RAG 기반 질의응답 시스템
"""

import os
import asyncio
import json
import time
import threading
from typing import Dict, List, Optional, AsyncGenerator, Any
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import secrets

from search_info import MultiAgentQASystem
from config_utils import ConfigManager

# 설정 로드
print("⚡️ 설정을 로드하는 중...")
config = ConfigManager()

# QA 시스템 클래스 정의
class QASystemManager:
    """질의응답 시스템 관리 클래스"""
    
    def __init__(self, prompt_type="general", use_rag=True):
        """
        질의응답 시스템 초기화
        
        Args:
            prompt_type: 사용할 프롬프트 유형 (기본값: "general")
            use_rag: RAG 사용 여부 (기본값: True)
        """
        print("🤖 AI 시스템을 초기화하는 중...")
        start_time = time.time()
        
        # QA 시스템 초기화
        self.qa_system = MultiAgentQASystem(prompt_type=prompt_type, use_rag=use_rag)
        
        # 대화 컨텍스트 저장소 (세션 ID를 키로 사용)
        self.conversation_contexts = {}
        
        print(f"✅ AI 시스템 초기화 완료! (소요시간: {time.time() - start_time:.2f}초)")
    
    def generate_session_id(self) -> str:
        """세션 ID 생성 함수"""
        return secrets.token_hex(8)

    async def process_question(self, text: str, session_id: Optional[str] = None) -> Dict:
        """
        질문을 처리하고 응답을 반환하는 함수
        
        Args:
            text: 사용자 질문
            session_id: 세션 ID (대화 컨텍스트를 위한 고유 식별자)
            
        Returns:
            Dict: 응답 결과를 포함한 딕셔너리
        """
        try:
            # 세션 ID가 있는 경우 이전 대화 컨텍스트 가져오기
            previous_context = self.conversation_contexts.get(session_id) if session_id else None
            
            # 질문 처리
            qa_result = await self.qa_system.process_question(text, context=previous_context)
            
            # 대화 컨텍스트 업데이트 (세션 ID가 있는 경우에만)
            if session_id:
                if session_id not in self.conversation_contexts:
                    self.conversation_contexts[session_id] = {}
                
                # 현재 시간 기록
                current_time = time.time()
                
                self.conversation_contexts[session_id] = {
                    "last_question": text,
                    "last_answer": qa_result,
                    "last_active": current_time,
                    "history": self.conversation_contexts.get(session_id, {}).get("history", []) + [{"question": text, "answer": qa_result}]
                }
            
            return qa_result
        except Exception as e:
            print(f"❌ 질문 처리 중 오류 발생: {str(e)}")
            return {"error": str(e)}
    
    async def get_response_text(self, qa_result: Dict) -> str:
        """
        QA 결과에서 텍스트 응답을 추출하는 함수
        
        Args:
            qa_result: QA 시스템의 응답 결과
            
        Returns:
            str: 텍스트 응답
        """
        if "error" in qa_result:
            return f"오류 발생: {qa_result['error']}"
        
        full_response = ""
        async for chunk in qa_result["answer_stream"]:
            full_response += chunk
        
        return full_response
    
    def clean_old_contexts(self, max_age_seconds=86400):
        """
        오래된 대화 컨텍스트를 정리하는 함수
        
        Args:
            max_age_seconds: 최대 보관 시간 (초 단위, 기본값: 24시간)
        """
        while True:
            try:
                current_time = time.time()
                keys_to_remove = []
                
                # 오래된 컨텍스트 식별
                for session_id, context in self.conversation_contexts.items():
                    # 마지막 활동 시간 (기록이 없으면 현재 시간 사용)
                    last_active = context.get("last_active", current_time)
                    if current_time - last_active > max_age_seconds:
                        keys_to_remove.append(session_id)
                
                # 오래된 컨텍스트 제거
                for key in keys_to_remove:
                    del self.conversation_contexts[key]
                    print(f"🧹 오래된 세션 정리: {key}")
                
                # 컨텍스트 통계 출력
                if self.conversation_contexts:
                    print(f"🔍 활성 세션 수: {len(self.conversation_contexts)}")
                
                # 1시간마다 체크
                time.sleep(3600)
            except Exception as e:
                print(f"컨텍스트 클리닝 중 오류: {str(e)}")
                time.sleep(3600)  # 오류 발생해도 계속 실행

# FastAPI 초기화
api = FastAPI(title="RAG 기반 질의응답 API")

# CORS 설정
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 요청 모델
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryStreamRequest(QueryRequest):
    pass

# QA 시스템 매니저 인스턴스 생성
qa_manager = None

# API 엔드포인트 정의
@api.post("/api/query")
async def handle_query(request: QueryRequest):
    """일반 비스트리밍 응답 API"""
    global qa_manager
    
    # 세션 ID가 없는 경우 새로 생성
    session_id = request.session_id or qa_manager.generate_session_id()

    # AI 응답 생성
    try:
        qa_result = await qa_manager.process_question(request.query, session_id)
        full_response = await qa_manager.get_response_text(qa_result)

        # 응답 데이터 준비
        response_data = {
            "response": full_response,
            "session_id": session_id
        }

        # 컨텍스트 소스가 있는 경우 포함
        if "context_sources" in qa_result:
            response_data["context_sources"] = qa_result["context_sources"]

        return JSONResponse(
            content=response_data,
            media_type="application/json; charset=utf-8",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답 생성 중 오류 발생: {str(e)}")

@api.post("/api/query/stream")
async def handle_query_stream(request: QueryStreamRequest):
    """스트리밍 응답 API"""
    global qa_manager
    
    # 세션 ID가 없는 경우 새로 생성
    session_id = request.session_id or qa_manager.generate_session_id()

    # AI 응답 스트리밍 함수 정의
    async def stream_response():
        try:
            qa_result = await qa_manager.process_question(request.query, session_id)
            
            # 시작 정보 전송
            yield json.dumps({
                "type": "start",
                "session_id": session_id
            }) + "\n"
            
            # 응답 청크 스트리밍
            async for chunk in qa_result["answer_stream"]:
                yield json.dumps({
                    "type": "chunk",
                    "content": chunk
                }) + "\n"
            
            # 종료 정보 전송
            end_data = {
                "type": "end"
            }
            
            # 컨텍스트 소스가 있는 경우 포함
            if "context_sources" in qa_result:
                end_data["context_sources"] = qa_result["context_sources"]
                
            yield json.dumps(end_data) + "\n"
            
        except Exception as e:
            # 오류 정보 전송
            yield json.dumps({
                "type": "error",
                "error": str(e)
            }) + "\n"

    # 스트리밍 응답 반환
    return StreamingResponse(
        stream_response(),
        media_type="application/x-ndjson; charset=utf-8"
    )

# 세션 관리 엔드포인트
@api.get("/api/sessions")
async def list_sessions():
    """활성 세션 목록 조회"""
    global qa_manager
    
    sessions = []
    for session_id, context in qa_manager.conversation_contexts.items():
        sessions.append({
            "session_id": session_id,
            "last_question": context.get("last_question", ""),
            "last_active": context.get("last_active", 0),
            "conversation_length": len(context.get("history", []))
        })
    
    return {"sessions": sessions}

@api.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제"""
    global qa_manager
    
    if session_id in qa_manager.conversation_contexts:
        del qa_manager.conversation_contexts[session_id]
        return {"message": f"세션 {session_id} 삭제 완료"}
    else:
        raise HTTPException(status_code=404, detail=f"세션 {session_id}를 찾을 수 없습니다")

# 건강 상태 확인 엔드포인트
@api.get("/health")
async def health_check():
    """시스템 건강 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_sessions": len(qa_manager.conversation_contexts) if qa_manager else 0
    }

# CLI 인터페이스 클래스 정의
class QASystemCLI:
    """질의응답 시스템 CLI 인터페이스"""
    
    def __init__(self, qa_manager: QASystemManager):
        """
        CLI 인터페이스 초기화
        
        Args:
            qa_manager: QA 시스템 매니저 인스턴스
        """
        self.qa_manager = qa_manager
        self.session_id = qa_manager.generate_session_id()
        
    async def start(self):
        """CLI 인터페이스 시작"""
        print("\n=== RAG 기반 질의응답 시스템 ===")
        print("종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
        
        while True:
            # 사용자 입력 받기
            query = input("\n🧠 질문을 입력하세요: ")
            
            # 종료 명령 확인
            if query.lower() in ["exit", "quit", "종료"]:
                print("👋 프로그램을 종료합니다.")
                break
            
            if not query.strip():
                print("❗️ 질문을 입력해주세요.")
                continue
            
            # 로딩 메시지 표시 (별도 스레드)
            stop_event = threading.Event()
            loading_thread = threading.Thread(
                target=self._display_loading_animation,
                args=(stop_event,)
            )
            loading_thread.daemon = True
            loading_thread.start()
            
            try:
                # 질문 처리
                qa_result = await self.qa_manager.process_question(query, self.session_id)
                
                # 로딩 애니메이션 중지
                stop_event.set()
                loading_thread.join()
                
                # 응답 출력
                print("\n")  # 줄바꿈으로 로딩 메시지와 구분
                
                if "error" in qa_result:
                    print(f"❌ 오류 발생: {qa_result['error']}")
                else:
                    print("\n💬 답변:")
                    async for chunk in qa_result["answer_stream"]:
                        print(chunk, end="", flush=True)
                    print("\n")
                    
                    # 컨텍스트 소스가 있는 경우 출력
                    if "context_sources" in qa_result:
                        print("\n📚 참고 소스:")
                        for source in qa_result["context_sources"]:
                            print(f"  - {source}")
                
            except Exception as e:
                # 오류 발생 시 로딩 애니메이션 중지
                stop_event.set()
                if loading_thread.is_alive():
                    loading_thread.join()
                
                print(f"\n❌ 오류 발생: {str(e)}")
    
    def _display_loading_animation(self, stop_event):
        """로딩 애니메이션 표시 함수"""
        loading_messages = [
            "🤔 답변을 생성하는 중입니다   ",
            "🤔 답변을 생성하는 중입니다.  ",
            "🤔 답변을 생성하는 중입니다.. ",
            "🤔 답변을 생성하는 중입니다..."
        ]
        idx = 0
        
        while not stop_event.is_set():
            print(f"\r{loading_messages[idx]}", end="", flush=True)
            idx = (idx + 1) % len(loading_messages)
            time.sleep(0.3)

# 메인 함수 정의
def run_api_server():
    """API 서버 실행 함수"""
    print("🚀 API 서버 시작...")
    server_config = config.get_server_config()
    uvicorn.run(
        api, 
        host=server_config.get('host', '0.0.0.0'),
        port=server_config.get('port', 5001)
    )

async def run_cli():
    """CLI 인터페이스 실행 함수"""
    global qa_manager
    cli = QASystemCLI(qa_manager)
    await cli.start()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 기반 질의응답 시스템")
    parser.add_argument("--mode", choices=["api", "cli"], default="cli", help="실행 모드 (api: API 서버, cli: 대화형 인터페이스)")
    parser.add_argument("--prompt-type", default="general", help="프롬프트 유형")
    parser.add_argument("--no-rag", action="store_true", help="RAG 비활성화")
    
    args = parser.parse_args()
    
    # QA 시스템 매니저 인스턴스 초기화
    qa_manager = QASystemManager(
        prompt_type=args.prompt_type,
        use_rag=not args.no_rag
    )
    
    # 대화 컨텍스트 정리 스레드 시작
    cleaning_thread = threading.Thread(target=qa_manager.clean_old_contexts, daemon=True)
    cleaning_thread.start()
    
    if args.mode == "api":
        run_api_server()
    else:
        asyncio.run(run_cli())
