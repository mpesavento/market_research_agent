# workflow.py
"""
Workflow implementation for coordinating market research agents.
Defines the execution graph and manages agent interactions.
"""
from datetime import datetime
import time
from typing import TypedDict, List, Dict, Optional, Callable, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, HumanMessage

from research_agent.agents import (
    market_trends_node, competitor_node,
    consumer_node, report_node, should_continue, MarketResearchState
)
from research_agent.storage import create_storage_backend, StorageBackend

class MarketResearchOrchestrator:
    """Orchestrates multiple agents in a market research workflow"""
    def __init__(
        self,
        storage_type: str = "local",
        storage_config: Optional[dict] = None,
        status_callback: Optional[Callable] = None
    ):
        """
        Initialize the orchestrator

        Args:
            storage_type: Type of storage ("local" or "s3")
            storage_config: Configuration for storage backend
            status_callback: Optional callback for status updates
        """
        self.graph = self._build_graph()
        self.status_callback = status_callback or (lambda x: None)

        # Initialize storage
        storage_config = storage_config or {}
        self.storage = create_storage_backend(storage_type, **storage_config)

    def _build_graph(self):
        """Internal method to build the workflow graph"""
        builder = StateGraph(MarketResearchState)

        # Add nodes
        builder.add_node("market_trends", market_trends_node)
        builder.add_node("competitor", competitor_node)
        builder.add_node("consumer", consumer_node)
        builder.add_node("report", report_node)

        # Add edges for market_trends node
        builder.add_conditional_edges(
            "market_trends",
            should_continue,
            {
                "competitor": "competitor",
                "consumer": "consumer",
                "report": "report",
                END: END
            }
        )

        # Add edges for competitor node
        builder.add_conditional_edges(
            "competitor",
            should_continue,
            {
                "consumer": "consumer",
                "report": "report",
                END: END
            }
        )

        # Add edges for consumer node
        builder.add_conditional_edges(
            "consumer",
            should_continue,
            {
                "report": "report",
                END: END
            }
        )

        # Add edge for report node
        builder.add_conditional_edges(
            "report",
            should_continue,
            {END: END}
        )

        # Set entry point - this will be determined by the initial state
        builder.set_entry_point("market_trends")

        return builder.compile()

    def _save_final_report(self, report: str, query: str, timestamp: str) -> dict:
        """
        Save the final report using the storage backend

        Returns:
            dict: Contains file info including path and access URL
        """
        filename = f"market_research_report_{timestamp}.txt"
        content = (
            "=== Market Research Report ===\n\n"
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Query: {query}\n\n"
            + "-" * 50 + "\n\n"
            + f"{report}\n\n"
            + "-" * 50 + "\n"
        )

        file_path = self.storage.save_file(content, filename)
        access_path = self.storage.get_file_url(filename)

        return {
            "filename": filename,
            "path": file_path,
            "access_path": access_path
        }

    def _save_intermediate_findings(
        self,
        findings: Dict,
        query: str,
        timestamp: str
    ) -> Optional[dict]:
        """
        Save intermediate findings using the storage backend

        Returns:
            Optional[dict]: File info if findings were saved, None otherwise
        """
        if not findings:
            return None

        filename = f"intermediate_findings_{timestamp}.txt"
        content = (
            "=== Market Research Intermediate Findings ===\n\n"
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Query: {query}\n\n"
        )

        for agent, data in findings.items():
            if "findings" in data:
                content += f"\n=== {agent.replace('_', ' ').title()} ===\n"
                content += data["findings"]
                content += "\n" + "-" * 50 + "\n"

        file_path = self.storage.save_file(content, filename)
        access_path = self.storage.get_file_url(filename)

        return {
            "filename": filename,
            "path": file_path,
            "access_path": access_path
        }

    def run_research(self, query: str, focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Orchestrate the research workflow across multiple specialized agents"""
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty")

        # Convert focus areas to standard format and log them
        focus_areas = [area.replace(" ", "_").lower() for area in (focus_areas or [])]
        print(f"[DEBUG] Selected focus areas: {focus_areas}")

        self.status_callback("🔄 Preparing research workflow")

        # Determine the first agent based on focus areas
        first_agent = "report"  # Default to report if no focus areas
        if focus_areas:
            if "market_trends" in focus_areas:
                first_agent = "market_trends"
            elif "competitor_analysis" in focus_areas:
                first_agent = "competitor"
            elif "consumer_behavior" in focus_areas:
                first_agent = "consumer"

        print(f"[DEBUG] Starting with agent: {first_agent}")

        initial_state = {
            "query": query,
            "messages": [HumanMessage(content=query)],
            "research_data": {},
            "final_report": "",
            "agent_outputs": {},
            "_status_callback": self.status_callback,
            "next_agent": first_agent,
            "focus_areas": focus_areas
        }

        # Run the graph
        self.status_callback("🔍 Beginning research analysis")
        start_time = time.time()
        try:
            final_state = self.graph.invoke(initial_state)

            # Check if we need to run the report node explicitly
            if final_state.get("next_agent") == "report":
                print("[DEBUG] Running report node explicitly")
                final_state = report_node(final_state)

            if not final_state.get("final_report"):
                raise RuntimeError("Research failed to generate a report")

        except Exception as e:
            self.status_callback(f"❌ Error during research: {str(e)}")
            raise

        end_time = time.time()
        elapsed_time = end_time - start_time
        self.status_callback(f"✅ Research workflow complete (took {elapsed_time:.2f} seconds)")

        # Save reports
        self.status_callback("💾 Saving research outputs...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_info = self._save_final_report(
            final_state["final_report"],
            query,
            timestamp
        )

        findings_info = self._save_intermediate_findings(
            final_state.get("research_data", {}),
            query,
            timestamp
        )

        self.status_callback("✅ Research workflow complete!")

        return {
            "final_report": final_state["final_report"],
            "report_info": report_info,
            "findings_info": findings_info,
            "agent_outputs": final_state.get("research_data", {})
        }

def create_market_research_orchestrator(
    storage_type: str = "local",
    storage_config: Optional[dict] = None,
    status_callback: Optional[Callable] = None
) -> MarketResearchOrchestrator:
    """
    Create the market research orchestrator

    Args:
        storage_type: Type of storage ("local" or "s3")
        storage_config: Configuration for storage backend
        status_callback: Optional callback for status updates

    Returns:
        MarketResearchOrchestrator: Configured orchestrator
    """
    return MarketResearchOrchestrator(
        storage_type=storage_type,
        storage_config=storage_config,
        status_callback=status_callback
    )
