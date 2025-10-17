#!/usr/bin/env python3
import sys
from pathlib import Path
import windguru
import render

def main():
    """
    Run the complete wind forecast workflow:
    1. Fetch and process forecast data (windguru.py)
    2. Generate HTML report (render.py)
    3. Create JPG snapshot of the report
    """
    print("1. Fetching forecast data...")
    try:
        windguru.main()
    except Exception as e:
        print(f"Error fetching forecast data: {e}", file=sys.stderr)
        return 1

    print("\n2. Generating report...")
    try:
        # Pass --jpg flag to render.py
        sys.argv = [sys.argv[0], "--jpg"]  # Simulate --jpg argument
        render.main()
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())