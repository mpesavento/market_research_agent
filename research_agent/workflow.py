# workflow.py
"""
Workflow implementation for coordinating market research agents.
Defines the execution graph and manages agent interactions.
"""

from langgraph.graph import StateGraph, END
from utils import AgentState, AgentType
from agents import MarketTrendsAgent, CompetitorAgent, ConsumerAgent, ReportAgent

class MarketResearchWorkflow:
    """
    Coordinates the execution of multiple agents for market research.

    Manages the workflow of market trends analysis, competitor analysis,
    consumer insights, and report generation.
    """

    def __init__(self):
        """Initialize the workflow with all required agents."""
        self.market_trends_agent = MarketTrendsAgent()
        self.competitor_agent = CompetitorAgent()
        self.consumer_agent = ConsumerAgent()
        self.report_agent = ReportAgent()
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        """
        Create the workflow graph defining agent interactions.

        Returns:
            Graph: Compiled workflow graph
        """
        workflow = StateGraph(AgentState)

        # Add agent nodes
        workflow.add_node(AgentType.MARKET_TRENDS.value, self.market_trends_agent.process)
        workflow.add_node(AgentType.COMPETITOR.value, self.competitor_agent.process)
        workflow.add_node(AgentType.CONSUMER.value, self.consumer_agent.process)
        workflow.add_node(AgentType.REPORT.value, self.report_agent.process)

        # Define edges
        workflow.add_edge(AgentType.MARKET_TRENDS.value, AgentType.COMPETITOR.value)
        workflow.add_edge(AgentType.COMPETITOR.value, AgentType.CONSUMER.value)
        workflow.add_edge(AgentType.CONSUMER.value, AgentType.REPORT.value)

        # Add conditional ending
        workflow.add_conditional_edges(
            AgentType.REPORT.value,
            self._should_end,
            {
                True: END,
                False: AgentType.MARKET_TRENDS.value
            }
        )

        return workflow.compile()

    @staticmethod
    def _should_end(state: AgentState) -> bool:
        """
        Determine if the workflow should end.

        Args:
            state (AgentState): Current workflow state

        Returns:
            bool: True if workflow should end, False otherwise
        """
        return state["next_agent"] == AgentType.END.value

    def run(self, state: AgentState):
        """
        Run the workflow with the given initial state.

        Args:
            state (AgentState): Initial workflow state

        Returns:
            Iterator: Stream of states as the workflow progresses
        """
        return self.workflow.stream(state)