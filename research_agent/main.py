# main.py
"""
Main execution script for the market research system.
Provides interface for running market research analysis.
"""

import sys
import time
import argparse
import textwrap
from research_agent.workflow import create_market_research_orchestrator

def print_status(message: str):
    """Print status message with timestamp."""
    print(f"\r{message}", file=sys.stderr)
    sys.stderr.flush()

def main():
    """Run the market research CLI."""
    parser = argparse.ArgumentParser(
        description="Market Research Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Example usage:
            python main.py "Analyze the market for wearable fitness trackers"

            For complex queries, you can use multiple lines with triple quotes in a file:
            python main.py --file query.txt
        """)
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='Path to file containing the research query')
    group.add_argument('query', nargs='?', help='Research query string')

    # args = parser.parse_args()

    # # Get query from file or command line
    # if args.file:
    #     with open(args.file, 'r') as f:
    #         query = f.read().strip()
    # else:
    #     query = args.query


    query = """Conduct a comprehensive market analysis of wearable fitness trackers,
focusing on current trends, major competitors, and consumer preferences.
Pay special attention to emerging technologies and integration opportunities
with personalized wellness coaching systems."""

    print("\nMarket Research Analysis")
    print("=" * 80)
    # Run the research
    try:
        orchestrator = create_market_research_orchestrator(status_callback=print_status)
        start_time = time.time()
        result = orchestrator.run_research(query)
        end_time = time.time()
        print(f"\nResearch completed in {end_time - start_time:.2f} seconds")

        print("\nMarket Research Report:")
        print("=" * 80)
        print(result["final_report"])
        print("=" * 80)
        print(f"\nReport saved to: {result['report_path']}")
        if result.get('findings_path'):
            print(f"Intermediate findings saved to: {result['findings_path']}")

    except Exception as e:
        print(f"Error running market research: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
