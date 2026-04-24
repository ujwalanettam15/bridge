from pathlib import Path

from dotenv import load_dotenv


def load_bridge_env() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    repo_root = backend_dir.parents[1]
    load_dotenv(repo_root / ".env")
    load_dotenv(backend_dir / ".env")
