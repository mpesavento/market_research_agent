# agents.py
"""
Agent implementations for the market research system.
Includes base agent class and specialized agents for different aspects of market research.
"""
import os
from datetime import datetime
import json
import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AnyMessage, SystemMessage, BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from research_agent.utils import AgentState, AgentType, MODEL_NAME, TEMPERATURE, AgentStatus
from research_agent.prompts import (
    BASE_PROMPT, MARKET_TRENDS_ROLE, COMPETITOR_ROLE,
    CONSUMER_ROLE, REPORT_ROLE
)

from langchain_community.tools.tavily_search import TavilySearchResults
from tavily import TavilyClient
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any, Optional, Callable
from pydantic import BaseModel

# Global tools setup
search_tool = TavilySearchResults(max_results=4)

# Model definition
model = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)

class MarketResearchState(TypedDict):
    """State for the market research workflow"""
    messages: List[AnyMessage]
    research_data: dict
    next_agent: str
    final_report: str | None
    _status_callback: Optional[Callable]
    focus_areas: List[str]

class SearchQueries(BaseModel):
    """Model for structured search queries"""
    queries: List[str]

def market_trends_node(state: MarketResearchState):
    """Node for market trends research"""
    focus_areas = state.get("focus_areas", [])
    print(f"[DEBUG] Market Trends Node - Focus Areas: {focus_areas}")

    # Skip if not in focus areas
    if "market_trends" not in focus_areas:
        print("[DEBUG] Skipping Market Trends Node")
        return {
            **state,
            "next_agent": "competitor",
            "research_data": state.get("research_data", {}),
            "messages": state.get("messages", []),
            "final_report": state.get("final_report", ""),
            "_status_callback": state.get("_status_callback"),
            "focus_areas": focus_areas
        }

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.MARKET_TRENDS_START)
    start_time = time.time()

    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=MARKET_TRENDS_ROLE),
        HumanMessage(content=state['messages'][-1].content if state['messages'] else "Analyze market trends")
    ])

    research_data = state['research_data']
    if 'market_trends' not in research_data:
        research_data['market_trends'] = {}

    # Perform searches and collect results
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    # Process results with LLM
    response = model.invoke([
        SystemMessage(content=MARKET_TRENDS_ROLE),
        HumanMessage(content=f"Analyze these market trends findings:\n\n{json.dumps(search_results)}")
    ])

    research_data['market_trends'].update({
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    })

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.MARKET_TRENDS_COMPLETE} (took {elapsed_time:.2f} seconds)")
    return {
        "messages": state['messages'] + [response],
        "research_data": research_data,
        "next_agent": "competitor",
        "final_report": None,
        "_status_callback": status_callback
    }

def competitor_node(state: MarketResearchState):
    """Node for competitor analysis"""
    focus_areas = state.get("focus_areas", [])
    print(f"[DEBUG] Competitor Node - Focus Areas: {focus_areas}")

    # Skip if not in focus areas
    if "competitor_analysis" not in focus_areas:
        print("[DEBUG] Skipping Competitor Node")
        return {
            **state,
            "next_agent": "consumer",
            "research_data": state.get("research_data", {}),
            "messages": state.get("messages", []),
            "final_report": state.get("final_report", ""),
            "_status_callback": state.get("_status_callback"),
            "focus_areas": focus_areas
        }

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.COMPETITOR_START)
    start_time = time.time()
    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=COMPETITOR_ROLE),
        HumanMessage(content=state['messages'][-1].content if state['messages'] else "Analyze competitors")
    ])

    research_data = state['research_data']
    if 'competitor' not in research_data:
        research_data['competitor'] = {}

    # Perform searches and collect results
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    # Process results with LLM
    response = model.invoke([
        SystemMessage(content=COMPETITOR_ROLE),
        HumanMessage(content=f"Analyze these competitor findings:\n\n{json.dumps(search_results)}")
    ])

    research_data['competitor'].update({
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    })

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.COMPETITOR_COMPLETE} (took {elapsed_time:.2f} seconds)")
    return {
        "messages": state['messages'] + [response],
        "research_data": research_data,
        "next_agent": "consumer",
        "final_report": None,
        "_status_callback": status_callback
    }

