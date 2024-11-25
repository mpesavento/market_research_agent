import pytest
from unittest.mock import Mock, patch
from research_agent.workflow import create_market_research_orchestrator
from research_agent.agents import MarketResearchState
from langchain_core.messages import AIMessage

# Mock responses for different agents
MOCK_MARKET_TRENDS_RESPONSE = "Market is trending towards digital transformation."
MOCK_COMPETITOR_RESPONSE = "Major competitors include Company A and Company B."
MOCK_CONSUMER_RESPONSE = "Consumers show strong preference for sustainable products."
MOCK_REPORT_RESPONSE = "Final synthesized market research report."

@pytest.fixture
def mock_llm_responses():
    """Mock LLM responses for testing"""
    with patch('research_agent.agents.model') as mock_model:
        # Mock structured output for queries
        mock_model.with_structured_output.return_value.invoke.return_value.queries = [
            "test query 1",
            "test query 2"
        ]

        # Mock regular responses
        mock_model.invoke.return_value = AIMessage(content="Mock response")
        yield mock_model

@pytest.fixture
def mock_search_tool():
    """Mock search tool responses"""
    with patch('research_agent.agents.search_tool') as mock_tool:
        mock_tool.invoke.return_value = [
            {"title": "Test Result", "content": "Test content"}
        ]
        yield mock_tool

# Unit Tests (will run in both CI and local)
@pytest.mark.unit
class TestMarketResearchUnit:
    def test_orchestrator_initialization(self):
        """Test basic orchestrator initialization"""
        orchestrator = create_market_research_orchestrator()
        assert orchestrator is not None
        assert orchestrator.reports_dir == "reports"

    def test_empty_query_validation(self):
        """Test that empty queries are rejected"""
        orchestrator = create_market_research_orchestrator()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            orchestrator.run_research("")

# Integration Tests (will only run when integration marker is enabled)
@pytest.mark.integration
class TestMarketResearchIntegration:
    def test_full_research_workflow(self, mock_llm_responses, mock_search_tool, tmp_path):
        """Test the complete research workflow with mocked external dependencies"""
        # Setup
        reports_dir = tmp_path / "reports"
        orchestrator = create_market_research_orchestrator()
        orchestrator.reports_dir = str(reports_dir)

        # Mock specific responses for different stages
        def mock_invoke_side_effect(messages):
            if "market trends" in str(messages).lower():
                return AIMessage(content=MOCK_MARKET_TRENDS_RESPONSE)
            elif "competitor" in str(messages).lower():
                return AIMessage(content=MOCK_COMPETITOR_RESPONSE)
            elif "consumer" in str(messages).lower():
                return AIMessage(content=MOCK_CONSUMER_RESPONSE)
            else:
                return AIMessage(content=MOCK_REPORT_RESPONSE)

        mock_llm_responses.invoke.side_effect = mock_invoke_side_effect

        # Run research
        query = "Analyze the market for eco-friendly products"
        result = orchestrator.run_research(query)

        # Assertions
        assert result["final_report"] is not None
        assert isinstance(result["final_report"], str)
        assert result["report_path"].endswith(".txt")
        assert result["findings_path"].endswith(".txt")
        assert isinstance(result["agent_outputs"], dict)

        # Verify files were created
        assert reports_dir.exists()
        assert len(list(reports_dir.glob("*.txt"))) == 2  # Should have report and findings files

    def test_status_callback_integration(self):
        """Test that status callbacks are properly called"""
        status_updates = []
        def status_callback(message):
            status_updates.append(message)

        orchestrator = create_market_research_orchestrator(status_callback=status_callback)

        with patch('research_agent.agents.model') as mock_model, \
             patch('research_agent.agents.search_tool') as mock_search:
            # Setup basic mocks
            mock_model.with_structured_output.return_value.invoke.return_value.queries = ["test"]
            mock_model.invoke.return_value = AIMessage(content="Test response")
            mock_search.invoke.return_value = [{"title": "Test", "content": "Test"}]

            # Run research
            orchestrator.run_research("Test query")

        # Verify status updates were received
        assert len(status_updates) > 0
        assert "Starting market research workflow..." in status_updates
        assert "Research workflow complete!" in status_updates