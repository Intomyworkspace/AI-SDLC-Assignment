import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("\n========== BANDIT SECURITY CHECK ==========")
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-r",
         "client_short_allocation"],
        check=False,
        cwd=ROOT
    )
    print("\nSECURITY GATE:", "PASS" if result.returncode == 0 else "FAIL")
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
