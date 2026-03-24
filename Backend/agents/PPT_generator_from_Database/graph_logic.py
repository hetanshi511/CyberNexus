import os
import json
import boto3
import re
import logging
from typing import Annotated, List, TypedDict, Union, Optional
from dotenv import load_dotenv

# LangChain Imports
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- IMPORT YOUR BUILDER TOOLS ---
from agents.PPT_generator_from_Database.builder_logic import visualization_builder_node, content_builder_node
from agents.PPT_generator_from_Database.db_utils import get_schema_summary, execute_read_query, get_all_table_names

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()



# --- HELPER: ROBUST JSON PARSER WITH MULTIPLE FALLBACKS ---
def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Robust JSON extraction with multiple fallback strategies.
    Returns None if all parsing attempts fail.
    """
    if not text or not isinstance(text, str):
        logger.warning("extract_json_from_text: Invalid input type")
        return None

    text = text.strip()
    if not text:
        return None

    # Strategy 0: Direct Parse (Best Case)
    try:
        data = json.loads(text)
        # Normalize structure
        if isinstance(data, list):
            return {"slides": data}
        elif isinstance(data, dict):
            # Check for slides key
            if "slides" in data and isinstance(data["slides"], list):
                return data
            # Check if any value is a list of slide-like objects
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and "title" in value[0]:
                        return {"slides": value}
            # Single slide object
            if "title" in data:
                return {"slides": [data]}
            # Default: Return the dictionary as-is
            return data
    except:
        pass

    # Strategy 1: Extract JSON from code blocks
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        text = match.group(1).strip()

    # Try parsing
    try:
        data = json.loads(text)
        logger.info(f"JSON Loaded. Type: {type(data)}")

        # Normalize structure
        if isinstance(data, list):
            return {"slides": data}
        elif isinstance(data, dict):
            logger.info("Is Dict")
            # Check for slides key
            if "slides" in data and isinstance(data["slides"], list):
                return data
            # Check if any value is a list of slide-like objects
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and "title" in value[0]:
                        return {"slides": value}
            # Single slide object
            if "title" in data:
                return {"slides": [data]}

            # Default: Return the dictionary as-is (e.g. for searching_table_node)
            logger.info("extract_json_from_text: MATCHED DICT returning data")
            return data

        logger.warning(f"extract_json_from_text: Unexpected structure: {type(data)} Value: {data}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"extract_json_from_text: JSON decode error: {e}")
        # Last resort: try to fix common issues
        try:
            # Remove trailing commas
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            data = json.loads(text)
            if isinstance(data, list):
                return {"slides": data}
            elif isinstance(data, dict) and "title" in data:
                return {"slides": [data]}
        except:
            pass

        return None

    except Exception as e:
        logger.error(f"extract_json_from_text: Unexpected error: {e}")
        return None



# --- STATE DEFINITION ---
class DeckState(TypedDict):
    raw_input: str  # Raw user input (topic or JSON)
    user_instructions: str  # Optional user instructions
    topic: str  # Extracted topic (determined by analyzer)
    source_json: str  # Extracted JSON (determined by analyzer)
    user_query: str  # User query/instructions (determined by analyzer)
    input_analysis: dict  # Analysis result from input analyzer
    slides: List[dict]
    current_step: str
    temp_pptx_path: str  # Temporary PPTX file path for sharing between builder agents
    final_file_path: str
    error_message: str
    generation_warning: str # Warning message if requested slide count wasn't reached
    search_results: str # Results from the Search Agent
    template_name: str # Selected template name
    document_metadata: dict # Metadata for Document Control slide
    
    # --- DB ADDITIONS ---
    db_schema: str # Schema summary
    relevant_tables: List[str] # List of tables relevant to the query
    generated_sql: str # SQL query generated by the agent
    query_results: List[dict] # Results from the DB execution



# --- INITIALIZE BEDROCK WITH ERROR HANDLING ---
def get_bedrock_client():
    """Initialize Bedrock client with proper error handling."""
    try:
        region = os.getenv("AWS_DEFAULT_REGION")
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        logger.info(f"Bedrock client initialized for region: {region}")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        raise

def get_llm():
    """Initialize LLM with proper error handling."""
    try:
        client = get_bedrock_client()
        llm = ChatBedrockConverse(
            client=client,
            model=os.getenv("BEDROCK_MODEL"),
            temperature=0.3,
            max_tokens=8000  
        )
        logger.info("LLM initialized successfully")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise

llm = get_llm()




# --- AGENT 1: SCHEMA SEARCH NODE ---
def searching_schema_node(state: DeckState) -> dict:
    """
    Fetches the database schema to understand available tables and columns.
    Uses a two-step process: 
    1. Fetch all table names.
    2. Filter relevant tables using LLM.
    3. Fetch full schema only for relevant tables.
    """
    logger.info("=== SCHEMA SEARCH AGENT: Fetching DB Schema  ===")
    
    try:
        # Step 1: Get all table names
        all_tables = get_all_table_names()
        if not all_tables:
             return {"error_message": "No tables found in database."}
             
        # Step 2: LLM Filter
        raw_input = state.get("raw_input", "").strip()
        system_prompt = f"""You are a Database Expert.
        
        USER REQUEST: "{raw_input}"
        
        AVAILABLE TABLES:
        {", ".join(all_tables)}
        
        TASK:
        Identify tables clearly related to the user request.
        
        STRICT RULES:
        1. Start with an EMPTY list.
        2. Select a table ONLY if it matches the user request keywords or intent explicitly.
        3. If the request (e.g. "tea") has NO relation to the tables, return an EMPTY list.
        4. Do NOT guess. Do NOT select broadly.
        
        OUTPUT:
        Return a JSON object with a list of "selected_tables".
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Select relevant tables.")
        ]
        
        response = llm.invoke(messages)
        data = extract_json_from_text(response.content)
        # Fix: Default to [] if data is None, do NOT fallback to all_tables
        selected_tables = data.get("selected_tables", []) if data else []
        
        # Fallback if LLM fails or returns empty
        if not selected_tables:
            logger.warning("LLM returned no relevant tables. Strict Mode: Stopping.")
            return {"error_message": "No relevant tables found for this request."}
            
        logger.info(f"Selected {len(selected_tables)} tables from {len(all_tables)} total.")

        # Step 3: Fetch Schema for Selected Tables
        schema_summary = get_schema_summary(table_names=selected_tables)
        logger.info(f"Schema fetched: {len(schema_summary)} chars")
        
        return {
            "db_schema": schema_summary,
            "relevant_tables": selected_tables,
            "current_step": "schema_fetched",
            "error_message": ""
        }
    except Exception as e:
        error_msg = f"Schema Search Agent failed: {e}"
        logger.error(error_msg, exc_info=True)
        return {"error_message": error_msg}





