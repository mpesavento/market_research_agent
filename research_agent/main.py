# main.py
"""
Main execution script for the market research system.
Provides interface for running market research analysis.
"""

from langchain_core.messages import HumanMessage
from workflow import build_research_graph, MarketResearchState
from datetime import datetime
import os

def run_market_research(query: str):
    """
    Execute a market research analysis with the given query.
    """
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    graph = build_research_graph()
    initial_state: MarketResearchState = {
        "messages": [HumanMessage(content=query)],
        "research_data": {},
        "next_agent": "market_trends",
        "final_report": None
    }

    print("Starting market research analysis...")
    print("-" * 50)

    intermediate_findings = {}
    timestamp = None

    agent_starttime = datetime.now()

    for output in graph.stream(initial_state):
        agent_endtime = datetime.now()
        agent_duration = agent_endtime - agent_starttime
        print(f"DEBUG - agent duration: {agent_duration}")
        # print(f"\nDEBUG - Raw output: {output}")
        # print(f"DEBUG - Output type: {type(output)}")
        # print(f"DEBUG - Output keys: {output.keys()}")

        try:
            if isinstance(output, dict):
                # Get the agent name (first key in the output dict)
                agent_name = next(iter(output))
                agent_data = output[agent_name]
                print(f"\nDEBUG - Agent name: {agent_name}")
                print(f"DEBUG - Agent data keys: {agent_data.keys() if isinstance(agent_data, dict) else 'Not a dict'}")

                # Print completion message
                print(f"\n{agent_name.replace('_', ' ').title()} analysis completed.")

                # If agent_data contains research findings, store them
                if isinstance(agent_data, dict) and "research_data" in agent_data:
                    print(f"DEBUG - Research data found: {agent_data['research_data']}")
                    intermediate_findings.update(agent_data["research_data"])

                    # Print intermediate findings
                    for data_agent, data in agent_data["research_data"].items():
                        if "findings" in data:
                            print(f"\n=== {data_agent.replace('_', ' ').title()} Findings ===")
                            print(data["findings"])
                            print("-" * 50)

                # Check for final report in agent_data
                if isinstance(agent_data, dict) and agent_data.get("final_report"):
                    final_report = agent_data["final_report"]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Save intermediate findings
                    findings_file = os.path.join(reports_dir, f"intermediate_findings_{timestamp}.txt")
                    with open(findings_file, "w", encoding="utf-8") as f:
                        f.write("=== Market Research Intermediate Findings ===\n\n")
                        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Query: {query}\n\n")

                        for agent, data in intermediate_findings.items():
                            if "findings" in data:
                                f.write(f"\n=== {agent.replace('_', ' ').title()} ===\n")
                                f.write(data["findings"])
                                f.write("\n" + "-" * 50 + "\n")

                    # Save final report
                    report_file = os.path.join(reports_dir, f"market_research_report_{timestamp}.txt")
                    with open(report_file, "w", encoding="utf-8") as f:
                        f.write("=== Market Research Report ===\n\n")
                        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Query: {query}\n\n")
                        f.write("-" * 50 + "\n\n")
                        f.write(final_report)  # Use final_report instead of output["final_report"]
                        f.write("\n\n" + "-" * 50 + "\n")

                    print("\n=== Final Market Research Report ===\n")
                    print(final_report)
                    print("\n=== End of Report ===\n")
                    print(f"Report saved to: {report_file}")
                    print(f"Intermediate findings saved to: {findings_file}")
                    break

            else:
                print(f"\nCompleted step: {output}")


        except Exception as e:
            print(f"DEBUG - Error processing output: {str(e)}")
            print(f"DEBUG - Unexpected output structure: {output}")
            continue

        agent_starttime = datetime.now()

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return {
        "final_report": output.get("final_report"),
        "intermediate_findings": intermediate_findings,
        "timestamp": timestamp
    }

if __name__ == "__main__":
    import argparse
    import textwrap

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

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r') as f:
            query = f.read().strip()
    else:
        query = args.query

    run_market_research(query)