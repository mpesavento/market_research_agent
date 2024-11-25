import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence, Union
from enum import Enum
import operator
from langchain_core.messages import AnyMessage, BaseMessage, SystemMessage, HumanMessage, ToolMessage

# Load environment variables
load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    research_data: dict
    final_report: Union[str, None]

class AgentType(str, Enum):
    MARKET_TRENDS = "market_trends"
    COMPETITOR = "competitor"
    CONSUMER = "consumer"
    REPORT = "report"
    END = "end"


# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0

class AgentStatus:
    """Standardized status messages for agent workflow"""
    MARKET_TRENDS_START = "🔍 Starting Market Trends Analysis..."
    MARKET_TRENDS_COMPLETE = "✅ Market Trends Analysis complete"
    COMPETITOR_START = "🏢 Starting Competitor Analysis..."
    COMPETITOR_COMPLETE = "✅ Competitor Analysis complete"
    CONSUMER_START = "👥 Starting Consumer Behavior Analysis..."
    CONSUMER_COMPLETE = "✅ Consumer Analysis complete"
    REPORT_START = "📝 Starting Final Report Generation..."
    REPORT_COMPLETE = "✅ Final Report Generation complete"
    WAITING = "⏳ Waiting to start..."

# Progress mapping for UI updates
PROGRESS_MAP = {
    AgentStatus.MARKET_TRENDS_START: 0.05,
    AgentStatus.MARKET_TRENDS_COMPLETE: 0.39,
    AgentStatus.COMPETITOR_START: 0.4,
    AgentStatus.COMPETITOR_COMPLETE: 0.59,
    AgentStatus.CONSUMER_START: 0.6,
    AgentStatus.CONSUMER_COMPLETE: 0.79,
    AgentStatus.REPORT_START: 0.8,
    AgentStatus.REPORT_COMPLETE: 0.9,
}
