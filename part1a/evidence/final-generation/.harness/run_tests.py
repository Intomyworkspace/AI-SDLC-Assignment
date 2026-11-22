import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("\n========== UNIT & CONTRACT TESTS ==========")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        check=False,
        cwd=ROOT
    )
    print("\nTEST GATE:", "PASS" if result.returncode == 0 else "FAIL")
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
