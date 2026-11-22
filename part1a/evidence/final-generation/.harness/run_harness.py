import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent

GATES = [
    ("LINT", "run_lint.py"),
    ("SECURITY", "run_security.py"),
    ("TESTS", "run_tests.py")
]

def main():
    print("\n========== PART 1A HARNESS ==========")
    results = {}

    for name, script in GATES:
        print(f"\nRunning {name} gate...")
        result = subprocess.run(
            [sys.executable, str(HARNESS / script)],
            check=False,
            cwd=ROOT
        )
        results[name] = result.returncode == 0

    print("\n========== FINAL HARNESS REPORT ==========")

    for name, passed in results.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    overall = all(results.values())
    print("OVERALL RESULT:", "PASS" if overall else "FAIL")

    return 0 if overall else 1

if __name__ == "__main__":
    sys.exit(main())
