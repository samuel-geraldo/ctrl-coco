"""Titik masuk .exe: PyInstaller butuh skrip, bukan `python -m ctrlcoco`."""
import sys

from ctrlcoco.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