# --- AGENT 3: QUERY AGENT NODE ---
def query_agent_node(state: DeckState) -> dict:
    """
    Generates and executes SQL query to fetch data.
    """
    # Circuit Breaker
    if state.get("error_message"):
        logger.warning("Skipping Query Agent due to previous error.")
        return {"error_message": state.get("error_message")}

    logger.info("=== QUERY AGENT: Generating and Executing SQL ===")
    
    raw_input = state.get("raw_input", "").strip()
    db_schema = state.get("db_schema", "")
    relevant_tables = state.get("relevant_tables", [])
    
    if not relevant_tables:
        logger.warning("No relevant tables found. creating generic query.")
        # Fallback? Or fail? Let's try to pass schema anyway.

    system_prompt = f"""You are a PostgreSQL Expert.
    
    Your task is to generate UP TO 5 SQL queries to retrieve data for the user's request.
    To ensure we get results, you MUST try different angles, ranging from SPECIFIC to BROAD:
    
    1. **Primary Specific Query**: Attempt to answer the user's specific question (e.g. "top 5 errors").
    2. **Simple Aggregation**: A basic COUNT/GROUP BY on a SINGLE relevant table (failsafe).
    3. **Raw Data Sample**: `SELECT * FROM table LIMIT 100`. 
       - *CRITICAL*: Set LIMIT to at least 100 (if data exists) to ensure we have enough content to generate 5-6 slides. 
       - DO NOT use small limits like 5 or 10 for this fallback.

    CRITICAL RULES:
    1. **NO HALLUCINATION**: Only use columns EXPLICITLY listed in the DATABASE SCHEMA below.
    2. **Avoid Complex Subqueries**: Do NOT use complex correlated subqueries. Use simple JOINs.
    3. **Check Foreign Keys**: 
       - `admin_workflow_executions` and `execution_logs` do **NOT** have `organization_id`.
       - **CORRECT JOIN PATHS**:
         - `execution_logs` -> `workflows` (on `workflow_id`) -> `organizations` (on `organization_id`)
         - `admin_workflow_executions` -> `users` (on `executed_by` = `users.id`) -> `organizations` (on `organization_id`)
       - Use `analytics` table for direct Organization-level metrics.
    4. **JSON Handling**: Use `->>` for JSON columns.
    5. **STRICT RELEVANCE**:
       - If the User Request cannot be answered by the available Schema, return an EMPTY list of queries. 
       - DO NOT force a query. DO NOT make up tables.
    6. **FAILSAFE STRATEGY**:
       - If Query 1 is complex, ensure Query 2 and 3 are VERY SIMPLE (single table).
       - **EMAIL/USER LOOKUP**: If the user provides an email (e.g. "bob@infopercept.com"):
         - Query 1: Use full email: `WHERE email = 'bob@infopercept.com'`
         - Query 2: **MUST** use partial match on name: `WHERE email ILIKE 'bob%'` (This fixes domain mismatches).
       - **PERMUTATIONS (Query 4+)**:
         - If initial queries yield low data, try different GROUP BYs, filter by Date Range, or check related tables.
       - This ensures we always get *some* data even if the domain is wrong.

    DATABASE SCHEMA:
    {db_schema}
    
    RELEVANT TABLES:
    {relevant_tables}
    
    USER REQUEST:
    "{raw_input}"
    
    INSTRUCTIONS:
    1. Write correct PostgreSQL `SELECT` or `WITH` queries.
    2. Return valid JSON containing a list of queries.
    
    OUTPUT FORMAT:
    {{
        "queries": [
            {{ "description": "Main workflow execution logs", "sql": "SELECT ..." }},
            {{ "description": "Summary logic", "sql": "SELECT ..." }}
        ]
    }}
    """
    
    generated_queries = []
    combined_results = {}
    total_rows = 0
    
    try:
        # 1. Generate SQL
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Generate SQL queries.")
        ]
        
        # Iterative Query Loop (Max 2 retries)
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            
            # Adjust prompt based on retry
            if retry_count > 0:
                current_instruction = f"Previous queries returned only {total_rows} rows. Generate NEW queries using different permutations, broader filters, or different tables to find data."
                messages.append(HumanMessage(content=current_instruction))

            try:
                response = llm.invoke(messages)
                data = extract_json_from_text(response.content)
                
                if data and "queries" in data:
                    queries_to_run = data["queries"]
                    logger.info(f"Generated {len(queries_to_run)} queries (Attempt {retry_count + 1}).")
                    
                    # Execute SQL
                    for idx, q_obj in enumerate(queries_to_run):
                        sql = q_obj.get("sql")
                        desc = q_obj.get("description", f"Query {idx+1}")
                        
                        if not sql or sql in generated_queries: continue # Avoid duplicates
                        
                        logger.info(f"Executing Query {idx+1}: {desc}")
                        logger.info(f"Generated SQL: {sql}")
                        results = execute_read_query(sql)
                        
                        if isinstance(results, list):
                             count = len(results)
                             logger.info(f"Query {idx+1} returned {count} rows.")
                             if count > 0:
                                 combined_results[desc] = results
                                 total_rows += count
                             generated_queries.append(sql)
                        else:
                             logger.error(f"Query {idx+1} Error: {results}")

                # Check sufficiency (Goal: 50+ rows)
                if total_rows >= 50:
                    logger.info(f"Data sufficient ({total_rows} rows). Stopping query loop.")
                    break
                
                retry_count += 1
                if retry_count <= max_retries:
                    logger.info(f"Insufficient data ({total_rows} rows). Retrying with new permutations...")
                    
            except Exception as e:
                logger.error(f"Query generation failed: {e}")
                break

        if total_rows == 0:
            logger.warning("All queries returned 0 rows. Stopping workflow.")
            return {
                 "current_step": "no_analytics_data",
                 "error_message": "Database queries returned 0 results. No data available to generate presentation."
            }

        # 3. Prepare State for Planner
        # We mimic the old 'input_analysis' so planner knows to make charts
        input_analysis = {
            "input_type": "json", # Treat DB results as JSON input
            "can_create_visualizations": True, # Always true for DB data
            "visualization_types": ["BAR_CHART", "PIE_CHART", "LINE_CHART", "TABLE"],
            "extracted_topic": raw_input
        }
        
        # We put the results into 'source_json' as a string for the planner
        source_json = json.dumps(combined_results, default=str)

        return {
            "generated_sql": json.dumps(generated_queries), # Store as JSON list string
            "query_results": combined_results, # Store dict of results
            "source_json": source_json, # Compatibility with Planner
            "input_analysis": input_analysis, # Compatibility with Planner
            "topic": raw_input, # Compatibility
            "current_step": "query_complete",
            "error_message": ""
        }

    except Exception as e:
        error_msg = f"Query Agent failed: {e}"
        logger.error(error_msg, exc_info=True)
        return {"error_message": error_msg}


