# workflow.py
"""
Workflow implementation for coordinating market research agents.
Defines the execution graph and manages agent interactions.
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.messages import AnyMessage
from agents import (
    market_trends_node, competitor_node,
    consumer_node, report_node, should_continue, MarketResearchState
)


def build_research_graph():
    """
    Create the workflow graph defining agent interactions.

    Returns:
        Graph: Compiled workflow graph
    """
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