import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(script: str) -> None:
    path = PROJECT_ROOT / "ml" / script
    if not path.exists():
        print(f"Skip missing step: {script}", flush=True)
        return

    print(f"\n=== Running {script} ===", flush=True)
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {script}, exit code {result.returncode}")


def main() -> None:
    steps = [
        "prepare_dataset.py",
        "prepare_bid_dataset.py",
        "train_base_price_model.py",
        "train_final_price_model.py",
        "analyze_auction_behavior.py",
        "evaluate.py",
    ]
    for step in steps:
        run_step(step)
    print("\nML pipeline finished successfully.", flush=True)


if __name__ == "__main__":
    main()
