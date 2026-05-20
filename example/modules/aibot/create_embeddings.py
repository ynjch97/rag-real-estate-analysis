import os
import re
import openai
import json
from pathlib import Path
from datetime import datetime
from config_utils import ConfigManager
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import MarkdownTextSplitter


class QAEmbedding:
    def __init__(self, config_path: str = "config.ini"):
        # 설정 로드
        self.config_manager = ConfigManager(config_path)
        self.config_manager.validate_paths()

        # OpenAI 설정
        openai_config = self.config_manager.get_openai_config()
        self.api_key = openai_config.get('api_key') or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. 'config.ini' 또는 환경 변수를 확인하세요.")

        openai.api_key = self.api_key

        # 경로 설정
        paths_config = self.config_manager.get_paths_config()
        self.docs_dir = Path(paths_config['docs_dir']).resolve()
        self.embedding_dir = Path(paths_config['embedding_dir']).resolve()

        # 모델 설정
        model_config = self.config_manager.get_model_config()
        chunk_size = model_config.get('chunk_size', 512)
        chunk_overlap = model_config.get('chunk_overlap', 50)
        
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        self.text_splitter = MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "folders": set(),
            "total_questions": 0,
            "file_question_counts": {}
        }

    def extract_qa_pairs(self, content: str, file_path: str) -> list:
        """마크다운 파일에서 Question/Answer 쌍을 추출하는 향상된 메서드
        
        여러 형식의 Question/Answer 패턴을 인식하며, 마크다운 구조를 고려합니다.
        """
        qa_pairs = []
        
        # 기본 패턴: "Question: ... Answer: ..." 형식 
        # 줄바꿈, 여러 공백 등을 허용하고 다음 Question이나 파일 끝까지 캡처
        pattern = r'Question:\s*(.*?)\s*Answer:\s*(.*?)(?=\s*Question:|$)'
        
        # 대소문자 구분 없이 검색하고, 여러 줄에 걸친 내용 허용
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        file_name = str(file_path)
        self.stats["file_question_counts"][file_name] = len(matches)
        
        for match in matches:
            question = match[0].strip()
            answer = match[1].strip()
            
            # 빈 질문이나 답변은 건너뜀
            if not question or not answer:
                continue
                
            # 마크다운 포맷 정리 (필요시)
            # 예: 불필요한 마크다운 기호 제거, 중복 공백 제거 등
            question = self._clean_markdown_text(question)
            answer = self._clean_markdown_text(answer)
            
            qa_pairs.append({
                "content": f"Question: {question}\nAnswer: {answer}",
                "metadata": {
                    "source": str(file_path),
                    "type": "qa_pair",
                    "question": question,
                    "file_name": Path(file_path).name
                }
            })
            
            self.stats["total_questions"] += 1
        
        return qa_pairs
    
    def _clean_markdown_text(self, text: str) -> str:
        """마크다운 텍스트 정리
        
        불필요한 마크다운 기호, 중복 공백 등을 제거하고 텍스트 정리
        """
        # 여러 줄바꿈을 단일 줄바꿈으로 변환
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 줄 끝의 공백 제거
        text = re.sub(r' +$', '', text, flags=re.MULTILINE)
        
        # 텍스트 중간의 중복 공백 제거
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()

    def process_documents(self):
        """문서 처리 로직"""
        questions = []
        md_files = list(self.docs_dir.rglob("*.md"))
        self.stats["total_files"] = len(md_files)

        print(f"\n총 {len(md_files)}개의 마크다운 파일을 처리합니다...")

        for file_path in md_files:
            try:
                relative_path = file_path.relative_to(self.docs_dir)
                self.stats["folders"].add(str(relative_path.parent))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                qa_pairs = self.extract_qa_pairs(content, file_path)
                questions.extend(qa_pairs)

                self.stats["processed_files"] += 1
                print(f"  ✓ {file_path.name} - {len(qa_pairs)}개 Q&A 쌍 추출됨")
                
            except Exception as e:
                print(f"  ✗ {file_path} 처리 중 오류 발생: {str(e)}")

        return questions

    def create_embeddings(self):
        """벡터 임베딩 생성 및 저장"""
        self.embedding_dir.mkdir(parents=True, exist_ok=True)
        questions = self.process_documents()

        if not questions:
            raise ValueError("처리할 Q&A 쌍이 없습니다. 문서를 확인해주세요.")

        print(f"\n총 {len(questions)}개의 Q&A 쌍을 임베딩합니다...")
        
        texts = [q["content"] for q in questions]
        metadatas = [q["metadata"] for q in questions]

        vector_store = FAISS.from_texts(texts=texts, embedding=self.embeddings, metadatas=metadatas)

        # 벡터 스토어 저장
        vector_store_path = self.embedding_dir / "vector_store"
        vector_store.save_local(str(vector_store_path))
        print(f"  ✓ 벡터 스토어가 저장되었습니다: {vector_store_path}")

        # 통계 정보 최종 업데이트 및 저장
        self.stats["folders"] = list(self.stats["folders"])
        self.stats["last_update"] = datetime.now().isoformat()

        metadata_path = self.embedding_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 메타데이터가 저장되었습니다: {metadata_path}")

        print(f"\n임베딩 생성 완료!")
        print(f"  - 처리된 파일: {self.stats['processed_files']}/{self.stats['total_files']}")
        print(f"  - 추출된 Q&A 쌍: {self.stats['total_questions']}")
        print(f"  - 저장 위치: {self.embedding_dir}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Q&A 문서 임베딩 생성기")
    parser.add_argument("--config", default="config.ini", help="설정 파일 경로")
    args = parser.parse_args()

    embedder = QAEmbedding(args.config)
    embedder.create_embeddings()

if __name__ == "__main__":
    main()