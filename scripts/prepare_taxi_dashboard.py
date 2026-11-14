"""Prepare the retained taxi tables for the trusted Streamlit presentation, without model calls."""

import argparse
from pathlib import Path

from backintel.presentation.taxi_story import write_story

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = write_story(args.report, args.output)
    print(f"Prepared taxi dashboard data at {path}")
