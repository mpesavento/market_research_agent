# agents.py
"""
Agent implementations for the market research system.
Includes base agent class and specialized agents for different aspects of market research.
"""

from datetime import datetime
import json
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from utils import AgentState, AgentType, MODEL_NAME, TEMPERATURE
from prompts import (
    BASE_PROMPT, MARKET_TRENDS_ROLE, COMPETITOR_ROLE,
    CONSUMER_ROLE, REPORT_ROLE
)

from langchain_community.tools.tavily_search import TavilySearchResults
from tavily import TavilyClient

# client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
# tool = TavilySearchResults(max_results=4) #increased number of results

class BaseAgent:
    """
    Base agent class providing common functionality for all market research agents.

    Attributes:
        role_description (str): Description of the agent's role and responsibilities
        agent_type (str): Type identifier for the agent
        next_agent (str): Identifier of the next agent in the workflow
        chain (Chain): LangChain chain for processing queries
    """

    def __init__(self, role_description: str, agent_type: str, next_agent: str):
        """
        Initialize a new agent.

        Args:
            role_description (str): Description of the agent's role
            agent_type (str): Type identifier for the agent
            next_agent (str): Next agent in the workflow
        """
        self.role_description = role_description
        self.agent_type = agent_type
        self.next_agent = next_agent
        self.chain = self._create_chain()

    def _create_chain(self):
        """
        Create the LangChain processing chain for the agent.

        Returns:
            Chain: Configured LangChain chain
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", BASE_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ])

        return prompt | ChatOpenAI(
            temperature=TEMPERATURE,
            model=MODEL_NAME
        )

    def process(self, state: AgentState) -> AgentState:
        """
        Process the current state and generate response.

        Args:
            state (AgentState): Current state of the workflow

        Returns:
            AgentState: Updated state after processing
        """
        messages = state["messages"]
        research_data = state["research_data"]

        response = self.chain.invoke({
            "role_description": self.role_description,
            "research_context": json.dumps(research_data.get(self.agent_type, {})),
            "previous_findings": json.dumps(research_data),
            "messages": messages,
            "query": messages[-1].content if messages else f"Analyze {self.agent_type}"
        })

        if self.agent_type not in research_data:
            research_data[self.agent_type] = {}

        research_data[self.agent_type].update({
            "last_update": datetime.now().isoformat(),
            "findings": response.content
        })

        return {
            "messages": messages + [response],
            "research_data": research_data,
            "next_agent": self.next_agent,
            "final_report": None
        }

class MarketTrendsAgent(BaseAgent):
    """Agent specialized in analyzing market trends and industry dynamics."""

    def __init__(self):
        super().__init__(
            MARKET_TRENDS_ROLE,
            AgentType.MARKET_TRENDS.value,
            AgentType.COMPETITOR.value
        )

class CompetitorAgent(BaseAgent):
    """Agent specialized in analyzing competitors and their offerings."""

    def __init__(self):
        super().__init__(
            COMPETITOR_ROLE,
            AgentType.COMPETITOR.value,
            AgentType.CONSUMER.value
        )

class ConsumerAgent(BaseAgent):
    """Agent specialized in analyzing consumer behavior and preferences."""

    def __init__(self):
        super().__init__(
            CONSUMER_ROLE,
            AgentType.CONSUMER.value,
            AgentType.REPORT.value
        )

class ReportAgent(BaseAgent):
    """
    Agent specialized in generating comprehensive market research reports
    by synthesizing findings from other agents.
    """

    def __init__(self):
        super().__init__(
            REPORT_ROLE,
            AgentType.REPORT.value,
            AgentType.END.value
        )

    def process(self, state: AgentState) -> AgentState:
        """
        Generate a comprehensive report from all collected research data.

        Args:
            state (AgentState): Current state containing all research findings

        Returns:
            AgentState: Updated state including the final report
        """
        messages = state["messages"]
        research_data = state["research_data"]

        # Create a summary prompt that includes all findings
        report_prompt = f"""
        Based on the following research findings, generate a comprehensive market research report:

        Market Trends:
        {research_data.get('market_trends', {}).get('findings', 'No data available')}

        Competitor Analysis:
        {research_data.get('competitor', {}).get('findings', 'No data available')}

        Consumer Insights:
        {research_data.get('consumer', {}).get('findings', 'No data available')}

        Format the report using markdown with clear sections and bullet points where appropriate.
        """

        messages.append(HumanMessage(content=report_prompt))

        response = self.chain.invoke({
            "role_description": self.role_description,
            "research_context": json.dumps(research_data),
            "previous_findings": json.dumps(research_data),
            "messages": messages,
            "query": report_prompt
        })

        return {
            "messages": messages + [response],
            "research_data": research_data,
            "next_agent": self.next_agent,
            "final_report": response.content
        }
