import pytest
import os

@pytest.fixture(autouse=True)
def env_setup():
    """Ensure environment variables are set for testing"""
    os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'dummy_key')
    os.environ['TAVILY_API_KEY'] = os.environ.get('TAVILY_API_KEY', 'dummy_key')
