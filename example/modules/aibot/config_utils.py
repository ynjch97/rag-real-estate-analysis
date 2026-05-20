import os
from pathlib import Path
import configparser
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self) -> None:
        """설정 파일 로드 및 필수 항목 검증"""
        if not os.path.exists(self.config_path):
            print(f"⚠️ 설정 파일을 찾을 수 없습니다: {self.config_path}")
            print("기본 설정 파일을 생성합니다...")
            
            # 기본 설정 내용
            default_config = """[openai]
                api_key = api_key_secret

                [paths]
                docs_dir = docs/md
                embedding_dir = qa_embeddings
                prompt_dir = prompts

                [model]
                model_name = gpt-4o
                temperature = 0.1
                max_tokens = 1024
                chunk_size = 1000
                chunk_overlap = 200

                [prompt]
                general = custom_prompt.txt
                """
            # 설정 파일 저장
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(default_config)
            
            print(f"✅ 기본 설정 파일이 생성되었습니다: {self.config_path}")
            print("필요에 맞게 설정을 수정해주세요.")
        
        self.config.read(self.config_path, encoding='utf-8')

        # 필수 설정 섹션과 키 검증
        required_keys = {
            'openai': ['api_key'],
            'paths': ['docs_dir', 'embedding_dir', 'prompt_dir'],
            'model': ['model_name', 'temperature', 'chunk_size', 'chunk_overlap'],
            'prompt': ['general']
        }

        for section, keys in required_keys.items():
            if section not in self.config:
                raise ValueError(f"❌ 설정 파일에 필수 섹션이 없습니다: [{section}]")

            for key in keys:
                if key not in self.config[section]:
                    raise ValueError(f"❌ 설정 파일의 [{section}] 섹션에서 필수 키 '{key}'가 누락되었습니다.")

    def get_openai_config(self) -> Dict[str, str]:
        """OpenAI 관련 설정 반환"""
        return {
            'api_key': self.config.get('openai', 'api_key')
        }

    def get_paths_config(self) -> Dict[str, Path]:
        """경로 관련 설정 반환"""
        return {
            'docs_dir': Path(self.config.get('paths', 'docs_dir')).resolve(),
            'embedding_dir': Path(self.config.get('paths', 'embedding_dir')).resolve(),
            'prompt_dir': Path(self.config.get('paths', 'prompt_dir')).resolve(),
            'api_keys_dir': Path(self.config.get('paths', 'api_keys_dir', fallback='api_keys')).resolve()
        }

    def get_model_config(self) -> Dict[str, Any]:
        """모델 관련 설정 반환"""
        return {
            'model_name': self.config.get('model', 'model_name', fallback='gpt-4o'),
            'temperature': self.config.getfloat('model', 'temperature', fallback=0.1),
            'max_tokens': self.config.getint('model', 'max_tokens', fallback=1024),
            'chunk_size': self.config.getint('model', 'chunk_size', fallback=1000),
            'chunk_overlap': self.config.getint('model', 'chunk_overlap', fallback=200)
        }

    def get_prompt_config(self) -> Dict[str, str]:
        """프롬프트 관련 설정 반환"""
        return {
            'general': self.config.get('prompt', 'general')
        }

    def get_server_config(self) -> Dict[str, Any]:
        """서버 관련 설정 반환"""
        return {
            'host': self.config.get('server', 'host', fallback='0.0.0.0'),
            'port': self.config.getint('server', 'port', fallback=5001)
        }

    def validate_paths(self) -> None:
        """경로 유효성 검증 및 자동 생성"""
        paths = self.get_paths_config()

        # 각 디렉토리 검증 및 자동 생성
        for name, path in paths.items():
            if not path.exists():
                print(f"📂 {name.replace('_', ' ').title()} directory not found. Creating: {path}")
                path.mkdir(parents=True, exist_ok=True)