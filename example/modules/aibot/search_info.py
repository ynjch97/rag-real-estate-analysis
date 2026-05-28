"""
search_info.py - 수정된 버전
"""

import os
import asyncio
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator, Any
from config_utils import ConfigManager
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class QuestionAnalyzer:
    def __init__(self, model_config, openai_config):
        """질문을 분석하여 요점과 핵심 키워드를 추출하는 Agent"""
        self.llm = ChatOpenAI(
            model=model_config['model_name'],
            temperature=0.2,
            api_key=openai_config['api_key']
        )

    async def analyze_question(self, question: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "사용자의 질문을 분석하여 핵심 요점과 검색에 사용할 키워드를 추출하세요."),
            ("human", "{input}")
        ])

        chain = prompt | self.llm
        response = await chain.ainvoke({"input": question})
        return response.content.strip()

class Agent:
    def __init__(self, model_config: Dict, openai_config: Dict, prompt_dir: Path, prompt_file: str, use_rag: bool = True):
        self.model_config = model_config
        self.prompt_dir = prompt_dir
        self.prompt_file = prompt_file
        self.use_rag = use_rag
        self.llm = ChatOpenAI(
            model=model_config['model_name'],
            temperature=model_config['temperature'],
            max_tokens=model_config.get('max_tokens', 1024),
            api_key=openai_config['api_key'],
            streaming=True
        )

    def _load_prompt(self) -> str:
        prompt_path = self.prompt_dir / self.prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    async def process_stream(self, question: str, context: Optional[List[Dict]] = None, previous_context: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 이전 컨텍스트가 있으면 질문에 포함
        enhanced_question = question
        if previous_context and 'last_question' in previous_context and 'last_answer' in previous_context:
            enhanced_question = f"이전 질문: {previous_context['last_question']}\n이전 답변의 요약: {self._summarize_previous_answer(previous_context['last_answer'])}\n\n새 질문: {question}"

        if self.use_rag:
            if context is None or len(context) == 0:
                yield "관련된 문서를 찾을 수 없습니다."
                return

            relevant_answers = []
            for doc in context:
                content = doc["content"]
                source = doc["metadata"]["source"]
                similarity = doc["similarity"]

                if similarity >= 0.3:
                    answer_section = self.extract_answer_section(content)
                    if answer_section:
                        relevant_answers.append(f"📌 출처: {source}\n{answer_section}")

            if not relevant_answers:
                yield "관련된 문서를 찾을 수 없습니다."
                return

            formatted_context = "\n\n".join(relevant_answers)
            system_content = self._load_prompt().format(
                context=formatted_context,
                current_time=current_time
            )
        else:
            system_content = self._load_prompt().format(
                context="",  # 빈 컨텍스트 제공
                current_time=current_time
            )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=enhanced_question)
        ]

        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

    def _summarize_previous_answer(self, previous_answer: Any) -> str:
        """이전 답변을 요약하여 문자열로 반환합니다."""
        # previous_answer가 문자열인 경우
        if isinstance(previous_answer, str):
            # 너무 긴 경우 앞부분만 사용
            if len(previous_answer) > 200:
                return previous_answer[:200] + "..."
            return previous_answer
        
        # previous_answer가 딕셔너리인 경우
        elif isinstance(previous_answer, dict):
            if "error" in previous_answer:
                return f"이전 질문에서 오류 발생: {previous_answer['error']}"
            return "이전 답변이 있지만 형식을 알 수 없습니다."
        
        # 그 외 타입인 경우
        return "이전 답변 있음"

    def extract_answer_section(self, content: str) -> Optional[str]:
        try:
            match = re.search(r"Question:\s*(.*?)\s*Answer:\s*(.*)", content, re.DOTALL)
            if match:
                answer_part = match.group(2).strip()
                if answer_part:
                    return answer_part
        except Exception as e:
            print(f"❌ [오류] Answer 섹션 추출 실패: {str(e)}")

        return None

class MultiAgentQASystem:
    def __init__(self, prompt_type: str = "general", use_rag: bool = True):
        self.config_manager = ConfigManager()
        self.config_manager.validate_paths()

        self.openai_config = self.config_manager.get_openai_config()
        self.paths_config = self.config_manager.get_paths_config()
        self.model_config = self.config_manager.get_model_config()
        self.prompt_config = self.config_manager.get_prompt_config()

        self.embeddings = OpenAIEmbeddings(api_key=self.openai_config['api_key'])
        self.vector_store = self._load_vector_store() if use_rag else None

        # 프롬프트 파일 결정
        prompt_file = self.prompt_config.get(prompt_type, self.prompt_config.get("general"))
        
        self.agent = Agent(
            self.model_config,
            self.openai_config,
            self.paths_config['prompt_dir'],
            prompt_file,
            use_rag
        )

        self.question_analyzer = QuestionAnalyzer(self.model_config, self.openai_config)

    def _load_vector_store(self) -> Optional[FAISS]:
        try:
            vector_store_path = self.paths_config['embedding_dir'] / "vector_store"
            if vector_store_path.exists():
                return FAISS.load_local(str(vector_store_path), self.embeddings, allow_dangerous_deserialization=True)
            print("⚠️ Vector store가 없습니다. 데이터를 먼저 임베딩해주세요.")
            return None
        except Exception as e:
            print(f"⚠️ Vector store 로드 중 오류 발생: {str(e)}")
            return None

    async def _get_relevant_context(self, analyzed_question: str, k: int = 10) -> Optional[List[Dict]]:
        if self.vector_store is None:
            return None

        try:
            similar_docs = self.vector_store.similarity_search_with_score(analyzed_question, k=k)
            results = []

            for i, (doc, score) in enumerate(similar_docs, 1):
                content = doc.page_content
                source = doc.metadata["source"]
                similarity = 1 - score  

                if similarity < 0.3:
                    continue

                answer = self.agent.extract_answer_section(content)
                if not answer:
                    continue

                results.append({
                    "content": content,
                    "metadata": {"source": source},
                    "similarity": similarity
                })

            return results if results else []
        
        except Exception as e:
            print(f"⚠️ 컨텍스트 검색 중 오류 발생: {str(e)}")
            return []

    async def process_question(self, question: str, context: Optional[Dict] = None) -> Dict:
        """
        질문을 처리하고 답변을 생성합니다.
        
        Args:
            question: 사용자 질문
            context: 이전 대화 컨텍스트 (선택적)
        
        Returns:
            Dict: 질문, 분석된 질문, 답변 스트림 등을 포함한 딕셔너리
        """
        try:
            analyzed_question = await self.question_analyzer.analyze_question(question)

            search_context = await self._get_relevant_context(analyzed_question) if self.agent.use_rag else None

            result = {
                "question": question,
                "analyzed_question": analyzed_question,
                "answer_stream": self.agent.process_stream(question, search_context, context)
            }

            if search_context:
                result["context_sources"] = [doc["metadata"]["source"] for doc in search_context]

            return result
        except Exception as e:
            print(f"❌ 질문 처리 중 오류 발생: {str(e)}")
            raise
