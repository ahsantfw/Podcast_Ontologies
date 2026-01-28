
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

# Mock setup
class MockRetriever:
    def retrieve(self, query, **kwargs):
        print(f"MockRetriever called with: {query}")
        return []

class MockNeo4jClient:
    def execute_read(self, query, params=None):
        return []

@dataclass
class MockAgentResponse:
    answer: str
    sources: list
    metadata: dict

class MockAgent:
    def __init__(self, workspace_id="default", model="gpt-4o-mini", neo4j_client=None, hybrid_retriever=None):
        self.workspace_id = workspace_id
        self.model = model
        self.openai_client = None # Mocked separately if needed
        
    def _resolve_pronouns(self, query, metadata):
        return query
        
    def _synthesize_answer(self, query, resolved_query, rag_results, kg_results, conversation_history, session_metadata):
        print("!!! _synthesize_answer WAS CALLED !!!")
        return "This is a hallucinated answer about society issues."
        
    def _extract_sources(self, rag_results, kg_results):
        return []


# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import LangGraph components
try:
    from core_engine.reasoning.langgraph_workflow import create_retrieval_workflow, run_workflow_simple
    from core_engine.reasoning.langgraph_state import RetrievalState, QueryPlan
except ImportError:
    print("Failed to import LangGraph components. Make sure dependencies are installed.")
    sys.exit(1)

def test_enforcement():
    print("--- Testing Retrieval Enforcement ---")
    
    # Setup mocks
    retriever = MockRetriever()
    neo4j_client = MockNeo4jClient()
    agent = MockAgent()
    
    # Query that triggered the issue
    query = "what are the issues of the society?"
    
    # Mock OpenAI Client for planner (we want to simulate the planner's output)
    # Since we can't easily mock the internal planner logic unless we mock the OpenAI client deep inside,
    # we will manually construct the state after planning if possible?
    # No, run_workflow_simple takes dependencies.
    
    # We need a real OpenAI client or a mock that returns the expected classification.
    # Let's mock the openai_client passed to run_workflow_simple.
    
    class MockOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    # Mock response based on prompt
                    messages = kwargs.get("messages", [])
                    prompt = messages[-1]["content"] if messages else ""
                    
                    if "Analyze query complexity" in prompt:
                        return MockResponse('{"complexity": "moderate", "intent": "knowledge_query", "needs_decomposition": false, "entities": [], "relationships": []}')
                    
                    if "Check domain relevance" in prompt:
                        return MockResponse('{"is_relevant": true, "reason": "Relevant"}')
                        
                    if "Analyze if this query is a follow-up" in prompt:
                        return MockResponse('{"is_follow_up": false, "referenced_entities": [], "context_summary": "", "previous_topics": []}')

                    return MockResponse("{}")

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockMessage:
        def __init__(self, content):
            self.content = content

    openai_client = MockOpenAI()
    
    # Run the workflow
    try:
        final_state = run_workflow_simple(
            workflow=create_retrieval_workflow(),
            query=query,
            conversation_history=[],
            session_metadata={},
            hybrid_retriever=retriever,
            neo4j_client=neo4j_client,
            podcast_agent=agent,
            openai_client=openai_client,
        )
        
        print(f"\nFinal Answer: {final_state.get('answer')}")
        print(f"RAG Count: {len(final_state.get('rag_results', []))}")
        print(f"KG Count: {len(final_state.get('kg_results', []))}")
        print(f"Should Continue: {final_state.get('should_continue')}")
        
    except Exception as e:
        print(f"Error running workflow: {e}")

if __name__ == "__main__":
    test_enforcement()
