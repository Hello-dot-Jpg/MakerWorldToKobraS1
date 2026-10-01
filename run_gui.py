from __future__ import annotations

from pathlib import Path
import sys


repository = Path(__file__).resolve().parent
sys.path.insert(0, str(repository / "src"))

from s1_optimizer.gui import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