# --- HELPER: CHUNKING ANALYSIS ---
def analyze_large_json_in_chunks(data_str: str, chunk_size: int = 15000) -> str:
    """
    Analyzes large JSON data in chunks to extract insights without truncation.
    """
    if not data_str:
        return "No data provided."
        
    logger.info(f"Starting chunked analysis. Total size: {len(data_str)} chars.")
    
    chunks = [data_str[i:i+chunk_size] for i in range(0, len(data_str), chunk_size)]
    aggregated_insights = []
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
        prompt = f'''You are a Data Analyst. Extract key insights, trends, and specific data points from this partial dataset.
        
        DATA CHUNK:
        {chunk}
        
        OUTPUT:
        - List key metrics and values found.
        - Identify any meaningful trends.
        - valid JSON format is NOT required, just clear text notes.
        '''
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            aggregated_insights.append(f"--- CHUNK {i+1} INSIGHTS ---\n{response.content}")
        except Exception as e:
            logger.error(f"Error analyzing chunk {i+1}: {e}")
            
    return "\n\n".join(aggregated_insights)


# --- AGENT 1: PLANNER NODE (The "Analyst" Agent) ---

def planner_node(state: DeckState) -> dict:
    """
    Primary planning agent that analyzes input and creates slide structure.
    Strictly stops if no data is available.
    """
    # Circuit Breaker
    if state.get("error_message"):
        logger.warning("Skipping Planner due to previous error.")
        return {
            "slides": [],
            "error_message": state.get("error_message"),
             "current_step": "planning_failed"
        }

    topic = state.get('topic', '').strip()

    """

    Primary planning agent that analyzes input and creates slide structure.

    Uses input analysis to determine if visualizations should be created.

    Ensures minimum 4 slides are generated.

    """

    topic = state.get('topic', '').strip()

    source_json = state.get('source_json', '').strip()

    user_query = state.get('user_query', '').strip()

    input_analysis = state.get('input_analysis', {})

   

    logger.info("=== PLANNER AGENT: Starting analysis ===")
    
    # Retrieve Search Results & Existing Slides (Memory)
    search_results = state.get('search_results', '').strip()
    existing_slides = state.get('slides', [])
    is_update_request = len(existing_slides) > 0

    # Validation: Need either JSON, Topic+Search, or Topic+Memory
    # STRICT MODE: If we expected data from Query Agent but got none, FAIL.
    if not source_json and not search_results and not existing_slides:
        # Check if query agent explicitly said "no data"
        if state.get("current_step") == "no_analytics_data":
             error_msg = "Data Unavailable: Query returned no results."
        else:
             error_msg = "Correction: Data not found for request. Please provide correct input related to available database tables."
        
        logger.warning(f"Strict Mode Stopping: {error_msg}")
        return {
            "slides": [],
            "current_step": "planning_failed",
            "error_message": error_msg
        }

    # Extract requested slide count from user instructions

    # Extract requested slide count from user instructions
    import re
    slide_count_request = None
    user_instructions = state.get('user_instructions', '')
    
    # Try to find "X slides" or "X-Y slides" pattern
    # Look for explicit number followed by "slide" or "slides"
    count_match = re.search(r'(\d+)\s+slides?', user_instructions, re.IGNORECASE)
    if count_match:
        try:
            slide_count_request = int(count_match.group(1))
            logger.info(f"User requested {slide_count_request} slides.")
        except:
            pass
            
    # Default minimum if no request
    min_slides_default = 4 
    target_slides = slide_count_request if slide_count_request else min_slides_default

    # Get visualization recommendations from input analysis

    can_create_visualizations = input_analysis.get('can_create_visualizations', False)

    visualization_types = input_analysis.get('visualization_types', [])

   

    try:

        # Decide source mode: JSON vs Search vs Update
        if source_json:
            # Chunking Logic for Large Data (15k chars is safe for most 100k+ models)
            limit = 25000
            if len(source_json) > limit:
                logger.info(f"Data too large ({len(source_json)} chars). Using chunked analysis.")
                # Uses global helper function
                aggregated_insights = analyze_large_json_in_chunks(source_json)
                data_context = f"AGGREGATED DATA INSIGHTS (From Large Dataset):\n{aggregated_insights}"
            else:
                data_context = f"SOURCE DATA (JSON):\n{source_json}"
        elif search_results:
            # Search-based planning
            data_context = f"RESEARCH CONTEXT (Search Results):\\n{search_results}"
        else:
             # Just topic/instructions
             data_context = f"TOPIC CONTEXT: {topic}"

        if not user_query:
            user_query = "Create a comprehensive executive presentation." if not is_update_request else "Update the presentation based on instructions."

        vis_recommendation = "recommended" if can_create_visualizations else "not recommended"
        vis_instruction = "Prioritize charts based on data." if can_create_visualizations else "Focus on text insights."

        # Construct System Prompt with MEMORY AWARENESS
        system_prompt = f"""You are an expert Corporate Presentation Analyst.
        
        CURRENT MODE: {"UPDATE EXISTING SLIDES" if is_update_request else "CREATE NEW PRESENTATION"}
        
        USER INSTRUCTION: "{user_query}"
        
        {data_context}
        
        EXISTING SLIDES (Memory):
        {json.dumps(existing_slides, indent=2) if is_update_request else "None"}
        
        YOUR TASK:
        {"1. Modify the EXISTING SLIDES based on the User Instruction (e.g. add a slide, edit content)." if is_update_request else "1. Analyze the provided data/research and create a NEW presentation."}
        {"2. PRESERVE existing slides unless explicitly asked to change them." if is_update_request else ""}
        - USER REQUESTED: {f"Create {slide_count_request} slides." if slide_count_request else "Create a comprehensive presentation."}
        - QUALITY RULE: If the provided JSON data is insufficient to meet the requested slide count, DO NOT INVENT FACTS or repeated content just to fill the count. STOP generating slides when the data is exhausted. PRIORITIZE QUALITY OVER QUANTITY.
        
        STRATEGY 1: Data Usage
        - Use ONLY provided JSON or Research Context. Do not invent facts.
        
        STRATEGY 2: Visuals
        - Generate GRAPHS only for clear comparisons.
        - VARIANCE CHECK: No bar charts for identical values.
        
        OUTPUT SCHEMA (STRICT JSON):
        Return a JSON array of objects. Each object must follow one of these formats:
        
        1. CHART SLIDE:
        {{
            "title": "Slide Title",
            "chart_type": "BAR_CHART" | "PIE_CHART" | "LINE_CHART",
            "chart_data": {{
                "categories": ["A", "B", "C"],
                "values": [10, 20, 30],
                "series_name": "Sales"
            }},
            "description": "Bref summary. CRITICAL: Provide 3-4 sentences analyzing the trends, outliers, or key takeaways from this data. Do not just repeat the title.",
            "content": "Brief insight about the chart."
        }}
        
        2. TABLE SLIDE:
        {{
            "title": "Slide Title",
            "table_data": {{
                "columns": ["Col1", "Col2"],
                "rows": [["Row1Val1", "Row1Val2"], ["Row2Val1", "Row2Val2"]]
            }},
            "description": "Brief summary. CRITICAL: Provide 3-4 sentences summarizing the key data points and their implications.",
            "content": "Brief summary."
        }}
        
        3. TEXT SLIDE:
        {{
            "title": "Slide Title",
            "content": "CRITICAL: Output as a list of bullet points. Do NOT use paragraphs."
        }}
        
        OUTPUT:
        - Return ONLY valid JSON array of slide objects.
        """
        
        # Invoke LLM with Retry Logic
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Proceed with {'UPDATE' if is_update_request else 'CREATION'}.")
        ]
        
        max_retries = 10
        data = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Planner Agent: Generation attempt {attempt + 1}/{max_retries}")
                response = llm.invoke(messages)
                content = response.content
                
                # Extract JSON
                data = extract_json_from_text(content)
                
                if data and 'slides' in data and len(data['slides']) > 0:
                    break # Success!
                else:
                    logger.warning(f"Planner Agent: Attempt {attempt + 1} failed to produce valid slides.")
            except Exception as e:
                 logger.warning(f"Planner Agent: Attempt {attempt + 1} generated an error: {e}")
        
        slides = [] # Initialize clearly
        if not data or 'slides' not in data:
             logger.error("Planner agent: Failed to extract slides after retries.")
             # Fallback/Error handling (simplified for brevity)
             # We will proceed with empty slides list which handles the error gracefully downstream
             pass
        else:
             slides = data['slides']

        # Validate and Check Slide Count
        validated_slides = []
        for idx, slide in enumerate(slides):
            if isinstance(slide, dict) and 'title' in slide:
                # --- NEW LOGIC: Enforce Distinct Values for Bar Charts ---
                if slide.get('chart_type') == 'BAR_CHART' and 'chart_data' in slide:
                    try:
                        c_data = slide['chart_data']
                        vals = c_data.get('values', [])
                        
                        # Check if all values are identical (numerically)
                        is_identical = False
                        if vals and len(vals) > 0:
                            first_val = vals[0]
                            is_identical = all(v == first_val for v in vals)
                        
                        if is_identical:
                            logger.info(f"Slide {idx}: Converting BAR_CHART to TABLE due to identical values: {vals}")
                            
                            # Create table structure
                            categories = c_data.get('categories', [])
                            series_name = c_data.get('series_name', 'Value')
                            
                            # Build rows
                            rows = []
                            for i in range(min(len(categories), len(vals))):
                                rows.append([str(categories[i]), str(vals[i])])
                                
                            slide['table_data'] = {
                                "columns": ["Category", series_name],
                                "rows": rows
                            }
                            
                            # Remove chart data
                            del slide['chart_type']
                            del slide['chart_data']
                            
                    except Exception as e:
                        logger.warning(f"Error checking variance for slide {idx}: {e}")

                validated_slides.append(slide)

            else:

                logger.warning(f"Skipping invalid slide at index {idx}: {slide}")

       

        generation_warning = ""
        
        # Check if we met the requested count (fuzzy check, allow -1 difference)
        # Note: We use target_slides from the beginning of the function
        slide_count_request_val = slide_count_request if 'slide_count_request' in locals() and slide_count_request else None
        
        if slide_count_request_val:
            # If user requested X slides, but we got significantly fewer
            if len(validated_slides) < slide_count_request_val:
                generation_warning = f"Here is created ppt with {len(validated_slides)} number of slide but i can not generate more because of insuffiecient data "
                logger.info(f"Slide count warning: Requested {slide_count_request_val}, got {len(validated_slides)}")
        else:
            # Default warning only if very few slides
             if len(validated_slides) < 4:
                generation_warning = f"here is created ppt with {len(validated_slides)} number of slide but i can not generate more because of insuffiecient data in json typed input"

        logger.info(f"Planner agent completed successfully. Generated {len(validated_slides)} slides.")

        return {

            "slides": validated_slides,

            "current_step": "planning_complete",

            "error_message": "",
            
            "generation_warning": generation_warning

        }

       

    except Exception as e:

        error_msg = f"Planner agent error: {str(e)}"

        logger.error(error_msg, exc_info=True)

        return {

            "slides": [],

            "current_step": "planning_failed",

            "error_message": error_msg

        }



