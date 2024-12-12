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
    if "market_trends" not in focus_areas:
        return {**state, "next_agent": "competitor"}

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.MARKET_TRENDS_START)
    start_time = time.time()

    # Format base prompt with context
    previous_findings = json.dumps(state.get('research_data', {}), indent=2)
    current_query = state['messages'][-1].content if state['messages'] else "Analyze market trends"

    formatted_prompt = BASE_PROMPT.format(
        role_description=MARKET_TRENDS_ROLE,
        research_context=current_query,
        previous_findings=previous_findings,
        query=current_query
    )

    # Generate search queries
    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=formatted_prompt)
    ])

    research_data = state.get('research_data', {})
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    # Analyze results using the same base prompt
    analysis_prompt = BASE_PROMPT.format(
        role_description=MARKET_TRENDS_ROLE,
        research_context=f"Analyze these market trends:\n\n{json.dumps(search_results)}",
        previous_findings=previous_findings,
        query=current_query
    )

    response = model.invoke([
        SystemMessage(content=analysis_prompt)
    ])

    research_data['market_trends'] = {
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    }

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.MARKET_TRENDS_COMPLETE} (took {elapsed_time:.2f} seconds)")

    return {
        "messages": state.get('messages', []) + [response],
        "research_data": research_data,
        "next_agent": "competitor",
        "final_report": state.get("final_report", ""),
        "_status_callback": status_callback,
        "focus_areas": focus_areas
    }

def competitor_node(state: MarketResearchState):
    """Node for competitor analysis"""
    focus_areas = state.get("focus_areas", [])
    if "competitor_analysis" not in focus_areas:
        return {**state, "next_agent": "consumer"}

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.COMPETITOR_START)
    start_time = time.time()

    previous_findings = json.dumps(state.get('research_data', {}), indent=2)
    current_query = state['messages'][-1].content if state['messages'] else "Analyze competitors"

    formatted_prompt = BASE_PROMPT.format(
        role_description=COMPETITOR_ROLE,
        research_context=current_query,
        previous_findings=previous_findings,
        query=current_query
    )

    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=formatted_prompt)
    ])

    research_data = state.get('research_data', {})
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    analysis_prompt = BASE_PROMPT.format(
        role_description=COMPETITOR_ROLE,
        research_context=f"Analyze these competitor insights:\n\n{json.dumps(search_results)}",
        previous_findings=previous_findings,
        query=current_query
    )

    response = model.invoke([
        SystemMessage(content=analysis_prompt)
    ])

    research_data['competitor'] = {
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    }

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.COMPETITOR_COMPLETE} (took {elapsed_time:.2f} seconds)")

    return {
        "messages": state.get('messages', []) + [response],
        "research_data": research_data,
        "next_agent": "consumer",
        "final_report": state.get("final_report", ""),
        "_status_callback": status_callback,
        "focus_areas": focus_areas
    }

def consumer_node(state: MarketResearchState):
    """Node for consumer analysis"""
    focus_areas = state.get("focus_areas", [])
    if "consumer_behavior" not in focus_areas:
        return {**state, "next_agent": "report"}

    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.CONSUMER_START)
    start_time = time.time()

    previous_findings = json.dumps(state.get('research_data', {}), indent=2)
    current_query = state['messages'][-1].content if state['messages'] else "Analyze consumer behavior"

    formatted_prompt = BASE_PROMPT.format(
        role_description=CONSUMER_ROLE,
        research_context=current_query,
        previous_findings=previous_findings,
        query=current_query
    )

    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=formatted_prompt)
    ])

    research_data = state.get('research_data', {})
    search_results = []
    for query in queries.queries:
        results = search_tool.invoke({"query": query})
        search_results.extend(results)

    analysis_prompt = BASE_PROMPT.format(
        role_description=CONSUMER_ROLE,
        research_context=f"Analyze these consumer insights:\n\n{json.dumps(search_results)}",
        previous_findings=previous_findings,
        query=current_query
    )

    response = model.invoke([
        SystemMessage(content=analysis_prompt)
    ])

    research_data['consumer'] = {
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    }

    end_time = time.time()
    elapsed_time = end_time - start_time
    if status_callback:
        status_callback(f"{AgentStatus.CONSUMER_COMPLETE} (took {elapsed_time:.2f} seconds)")

    return {
        "messages": state.get('messages', []) + [response],
        "research_data": research_data,
        "next_agent": "report",
        "final_report": state.get("final_report", ""),
        "_status_callback": status_callback,
        "focus_areas": focus_areas
    }

def report_node(state: MarketResearchState):
    """Node for generating final report"""
    status_callback = state.get("_status_callback")
    if status_callback:
        status_callback(AgentStatus.REPORT_START)

    research_data = state.get('research_data', {})
    current_query = state['messages'][-1].content if state['messages'] else "Generate final report"
    previous_findings = json.dumps(research_data, indent=2)

    formatted_prompt = BASE_PROMPT.format(
        role_description=REPORT_ROLE,
        research_context="Generate comprehensive final report",
        previous_findings=previous_findings,
        query=current_query
    )

    response = model.invoke([
        SystemMessage(content=formatted_prompt)
    ])

    if status_callback:
        status_callback(AgentStatus.REPORT_COMPLETE)

    return {
        **state,
        "final_report": response.content,
        "next_agent": END
    }

def should_continue(state: MarketResearchState):
    """Determine next node based on state"""
    current_agent = state["next_agent"]
    focus_areas = state.get("focus_areas", [])

    print(f"[DEBUG] Should Continue - Current Agent: {current_agent}, Focus Areas: {focus_areas}")

    # If we're at the END or report, stop
    if current_agent in [END, "report"]:
        return END

    # Map agents to their focus areas
    agent_to_focus = {
        "market_trends": "market_trends",
        "competitor": "competitor_analysis",
        "consumer": "consumer_behavior"
    }

    # If current agent is in focus areas, let it execute by returning its name
    if agent_to_focus.get(current_agent) in focus_areas:
        print(f"[DEBUG] Should Continue - Executing {current_agent}")
        return current_agent

    # If current agent isn't in focus areas, find next valid agent
    agent_sequence = ["market_trends", "competitor", "consumer"]
    try:
        current_idx = agent_sequence.index(current_agent)
        remaining_agents = agent_sequence[current_idx + 1:]
    except ValueError:
        remaining_agents = []

    # Look for the next agent that matches a selected focus area
    for next_agent in remaining_agents:
        if agent_to_focus[next_agent] in focus_areas:
            print(f"[DEBUG] Should Continue - Moving to {next_agent}")
            return next_agent

    # If no more matching agents, go to report
    print("[DEBUG] Should Continue - Moving to report")
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
