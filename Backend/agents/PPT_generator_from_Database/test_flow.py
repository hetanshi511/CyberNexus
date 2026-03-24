
import os
import sys
import logging
from dotenv import load_dotenv

# Add Backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_utils import test_connection, get_schema_summary, execute_read_query
from graph_logic import searching_schema_node, searching_table_node, query_agent_node, DeckState

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_db_layer():
    print("\nXXX TESTING DB LAYER XXX")
    if test_connection():
        print("PASS: Database Connection Successful")
    else:
        print("FAIL: Database Connection Failed")
        return False

    schema = get_schema_summary()
    if schema and "Error" not in schema:
        print(f"PASS: Schema Retrieval ({len(schema)} chars)")
    else:
        print(f"FAIL: Schema Retrieval - {schema}")
        return False
        
    return True

def test_agent_layer():
    print("\nXXX TESTING AGENT LAYER XXX")
    
    # 1. Setup Mock State
    state = {
        "raw_input": "Show me the top 5 workflows from admin_workflows",
        "current_step": "start"
    }
    
    # 2. Run Schema Search
    print("\n--- Running Schema Search Node ---")
    state.update(searching_schema_node(state))
    if not state.get("db_schema"):
        print("FAIL: Schema Search Node did not produce schema")
        return
    print("PASS: Schema Search Node")
    
    # 3. Run Table Search
    print("\n--- Running Table Search Node ---")
    # This calls LLM, so it might fail if creds aren't there, but we catch exceptions
    res = searching_table_node(state)
    if res.get("error_message"):
        print(f"FAIL: Table Search Node Error: {res['error_message']}")
        # Continue anyway for partial testing
    else:
        state.update(res)
        print(f"PASS: Table Search Node (Found: {state.get('relevant_tables')})")
        
    # 4. Run Query Agent
    print("\n--- Running Query Agent Node ---")
    # If we failed table search, this might fail, but let's try
    if not state.get("relevant_tables"):
        print("SKIP: Query Agent Node (No relevant tables)")
    else:
        res = query_agent_node(state)
        if res.get("error_message"):
            print(f"FAIL: Query Agent Node Error: {res['error_message']}")
        else:
            state.update(res)
            print(f"PASS: Query Agent Node")
            print(f"Generated SQL: {state.get('generated_sql')}")
            print(f"Query Results: {len(state.get('query_results', []))} rows")

if __name__ == "__main__":
    load_dotenv()
    if test_db_layer():
        try:
            test_agent_layer()
        except Exception as e:
            print(f"FAIL: Agent Layer Exception: {e}")
