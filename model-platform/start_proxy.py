"""
Start LiteLLM Proxy after loading API keys from .env.

Usage:
  python start_proxy.py
  python start_proxy.py --port 4800
"""
import argparse
import subprocess
import sys
from pathlib import Path
from shutil import which

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4800)
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent.parent / '.env')
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
            str(args.port),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
