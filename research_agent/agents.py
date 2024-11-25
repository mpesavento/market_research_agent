# agents.py
"""
Agent implementations for the market research system.
Includes base agent class and specialized agents for different aspects of market research.
"""
import os
from datetime import datetime
import time
import json
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AnyMessage, SystemMessage, BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from research_agent.utils import AgentType, MODEL_NAME, TEMPERATURE, AgentStatus
from research_agent.prompts import (
    BASE_PROMPT, MARKET_TRENDS_ROLE, COMPETITOR_ROLE,
    CONSUMER_ROLE, REPORT_ROLE
)

from langchain_community.tools.tavily_search import TavilySearchResults
from tavily import TavilyClient
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any
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

class SearchQueries(BaseModel):
    """Model for structured search queries"""
    queries: List[str]


def market_trends_node(state: MarketResearchState):
    """Node for market trends research"""
    status_callback = state.get("_status_callback") or print
    start_time = time.time()
    status_callback(AgentStatus.MARKET_TRENDS_START)
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

    elapsed = time.time() - start_time
    status_callback(f"{AgentStatus.MARKET_TRENDS_COMPLETE} (took {elapsed:.1f}s)")
    return {
        "messages": state['messages'] + [response],
        "research_data": research_data,
        "next_agent": "competitor",
        "final_report": None
    }

def competitor_node(state: MarketResearchState):
    """Node for competitor analysis"""
    status_callback = state.get("_status_callback") or print
    start_time = time.time()
    status_callback(AgentStatus.COMPETITOR_START)
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

    elapsed = time.time() - start_time
    status_callback(f"{AgentStatus.COMPETITOR_COMPLETE} (took {elapsed:.1f}s)")
    return {
        "messages": state['messages'] + [response],
        "research_data": research_data,
        "next_agent": "consumer",
        "final_report": None
    }

def consumer_node(state: MarketResearchState):
    """Node for consumer analysis"""
    status_callback = state.get("_status_callback") or print
    start_time = time.time()
    status_callback(AgentStatus.CONSUMER_START)
    queries = model.with_structured_output(SearchQueries).invoke([
        SystemMessage(content=CONSUMER_ROLE),
        HumanMessage(content=state['messages'][-1].content if state['messages'] else "Analyze consumer behavior")
    ])

    research_data = state['research_data']
    if 'consumer' not in research_data:
        research_data['consumer'] = {}

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

    research_data['consumer'].update({
        "last_update": datetime.now().isoformat(),
        "findings": response.content,
        "search_results": search_results
    })

    elapsed = time.time() - start_time
    status_callback(f"{AgentStatus.CONSUMER_COMPLETE} (took {elapsed:.1f}s)")
    return {
        "messages": state['messages'] + [response],
        "research_data": research_data,
        "next_agent": "report",
        "final_report": None
    }

def report_node(state: MarketResearchState):
    """Node for final report generation"""
    status_callback = state.get("_status_callback") or print
    start_time = time.time()
    status_callback(AgentStatus.REPORT_START)
    # Compile all research data
    market_trends = state['research_data'].get('market_trends', {}).get('findings', '')
    competitor_analysis = state['research_data'].get('competitor', {}).get('findings', '')
    consumer_insights = state['research_data'].get('consumer', {}).get('findings', '')

    # Generate comprehensive report
    report_prompt = f"""Based on our research:

Market Trends:
{market_trends}

Competitor Analysis:
{competitor_analysis}

Consumer Insights:
{consumer_insights}

Please generate a comprehensive market research report that synthesizes all these findings.
Include key insights, recommendations, and potential opportunities."""

    response = model.invoke([
        SystemMessage(content=REPORT_ROLE),
        HumanMessage(content=report_prompt)
    ])

    elapsed = time.time() - start_time
    status_callback(f"{AgentStatus.REPORT_COMPLETE} (took {elapsed:.1f}s)")
    return {
        "messages": state['messages'] + [response],
        "research_data": state['research_data'],
        "next_agent": END,
        "final_report": response.content
    }

def should_continue(state: MarketResearchState):
    """Determine next node based on state"""
    return state["next_agent"]
