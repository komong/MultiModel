"""
Start LiteLLM Proxy after loading API keys from .env.

Usage:
  python start_proxy.py
"""
import subprocess
import sys
from shutil import which

from dotenv import load_dotenv


def main():
    load_dotenv()
    command = [which("litellm")] if which("litellm") else [
        sys.executable,
        "-c",
        "import litellm; litellm.run_server()",
    ]

    return subprocess.call(
        command
        + [
            "--config",
            "config.yaml",
            "--port",
            "4000",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
