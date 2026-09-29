import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger("food_label_backend")

def load_keys_from_env_or_file() -> List[str]:
    """
    Safely loads Gemini API keys from environment variables or local uncommitted keys file.
    No keys are hardcoded in source code.
    """
    keys = []
    
    # 1. From environment variables (recommended for production/deployment)
    env_keys = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY")
    if env_keys:
        for k in env_keys.split(","):
            cleaned = k.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    # 2. From local uncommitted keys.txt (in .gitignore) if present
    project_root = Path(__file__).resolve().parent
    candidate_paths = [
        project_root / "keys.txt",
        project_root / ".env",
        Path.cwd() / "keys.txt",
        Path.cwd() / ".env",
    ]
    for p in candidate_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("GEMINI_API_KEYS=") or line.startswith("GEMINI_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            for k in val.split(","):
                                if k.strip() and k.strip() not in keys:
                                    keys.append(k.strip())
                        elif not "=" in line and len(line) > 10:
                            if line not in keys:
                                keys.append(line)
            except Exception as e:
                logger.warning(f"Could not read keys from {p}: {e}")

    return keys

class KeyManager:
    def __init__(self):
        self.keys: List[str] = load_keys_from_env_or_file()
        self._current_index: int = 0
        if self.keys:
            logger.info(f"Loaded {len(self.keys)} Gemini API keys from environment/keys file.")
        else:
            logger.warning("No Gemini API keys found. Please set GEMINI_API_KEYS environment variable.")

    @property
    def current_key(self) -> str:
        if not self.keys:
            # Re-attempt loading in case environment variable was set dynamically
            self.keys = load_keys_from_env_or_file()
            if not self.keys:
                raise ValueError("No Gemini API keys found. Set the GEMINI_API_KEYS environment variable.")
        return self.keys[self._current_index % len(self.keys)]

    def rotate_key(self) -> str:
        if not self.keys:
            raise ValueError("No Gemini API keys available to rotate.")
        self._current_index = (self._current_index + 1) % len(self.keys)
        logger.warning(f"Rotated to Gemini API key index {self._current_index}")
        return self.current_key

    def get_all_keys(self) -> List[str]:
        if not self.keys:
            self.keys = load_keys_from_env_or_file()
        return self.keys

key_manager = KeyManager()