def consumer_node(state: MarketResearchState):
    """Node for consumer analysis"""
    focus_areas = state.get("focus_areas", [])
    print(f"[DEBUG] Consumer Node - Focus Areas: {focus_areas}")

    # Skip if not in focus areas
    if "consumer_behavior" not in focus_areas:
        print("[DEBUG] Skipping Consumer Node")
        return {
            **state,
            "next_agent": "report",
        }

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.CONSUMER_START)
    start_time = time.time()

    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=CONSUMER_ROLE),
        HumanMessage(content=state['messages'][-1].content if state['messages'] else "Analyze consumer behavior")
    ])

    # Initialize research_data if it doesn't exist
    research_data = state.get('research_data', {})
    print(f"[DEBUG] Consumer Node - Initial Research Data: {research_data}")

    # Perform searches and collect results
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    # Process results with LLM
    response = model.invoke([
        SystemMessage(content=CONSUMER_ROLE),
        HumanMessage(content=f"Analyze these consumer insights:\n\n{json.dumps(search_results)}")
    ])

    # Store the findings
    research_data['consumer'] = {
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    }

    print(f"[DEBUG] Consumer Node - Updated Research Data: {research_data}")

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.CONSUMER_COMPLETE} (took {elapsed_time:.2f} seconds)")

    updated_state = {
        "messages": state.get('messages', []) + [response],
        "research_data": research_data,
        "next_agent": "report",
        "final_report": state.get("final_report", ""),
        "_status_callback": status_callback,
        "focus_areas": focus_areas
    }
    print(f"[DEBUG] Consumer Node - Returning State Keys: {updated_state.keys()}")
    return updated_state

def report_node(state: MarketResearchState):
    """Node for final report generation"""
    print(f"[DEBUG] Report Node - Entering with State Keys: {state.keys()}")
    print(f"[DEBUG] Report Node - Research Data Keys: {state.get('research_data', {}).keys()}")

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.REPORT_START)

    focus_areas = state.get("focus_areas", [])
    research_data = state.get('research_data', {})

    print(f"[DEBUG] Report Node - Full Research Data: {research_data}")

    # Compile research data only from selected focus areas
    report_sections = []

    if "consumer_behavior" in focus_areas and 'consumer' in research_data:
        consumer_insights = research_data['consumer'].get('findings', '')
        if consumer_insights:
            print("[DEBUG] Report Node - Found consumer insights")
            report_sections.append(f"Consumer Insights:\n{consumer_insights}")

    # Generate report
    if report_sections:
        print("[DEBUG] Report Node - Generating report from sections")
        report_prompt = "Based on our research:\n\n" + "\n\n".join(report_sections)
        report_prompt += "\n\nPlease generate a comprehensive market research report that synthesizes these findings."

        response = model.invoke([
            SystemMessage(content=REPORT_ROLE),
            HumanMessage(content=report_prompt)
        ])

        final_report = response.content
        print(f"[DEBUG] Report Node - Generated Report Length: {len(final_report)}")

        if status_callback:
            status_callback(AgentStatus.REPORT_COMPLETE)

        return {
            "messages": state.get('messages', []) + [response],
            "research_data": research_data,
            "next_agent": END,
            "final_report": final_report,
            "_status_callback": status_callback,
            "focus_areas": focus_areas
        }
    else:
        print("[DEBUG] Report Node - No research sections found")
        error_msg = "No research data was found for the selected focus areas."
        if status_callback:
            status_callback(f"❌ Error: {error_msg}")
        raise RuntimeError(error_msg)

def should_continue(state: MarketResearchState):
    """Determine next node based on state"""
    current_agent = state["next_agent"]
    focus_areas = state.get("focus_areas", [])

    print(f"[DEBUG] Current agent: {current_agent}, Focus areas: {focus_areas}")

    # Mapping between focus areas and agents
    focus_to_agent = {
        "market_trends": ["market_trends"],
        "competitor_analysis": ["competitor"],
        "consumer_behavior": ["consumer"]
    }

    # If we're at the report node, end the sequence
    if current_agent == "report":
        return END

    # If no focus areas specified, run all agents
    if not focus_areas:
        return state["next_agent"]

    # Define the full sequence
    agent_sequence = ["market_trends", "competitor", "consumer", "report"]
    current_idx = agent_sequence.index(current_agent)

    # Find the next enabled agent
    for next_agent in agent_sequence[current_idx + 1:]:
        if next_agent == "report":
            return "report"

        # Check if this agent corresponds to a selected focus area
        for focus, agents in focus_to_agent.items():
            if next_agent in agents and focus.lower() in focus_areas:
                print(f"[DEBUG] Moving to next agent: {next_agent}")
                return next_agent

    print("[DEBUG] No more agents to run, moving to report")
    return "report"

def build_research_graph():
    """Build the research workflow graph"""
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
            AgentType.COMPETITOR.value: "competitor",
            END: END
        }
    )

    builder.add_conditional_edges(
        "competitor",
        should_continue,
        {
            AgentType.CONSUMER.value: "consumer",
            END: END
        }
    )

    builder.add_conditional_edges(
        "consumer",
        should_continue,
        {
            AgentType.REPORT.value: "report",
            END: END
        }
    )

    builder.add_conditional_edges(
        "report",
        should_continue,
        {END: END}
    )

    return builder.compile()
