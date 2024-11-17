# main.py
"""
Main execution script for the market research system.
Provides interface for running market research analysis.
"""

from langchain_core.messages import HumanMessage
from utils import AgentType
from workflow import MarketResearchWorkflow


def run_market_research(query: str):
    """
    Execute a market research analysis with the given query.

    Args:
        query (str): Initial research query or objective

    Prints progress updates and final report to console.
    """
    workflow = MarketResearchWorkflow()

    initial_state = {
        "messages": [HumanMessage(content=query)],
        "next_agent": AgentType.MARKET_TRENDS.value,
        "research_data": {},
        "final_report": None
    }

    print("Starting market research analysis...")
    print("-" * 50)

    for output in workflow.run(initial_state):
        agent_name = output["next_agent"].replace("_", " ").title()
        print(f"\n{agent_name} Agent completed its analysis.")

        if output.get("final_report"):
            print("\n=== Final Market Research Report ===\n")
            print(output["final_report"])
            print("\n=== End of Report ===\n")
            break


if __name__ == "__main__":
    query = """Conduct a comprehensive market analysis of wearable fitness trackers,
    focusing on current trends, major competitors, and consumer preferences.
    Pay special attention to emerging technologies and integration opportunities
    with personalized wellness coaching systems."""

    run_market_research(query)