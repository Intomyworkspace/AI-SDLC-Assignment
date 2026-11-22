import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("\n========== RUFF LINT CHECK ==========")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check",
         "client_short_allocation", "tests", ".harness"],
        check=False,
        cwd=ROOT
    )
    print("\nLINT GATE:", "PASS" if result.returncode == 0 else "FAIL")
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
