# workflow.py
"""
Workflow implementation for coordinating market research agents.
Defines the execution graph and manages agent interactions.
"""

from typing import TypedDict, List, Dict, Optional, Callable
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage
import os
from datetime import datetime

from research_agent.agents import (
    market_trends_node, competitor_node,
    consumer_node, report_node, should_continue, MarketResearchState
)

class MarketResearchOrchestrator:
    """Orchestrates multiple agents in a market research workflow"""
    def __init__(self, status_callback: Callable[[str], None], reports_dir: str = "reports"):
        # Get the directory where the package is installed
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.reports_dir = os.path.join(package_dir, reports_dir)
        self.status_callback = status_callback
        print("Debug - orchestrator initialized with callback:", self.status_callback)
        os.makedirs(self.reports_dir, exist_ok=True)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Internal method to build the workflow graph"""
        builder = StateGraph(MarketResearchState)

        # Add nodes
        builder.add_node("market_trends", market_trends_node)
        builder.add_node("competitor", competitor_node)
        builder.add_node("consumer", consumer_node)
        builder.add_node("report", report_node)

        # Set entry point
        builder.set_entry_point("market_trends")

        # Add conditional edges
        builder.add_conditional_edges(
            "market_trends",
            should_continue,
            {
                "competitor": "competitor",
                END: END
            }
        )

        builder.add_conditional_edges(
            "competitor",
            should_continue,
            {
                "consumer": "consumer",
                END: END
            }
        )

        builder.add_conditional_edges(
            "consumer",
            should_continue,
            {
                "report": "report",
                END: END
            }
        )

        builder.add_conditional_edges(
            "report",
            should_continue,
            {END: END}
        )

        return builder.compile()

    def run_research(self, query: str) -> Dict[str, str]:
        """
        Orchestrate the research workflow across multiple specialized agents

        Args:
            query: The research query to analyze

        Returns:
            Dict containing:
                - final_report: The synthesized research report
                - report_path: Path to saved report file
                - findings_path: Path to saved intermediate findings file
                - agent_outputs: Dict of each specialized agent's findings
        """
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty")

        self.status_callback("Starting market research workflow...")

        # Initialize the state
        initial_state = {
            "query": query,
            "messages": [],
            "research_data": {},
            "final_report": "",
            "agent_outputs": {},
            "_status_callback": self.status_callback  # Pass callback to graph
        }

        # Run the graph
        self.status_callback("Executing research workflow...")
        final_state = self.graph.invoke(initial_state)

        if not final_state.get("final_report"):
            raise RuntimeError("Research failed to generate a report")

        # Save reports
        self.status_callback("Saving research outputs...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self._save_final_report(
            final_state["final_report"],
            query,
            timestamp
        )
        findings_path = self._save_intermediate_findings(
            final_state.get("research_data", {}),
            query,
            timestamp
        )

        self.status_callback("Research workflow complete!")

        return {
            "final_report": final_state["final_report"],
            "report_path": report_path,
            "findings_path": findings_path,
            "agent_outputs": final_state.get("research_data", {})
        }

    def _save_final_report(self, report: str, query: str, timestamp: str) -> str:
        """Save the final report to a file"""
        report_file = os.path.join(self.reports_dir, f"market_research_report_{timestamp}.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("=== Market Research Report ===\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Query: {query}\n\n")
            f.write("-" * 50 + "\n\n")
            f.write(report)
            f.write("\n\n" + "-" * 50 + "\n")
        return report_file

    def _save_intermediate_findings(
        self,
        findings: Dict,
        query: str,
        timestamp: str
    ) -> Optional[str]:
        """Save intermediate findings to a file"""
        if not findings:
            return None

        findings_file = os.path.join(self.reports_dir, f"intermediate_findings_{timestamp}.txt")
        with open(findings_file, "w", encoding="utf-8") as f:
            f.write("=== Market Research Intermediate Findings ===\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Query: {query}\n\n")

            for agent, data in findings.items():
                if "findings" in data:
                    f.write(f"\n=== {agent.replace('_', ' ').title()} ===\n")
                    f.write(data["findings"])
                    f.write("\n" + "-" * 50 + "\n")
        return findings_file

def create_market_research_orchestrator(status_callback: Callable[[str], None]) -> MarketResearchOrchestrator:
    """
    Create the market research agent with workflow graph.

    Returns:
        MarketResearchOrchestrator: Configured market research agent
    """
    print("Debug - creating orchestrator with callback:", status_callback)
    return MarketResearchOrchestrator(status_callback=status_callback)
