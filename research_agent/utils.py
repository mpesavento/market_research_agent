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
