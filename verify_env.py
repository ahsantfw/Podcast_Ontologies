
import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print("Sys path:")
for p in sys.path:
    print(f"  - {p}")

try:
    import langgraph
    print(f"LangGraph version: {langgraph.__version__ if hasattr(langgraph, '__version__') else 'unknown'}")
    print(f"LangGraph location: {langgraph.__file__}")
except ImportError as e:
    print(f"LangGraph import failed: {e}")

try:
    from core_engine.reasoning.langgraph_workflow import create_retrieval_workflow
    print("Successfully imported create_retrieval_workflow")
except ImportError as e:
    print(f"Core engine import failed: {e}")