# --- AGENT 2: WRITER NODE (The "Comms Director" Agent) ---

def writer_node(state: DeckState) -> dict:

    """

    Refines slide content for executive audience.

    Focuses ONLY on text content refinement.

    """

    logger.info("=== WRITER AGENT: Refining content ===")
    slides = state.get('slides', [])
    if not slides:

        return {

            "current_step": "writer_failed",

            "error_message": "No slides to refine"

        }


   

    logger.info(f"Writer agent processing {len(slides)} slides")

   

    return {

        "slides": slides,

        "current_step": "writing_complete",

        "error_message": ""

    }



# --- AGENT 3: VALIDATOR NODE (The "Quality Assurance" Agent) ---

def validator_node(state: DeckState) -> dict:

    """

    Validates the slide structure and content.

    Ensures JSON schema compliance and content safety.

    """

    logger.info("=== VALIDATOR AGENT: Checking Quality ===")

    slides = state.get('slides', [])

   

    if not slides:

        error_msg = "No slides generated to validate"

        logger.error(error_msg)

        return {

            "current_step": "validation_failed",

            "error_message": error_msg

        }

   

    if len(slides) < 4:

        # No longer a hard fail, just a log, because we support user-driven counts now
        logger.warning(f"Validation warning: Only {len(slides)} slides. Minimum 6 usually recommended.")

   

    # Validate each slide structure

    validated_slides = []

    errors = []

   

    for idx, slide in enumerate(slides):

        if not isinstance(slide, dict):

            errors.append(f"Slide {idx + 1}: Not a dictionary")

            continue

       

        if 'title' not in slide or not slide['title']:

            errors.append(f"Slide {idx + 1}: Missing or empty title")

            continue

       

        # Check for required content based on slide type

        has_content = 'content' in slide and slide.get('content')

        has_chart = 'chart_type' in slide and 'chart_data' in slide

        has_table = 'table_data' in slide and slide.get('table_data')

       

        if not (has_content or has_chart or has_table):

            errors.append(f"Slide {idx + 1} ('{slide.get('title')}'): Missing content, chart, or table")

            continue

       

        # Validate chart data if present

        if has_chart:

            chart_data = slide.get('chart_data', {})

            if not chart_data.get('categories') or not chart_data.get('values'):

                errors.append(f"Slide {idx + 1} ('{slide.get('title')}'): Invalid chart data")

                continue

       

        # Validate table data if present

        if has_table:

            table_data = slide.get('table_data', {})

            if not table_data.get('columns') or not table_data.get('rows'):

                errors.append(f"Slide {idx + 1} ('{slide.get('title')}'): Invalid table data")

                continue

       

        validated_slides.append(slide)

   

    if errors:

        error_msg = f"Validation errors found: {'; '.join(errors)}"

        logger.warning(error_msg)

        # Continue with validated slides if we have at least 1
        if len(validated_slides) >= 1:
            logger.info(f"Proceeding with {len(validated_slides)} validated slides despite warnings")
        else:
            logger.error(f"Only {len(validated_slides)} valid slides. Cannot proceed.")

            return {

                "slides": validated_slides,

                "current_step": "validation_failed",

                "error_message": error_msg

            }

   

    logger.info(f"Validator agent completed. {len(validated_slides)} slides validated.")

    return {

        "slides": validated_slides,

        "current_step": "validation_complete",

        "error_message": ""

    }



