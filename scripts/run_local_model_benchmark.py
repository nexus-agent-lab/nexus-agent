import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    from app.benchmarks.runner import default_output_dir, default_suite_dir

    parser = argparse.ArgumentParser(description="Run the Nexus local model benchmark suite.")
    parser.add_argument("--suite-dir", default=str(default_suite_dir()))
    parser.add_argument("--output-dir", default=str(default_output_dir()))
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"))
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY", "ollama"))
    parser.add_argument("--models", nargs="+", required=True, help="One or more model ids to benchmark.")
    parser.add_argument("--repetitions", type=int, default=None)
    return parser.parse_args()


async def main() -> None:
    from app.benchmarks.runner import BenchmarkRunner

    args = parse_args()
    runner = BenchmarkRunner(
        suite_dir=args.suite_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        api_key=args.api_key,
    )
    result = await runner.run(models=args.models, repetitions=args.repetitions)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