# --- BUILD GRAPH WITH CONDITIONAL EDGES ---

# --- BUILD GRAPH WITH NEW DB AGENTS ---

workflow = StateGraph(DeckState)

# Add nodes
workflow.add_node("searching_schema", searching_schema_node)
workflow.add_node("query_agent", query_agent_node)
workflow.add_node("planner", planner_node)
workflow.add_node("writer", writer_node)
workflow.add_node("validator", validator_node)
workflow.add_node("visualization_builder", visualization_builder_node)
workflow.add_node("content_builder", content_builder_node)

# Set entry point
workflow.set_entry_point("searching_schema")

# Add edges (Linear Flow for DB)
# Add edges (Linear Flow for DB)
workflow.add_edge("searching_schema", "query_agent")
workflow.add_edge("query_agent", "planner")

# Conditional Edges from Planner onwards (Same as before)
def should_continue_to_writer(state: DeckState) -> str:
    """Check if planning was successful."""
    if state.get("current_step") == "planning_complete" and len(state.get("slides", [])) > 0:
        return "writer"
    return END

def should_continue_to_validator(state: DeckState) -> str:
    """Check if writing was successful."""
    slides = state.get("slides", [])
    if len(slides) > 0:
        return "validator"
    return END

def should_continue_to_visualization_builder(state: DeckState) -> str:
    """Check if validation was successful."""
    if state.get("current_step") == "validation_complete":
        slides = state.get("slides", [])
        if len(slides) >= 1: # Validation threshold relaxed
            return "visualization_builder"
    return END

def should_continue_to_content_builder(state: DeckState) -> str:
    """Check if visualization builder was successful."""
    if state.get("current_step") == "visualization_build_complete":
        return "content_builder"
    return END

workflow.add_conditional_edges("planner", should_continue_to_writer)
workflow.add_edge("writer", "validator")
workflow.add_conditional_edges("validator", should_continue_to_visualization_builder)
workflow.add_conditional_edges("visualization_builder", should_continue_to_content_builder)
workflow.add_edge("content_builder", END)

# Compile with Memory
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


logger.info("Workflow graph compiled successfully with DB Agents")
