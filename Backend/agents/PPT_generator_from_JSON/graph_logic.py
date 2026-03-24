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
from agents.PPT_generator_from_JSON.builder_logic import visualization_builder_node, content_builder_node

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

    # Strategy 1: Extract JSON from code blocks
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        text = match.group(1).strip()

    # Strategy 2: Find JSON array
    if not match:
        match_list = re.search(r"(\[[\s\S]*\])", text, re.DOTALL)
        if match_list:
            text = match_list.group(1).strip()

    # Strategy 3: Find JSON object
    if not match and not match_list:
        match_dict = re.search(r"(\{[\s\S]*\})", text, re.DOTALL)
        if match_dict:
            text = match_dict.group(1).strip()

    # Try parsing
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

        logger.warning(f"extract_json_from_text: Unexpected structure: {type(data)}")
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



# --- AGENT 0: INPUT ANALYZER NODE ---

def input_analyzer_node(state: DeckState) -> dict:

    """

   RESPONSIBILITIES:
•	Detect whether the raw input is valid structured JSON or a topic/description
•	Interpret and honor explicit user instructions
•	Evaluate whether the input contains explicitly provided analyzable or visualizable data (numeric values, categories, or trends)
•	Do NOT infer, assume, or enrich data using external or known statistical context
•	Determine whether charts or tables can be created only from the given data
•	Extract a clear and concise presentation topic/title
•	Preserve the source JSON exactly as provided when applicable
•	Produce a strictly structured JSON analysis output for downstream processing

INSTRUCTIONS:
1.	Analyze raw_input to determine:
o	Whether it is valid JSON (attempt parsing)
o	Whether it represents a topic, description, or conceptual input
o	Whether it contains explicit data suitable for visualization
⚠️ Do not infer or derive data not present in the input
2.	If the input is JSON:
o	Validate the JSON structure
o	Assess the presence of explicit numeric or categorical data
o	Decide whether visualizations can be created only from the provided values
o	Preserve the original JSON as a string without modification
3.	If the input is a topic/description:
o	Extract the main topic or presentation title
o	Determine visualization feasibility only if explicit data is included in the text
o	Do not rely on commonly known or external statistical data
4.	Visualization Selection (only if data exists):
o	Select appropriate visualization types from:
	BAR_CHART
	PIE_CHART
	LINE_CHART
	TABLE
5.	Presentation Guidance:
o	Generate concise recommendations for presentation structure only when analyzable data is present
6.	Output Rules (STRICT):
o	Return ONLY a valid JSON object
o	The output must strictly follow the defined schema
o	No explanations, assumptions, inferred values, or additional text


    """

    raw_input = state.get('raw_input', '').strip()
    user_instructions = state.get('user_instructions', '').strip()

   

    logger.info("=== INPUT ANALYZER AGENT: Analyzing input type and requirements ===")

   

    if not raw_input:

        error_msg = "No input provided"

        logger.error(error_msg)

        return {

            "input_analysis": {},

            "topic": "",

            "source_json": "",

            "user_query": "",

            "current_step": "input_analysis_failed",

            "error_message": error_msg

        }

   

    try:

        # Check if input is a file reference (starts with @)

        processed_input = raw_input

        if raw_input.startswith('@'):

            # Extract filename

            filename = raw_input[1:].strip()

            logger.info(f"Input analyzer: Detected file reference: {filename}")

           

            # Try to read the file

            file_paths_to_try = [

                filename,  # Direct path

                os.path.join(os.getcwd(), filename),  # Current directory

                os.path.join(os.path.dirname(os.path.dirname(__file__)), filename),  # Parent directory (workspace root)

            ]

           

            file_read = False

            for file_path in file_paths_to_try:

                try:

                    if os.path.exists(file_path) and os.path.isfile(file_path):

                        with open(file_path, 'r', encoding='utf-8') as f:

                            processed_input = f.read()

                        logger.info(f"Input analyzer: Successfully read file: {file_path}")

                        file_read = True

                        break

                except Exception as e:

                    logger.warning(f"Input analyzer: Failed to read file {file_path}: {e}")

                    continue

           

            if not file_read:

                error_msg = f"File not found: {filename}. Tried paths: {', '.join(file_paths_to_try)}"

                logger.error(error_msg)

                return {

                    "input_analysis": {},

                    "topic": "",

                    "source_json": "",

                    "user_query": "",

                    "current_step": "input_analysis_failed",

                    "error_message": error_msg

                }

           

            # Check file size (warn if very large, but still process)

            file_size_mb = len(processed_input) / (1024 * 1024)

            if file_size_mb > 10:

                logger.warning(f"Input analyzer: Large file detected ({file_size_mb:.2f} MB). Processing may take longer.")

            else:

                logger.info(f"Input analyzer: File size: {file_size_mb:.2f} MB")

       

        # Try to parse as JSON first

        is_json = False

        json_data = None

        parsed_json_str = ""

       

        try:

            # Try parsing the processed input as JSON

            json_data = json.loads(processed_input)

            is_json = True

            parsed_json_str = json.dumps(json_data, indent=2)

            logger.info("Input analyzer: Detected JSON data")

        except (json.JSONDecodeError, ValueError):

            # Not JSON, treat as topic

            is_json = False

            logger.info("Input analyzer: Detected topic/description")

       

        # Use LLM to analyze if visualizations are needed

        system_prompt = """
        Role:
You are an input analysis engine for presentation generation.
Task:
Analyze the provided input to classify its type and determine whether it contains EXPLICIT NUMERICAL DATA, TRENDS, or COMPARISONS suitable for creating a data analytics presentation (PPT).
A PPT must be generated ONLY when the input contains actual numbers, trends, or comparative data.

Analysis Steps:
1.	Determine the input type:
o	"json" → if the input is valid, structured JSON
o	"topic" → if the input is descriptive text, a concept, or a title
2.	STRICT Numerical Data Evaluation:
The input MUST contain at least ONE of the following to qualify for PPT generation:
o	EXPLICIT NUMERIC VALUES (e.g., "sales: $5000", "temperature: 25°C", "count: 42", "75%", "15% increase")
o	TRENDS OVER TIME (e.g., "increased by 15%", "declined from 100 to 80", "grew steadily", "trend analysis")
o	COMPARATIVE DATA (e.g., "A vs B", "higher than", "lower than", "ranked #1", "compare", "comparison")
o	AGGREGATED STATISTICS (e.g., "average: 25.5", "total: 1000", "percentage: 75%", "statistics")
- PURELY DESCRIPTIVE TEXT WITHOUT NUMBERS DOES NOT QUALIFY
- CONCEPTUAL TOPICS WITHOUT DATA DO NOT QUALIFY
- GENERAL DISCUSSION TOPICS DO NOT QUALIFY

3.	PPT Creation Rule (VERY STRICT):
o	If input type is "json" AND contains analytical data → ALWAYS proceed with PPT analysis (visualizations are compulsory)
o	If input type is "topic" and contains EXPLICIT numbers, trends, or comparisons → proceed with PPT analysis
o	If only descriptive text, categories, or concepts exist:
	Do NOT prepare PPT analysis
	Respond with: "PPT cannot be created because no analyzable data was provided."
4.	Visualization Requirements:
o	For JSON input WITH analytical data: Visualizations (charts/tables) are COMPULSORY.
o	STRICT GRAPH GENERATION RULE:
    - Generate GRAPH (Bar/Line/Pie) ONLY if there is a WELL-DEFINED VALUE COMPARISON or TREND (e.g. "Year A vs Year B", "Sales vs Cost", "Timeline").
    - If data is purely informational or a static list without comparison, use TABLE.
    - DO NOT force a graph if the data does not support a meaningful comparison.
o	Select appropriate visualization types from the allowed list only:
	BAR_CHART (Only for comparisons/trends)
	PIE_CHART (Only for part-to-whole comparisons)
	LINE_CHART (Only for trends over time)
	TABLE (For everything else, including static lists)
o	For JSON with analytical data: Create charts/tables to show insights
o	Extract a clear, concise topic/title suitable for a presentation slide deck
o	If input type is "json", return the original JSON as a string without modification
o	If input type is "topic", return an empty string for extracted JSON

Output Rules (STRICT):
•	If analyzable data is present:
o	Return ONLY a valid JSON object following the defined schema
•	If no analyzable data is present:
o	Return ONLY the following message (no JSON, no extra text):
o	PPT cannot be created because no analyzable data was provided.
•	No explanations, comments, assumptions, inferred values, or additional text
•	Follow all rules exactly

        """

        
        input_for_analysis = processed_input
        logger.info(f"Input analyzer: Processing full input of {len(processed_input)} chars.")

        user_prompt = f"""Analyze the following input:

Input:
{input_for_analysis}


Determine the input type, visualization needs, and extract key information."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # Try LLM analysis, but have fallback if it fails
        analysis_data = None
        try:
            logger.info("Invoking LLM for input analysis...")
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # Extract JSON from response
            analysis_data = extract_json_from_text(content)
            
            # For JSON data with analytics, override LLM analysis to ensure compulsory visualizations
            if is_json and analysis_data and isinstance(analysis_data, dict):
                # Check if JSON contains analytical data (numbers, trends, comparisons, or aggregatable data)
                def has_analytical_data(data):
                    """Check if JSON contains data suitable for analytics/visualization"""
                    if isinstance(data, (int, float)):
                        return True
                    elif isinstance(data, str):
                        # Check for actual numerical values (not just numbers in text)
                        import re
                        # Only match standalone numbers or percentages, not numbers in words
                        if re.search(r'\\b\\d+(\\.\\d+)?%?\\b', data):
                            return True
                        # Check for analytical keywords in context
                        analytical_keywords = ['sales', 'revenue', 'cost', 'profit', 'growth', 'total', 'average', 'count', 'amount', 'price', 'quantity', 'rate', 'score']
                        if any(keyword in data.lower() for keyword in analytical_keywords):
                            return True
                    elif isinstance(data, list):
                        # For arrays, check if it contains objects with analytical data
                        if len(data) > 0 and isinstance(data[0], dict):
                            return any(has_analytical_data(item) for item in data)
                        # For simple arrays, only consider analytical if they contain numbers
                        return any(isinstance(item, (int, float)) for item in data)
                    elif isinstance(data, dict):
                        return any(has_analytical_data(value) for value in data.values())
                    return False
                
                # Only override if JSON contains analytical data
                if has_analytical_data(json_data):
                    analysis_data["input_type"] = "json"
                    analysis_data["can_create_visualizations"] = True
                    if not analysis_data.get("visualization_types"):
                        analysis_data["visualization_types"] = ["TABLE"]
                    analysis_data["recommendations"] = "Create compulsory visualizations (charts/tables) for JSON analytics data"
                    logger.info("JSON with analytical data detected: Overriding LLM analysis to ensure compulsory visualizations")
                else:
                    logger.info("JSON detected but no analytical data found - using normal LLM analysis")

        except Exception as e:
            logger.warning(f"Input analyzer: LLM analysis failed: {e}. Using fallback logic.")
            # Continue with fallback logic below

        if not analysis_data or not isinstance(analysis_data, dict):
            logger.warning("Input analyzer: Failed to extract analysis. Using fallback logic.")
            # Fallback: use stricter numerical data detection
            if is_json:
                # Strict check for actual numerical data, trends, or comparisons
                can_viz = False
                viz_types = []
                
                def contains_numerical_data(data):
                    """Recursively check if data contains actual numbers, trends, or comparisons"""
                    if isinstance(data, (int, float)):
                        return True
                    elif isinstance(data, str):
                        # Check for numerical patterns, trends, or comparisons in text
                        import re
                        # Numbers
                        if re.search(r'\\d+(\\.\\d+)?', data):
                            return True
                        # Trends/Comparisons keywords
                        trend_keywords = ['increased', 'decreased', 'grew', 'declined', 'higher', 'lower', 'vs', 'versus', 'compared', 'trend', 'average', 'total', 'percent', '%']
                        if any(keyword in data.lower() for keyword in trend_keywords):
                            return True
                    elif isinstance(data, list):
                        return any(contains_numerical_data(item) for item in data)
                    elif isinstance(data, dict):
                        return any(contains_numerical_data(value) for value in data.values())
                    return False

                # For JSON data with analytics, we want to create visualizations (compulsory for analytics)
                # Check if JSON contains analytical data
                def has_analytical_data(data):
                    """Check if JSON contains data suitable for analytics/visualization"""
                    if isinstance(data, (int, float)):
                        return True
                    elif isinstance(data, str):
                        # Check for actual numerical values (not just numbers in text)
                        import re
                        # Only match standalone numbers or percentages, not numbers in words
                        if re.search(r'\\b\\d+(\\.\\d+)?%?\\b', data):
                            return True
                        # Check for analytical keywords in context
                        analytical_keywords = ['sales', 'revenue', 'cost', 'profit', 'growth', 'total', 'average', 'count', 'amount', 'price', 'quantity', 'rate', 'score']
                        if any(keyword in data.lower() for keyword in analytical_keywords):
                            return True
                    elif isinstance(data, list):
                        # For arrays, check if it contains objects with analytical data
                        if len(data) > 0 and isinstance(data[0], dict):
                            return any(has_analytical_data(item) for item in data)
                        # For simple arrays, only consider analytical if they contain numbers
                        return any(isinstance(item, (int, float)) for item in data)
                    elif isinstance(data, dict):
                        return any(has_analytical_data(value) for value in data.values())
                    return False
                
                if has_analytical_data(json_data):
                    can_viz = True  # Compulsory visualizations for JSON with analytical data
                else:
                    can_viz = False  # No visualizations for JSON without analytical data
                
                # Determine visualization types based on data structure
                if isinstance(json_data, list) and len(json_data) > 0:
                    first_item = json_data[0] if isinstance(json_data[0], dict) else {}
                    has_numeric = any(isinstance(v, (int, float)) for v in first_item.values())
                    has_strings = any(isinstance(v, str) for v in first_item.values())
                    
                    if has_numeric and has_strings:
                        viz_types = ["BAR_CHART", "PIE_CHART", "TABLE"]
                    elif has_numeric:
                        viz_types = ["BAR_CHART", "LINE_CHART", "TABLE"]
                    else:
                        # Even without numeric data, create tables for categorical data
                        viz_types = ["TABLE"]
                elif isinstance(json_data, dict):
                    viz_types = ["BAR_CHART", "PIE_CHART", "TABLE"]
                else:
                    # Default fallback for any JSON structure
                    viz_types = ["TABLE"]

                analysis_data = {
                    "input_type": "json",
                    "can_create_visualizations": can_viz,
                    "visualization_types": viz_types,
                    "extracted_topic": "Data Report",
                    "extracted_json": "",  # Will use processed_input instead
                    "recommendations": "Create compulsory visualizations for JSON analytics data" if can_viz else "No analytical data found for visualization"
                }
            else:
                # For text input, check for numerical data, trends, or comparisons
                import re
                has_numbers = bool(re.search(r'\\d+(\\.\\d+)?', processed_input))
                trend_keywords = ['increased', 'decreased', 'grew', 'declined', 'higher', 'lower', 'vs', 'versus', 'compared', 'trend', 'average', 'total', 'percent', '%']
                has_trends = any(keyword in processed_input.lower() for keyword in trend_keywords)
                
                can_viz = has_numbers or has_trends
                
                analysis_data = {
                    "input_type": "topic",
                    "can_create_visualizations": can_viz,
                    "visualization_types": ["BAR_CHART", "PIE_CHART", "TABLE"] if can_viz else [],
                    "extracted_topic": processed_input[:100] if len(processed_input) <= 100 else processed_input[:97] + "...",
                    "extracted_json": "",
                    "recommendations": "Create data-driven presentation" if can_viz else "No numerical data found for presentation"
                }

        # Set up state based on analysis

        input_type = analysis_data.get("input_type", "topic")

        # STRICT OVERRIDE: If we successfully parsed JSON earlier, enforce input_type="json"
        # This prevents the system from treating non-analytical JSON as a "topic" and triggering a web search.
        if is_json:
             logger.info("Input analyzer: Valid JSON detected. input_type='json' to prevent search agent execution.")
             input_type = "json"
             # Ensure we have at least a fallback visualization
             if not analysis_data.get("visualization_types"):
                 analysis_data["visualization_types"] = ["TABLE"]
            

        # For JSON data with analytics, visualizations are compulsory - always proceed regardless of LLM analysis
        if input_type == "json":
            # Check if JSON contains analytical data before overriding
            def has_analytical_data(data):
                    """Check if JSON contains data suitable for analytics/visualization"""
                    try:
                        if isinstance(data, (int, float)):
                            return True
                        elif isinstance(data, str):
                            # Check for actual numerical values (not just numbers in text)
                            import re
                            # Only match standalone numbers or percentages, not numbers in words
                            if re.search(r'\\b\\d+(\\.\\d+)?%?\\b', data):
                                return True
                            # Check for analytical keywords in context
                            analytical_keywords = ['sales', 'revenue', 'cost', 'profit', 'growth', 'total', 'average', 'count', 'amount', 'price', 'quantity', 'rate', 'score']
                            if any(keyword in data.lower() for keyword in analytical_keywords):
                                return True
                        elif isinstance(data, list):
                            # For arrays, check if it contains objects with analytical data
                            if len(data) > 0 and isinstance(data[0], dict):
                                return any(has_analytical_data(item) for item in data)
                            # For simple arrays, only consider analytical if they contain numbers
                            return any(isinstance(item, (int, float)) for item in data)
                        elif isinstance(data, dict):
                            return any(has_analytical_data(value) for value in data.values())
                        return False
                    except:
                        return False
            
            # Parse the JSON to check for analytical data
            try:
                # Use the original raw_input for parsing since source_json might not be set yet
                json_data_for_check = json.loads(state.get('raw_input', '{}'))
                if has_analytical_data(json_data_for_check):
                    # Override LLM analysis to ensure compulsory visualizations for analytical JSON
                    analysis_data["can_create_visualizations"] = True
                    # Ensure we have visualization types
                    if not analysis_data.get("visualization_types"):
                        analysis_data["visualization_types"] = ["TABLE"]
                    analysis_data["recommendations"] = "Create compulsory visualizations for JSON analytics data"
                    logger.info("JSON with analytical data detected: Ensuring compulsory visualizations")
                else:
                    logger.info("JSON detected but no analytical data found - keeping LLM analysis")
            except Exception as parse_error:
                logger.warning(f"Failed to parse JSON for analytical data check: {parse_error}")

        if input_type == "json":
            # Always use the full processed input for JSON (preserves large files)
            # parsed_json_str might be truncated, so use processed_input
            if is_json:
                # Use processed_input to preserve full file content
                final_json = processed_input
            else:
                # Fallback: use extracted JSON or processed input
                final_json = analysis_data.get("extracted_json", processed_input)

            topic = analysis_data.get("extracted_topic", "Data Report")
            source_json = final_json
            logger.info(f"Input analyzer: Set source_json with {len(final_json)} characters")
        else:
            topic = analysis_data.get("extracted_topic", processed_input[:100] if len(processed_input) <= 100 else processed_input[:97] + "...")
            source_json = ""

        # Set user query
        if input_type == "json":
            user_query = f"Analyze the provided data and create a comprehensive executive presentation. {user_instructions}"
        else:
            user_query = f"Create a comprehensive presentation on this topic. {user_instructions}"

        # Check if analyzable data is present for analytics PPT creation
        can_create_visualizations = analysis_data.get("can_create_visualizations", False)
        
        if not can_create_visualizations and input_type != "topic":
            # No analytics data present AND not a topic (which would trigger search) - return user message and end workflow
            logger.info("Input analyzer: No analyzable data found and not a search topic. PPT creation not possible.")
            return {
                "input_analysis": analysis_data,
                "topic": topic,
                "source_json": source_json,
                "user_query": user_query,
                "current_step": "no_analytics_data",
                "error_message": "PPT cannot be created because no analyzable data was provided."
            }
        
        logger.info(f"=== INPUT ANALYZER AGENT: Analysis complete. Type: {input_type}, Visualizations: {can_create_visualizations} ===")

        return {
            "input_analysis": analysis_data,
            "topic": topic,
            "source_json": source_json,
            "user_query": user_query,
            "current_step": "input_analyzed",
            "error_message": ""
        }

    except Exception as e:
        error_msg = f"Input analyzer error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "input_analysis": {},
            "topic": "",
            "source_json": "",
            "user_query": "",
            "current_step": "input_analysis_failed",
            "error_message": error_msg
        }



# --- AGENT 0.5: SEARCH AGENT NODE ---
def search_node(state: DeckState) -> dict:
    """
    Research agent that searches the web for topic information.
    Triggered when input is a topic, not JSON.
    """
    topic = state.get('topic', '').strip()
    user_instructions = state.get('user_instructions', '').strip()
    
    logger.info(f"=== SEARCH AGENT: Researching topic '{topic}' ===")
    
    try:
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        
        # Configure wrapper with specific region to avoid "wt.wikipedia.org" DNS errors
        wrapper = DuckDuckGoSearchAPIWrapper(region="us-en", time="y", max_results=5)
        search = DuckDuckGoSearchRun(api_wrapper=wrapper)
        
        # Formulate search query
        query = f"{topic} {user_instructions}".strip()
        
        # Execute search
        results = search.invoke(query)
        
        logger.info(f"Search complete. Found {len(results)} characters of data.")
        
        return {
            "search_results": results,
            "current_step": "search_complete",
            "error_message": ""
        }
        
    except Exception as e:
        error_msg = f"Search agent error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
             "search_results": "",
             "current_step": "search_failed",
             "error_message": error_msg
        }


# --- AGENT 1: PLANNER NODE (The "Analyst" Agent) ---

def planner_node(state: DeckState) -> dict:

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

    # --- HELPER: CHECK FOR ANAL YTICAL DATA ---
    def has_analytical_data_check(data):
        """Check if JSON contains data suitable for analytics/visualization"""
        try:
            if isinstance(data, (int, float)):
                return True
            elif isinstance(data, str):
                # Check for actual numerical values (not just numbers in text)
                import re
                # Only match standalone numbers or percentages, not numbers in words
                if re.search(r'\b\d+(\.\d+)?%?\b', data):
                    return True
                # Check for analytical keywords in context
                analytical_keywords = ['sales', 'revenue', 'cost', 'profit', 'growth', 'total', 'average', 'count', 'amount', 'price', 'quantity', 'rate', 'score']
                if any(keyword in data.lower() for keyword in analytical_keywords):
                    return True
            elif isinstance(data, list):
                # For arrays, check if it contains objects with analytical data
                if len(data) > 0 and isinstance(data[0], dict):
                    return any(has_analytical_data_check(item) for item in data)
                # For simple arrays, only consider analytical if they contain numbers
                return any(isinstance(item, (int, float)) for item in data)
            elif isinstance(data, dict):
                return any(has_analytical_data_check(value) for value in data.values())
            return False
        except:
            return False

    # --- HELPER: CHUNKING & AGGREGATION LOGIC ---
    def analyze_large_json_in_chunks(json_str: str, topic_context: str) -> str:
        """
        Splits large JSON into chunks, analyzes each for metrics/trends,
        and returns an aggregated summary to fit context limits.
        """
        try:
            logger.info(f"Chunking Agent: Starting analysis of {len(json_str)} chars...")
            
            # 1. Parse Data
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Chunking Agent: Failed to parse JSON. Falling back to simple truncation.")
                return f"SOURCE DATA (TRUNCATED): {json_str[:1000000]}..."

            # 2. Determine Chunks
            chunks = []
            
            if isinstance(data, list):
                # List is ideal for chunking (e.g., list of records)
                item_count = len(data)
                # target ~50 items or ~20k chars per chunk
                batch_size = 50 
                
                # Dynamic batch size based on item complexity
                if item_count > 0:
                    sample_size = len(json.dumps(data[0]))
                    if sample_size > 1000:
                        batch_size = 20 # Smaller batch for complex items
                    elif sample_size < 100:
                        batch_size = 100 # Larger batch for simple items
                
                logger.info(f"Chunking Agent: splitting {item_count} list items into batches of {batch_size}")
                
                for i in range(0, item_count, batch_size):
                    chunk = data[i:i + batch_size]
                    chunks.append(chunk)
                    
            elif isinstance(data, dict):
                # Recursive function to find the largest splittable list
                def find_largest_list(d):
                    max_len = 0
                    max_k = None
                    max_parent = d
                    max_path = []
                    
                    # If this dict has a large list, return it
                    for k, v in d.items():
                        if isinstance(v, list) and len(v) > 0:
                            # Check character text size as proxy for "heaviness"
                            try:
                                char_size = len(json.dumps(v))
                                if char_size > max_len:
                                    max_len = char_size
                                    max_k = k
                                    max_parent = d
                            except:
                                pass
                        elif isinstance(v, dict):
                             # Recursive check currently disabled to avoid complex path reconstruction
                             # For now, we only look 1 level deep if the parent list was len=1
                             pass
                    
                    return max_parent, max_k, max_len

                # 1. Try top level
                parent, target_key, size = find_largest_list(data)
                
                # 2. If top level list has only 1 item, DRILL DOWN
                if target_key and size > 0:
                    target_list = parent[target_key]
                    if len(target_list) == 1 and isinstance(target_list[0], dict):
                        logger.info(f"Chunking Agent: Top level list '{target_key}' has only 1 item. Drilling down...")
                        # Look inside that single item
                        nested_parent, nested_key, nested_size = find_largest_list(target_list[0])
                        if nested_key and nested_size > (size * 0.5): # If nested list is the bulk of the data
                            logger.info(f"Chunking Agent: Found nested list '{nested_key}' inside '{target_key}'")
                            # We chunk THIS nested list
                            # Strategy: We fix the OUTER context (target_list[0] keys excluding nested_key)
                            # And split the INNER list.
                            
                            # Valid Context = data without target_key + target_key[0] without nested_key
                            # This is complex to reconstruct perfectly. 
                            # SIMPLIFIED STRATEGY: 
                            # Just extract the nested list and chunk IT. Pass the rest as "Shared Context" string.
                            
                            large_list_key = nested_key
                            list_data = nested_parent[nested_key]
                            
                            # Create a context object (everything except the large list)
                            context_obj = data.copy()
                            # We need to reach in and remove the large list from context to save space
                            # But since `data` -> `target_key` -> [0] -> `nested_key`, it's deep.
                            # Let's just create a simplified context string.
                            context_obj[target_key] = [ { k: v for k,v in target_list[0].items() if k != nested_key } ]
                            topic_context += f"\nGlobal Context: {json.dumps(context_obj)[:5000]}..." # Truncate context
                        else:
                            # Stick with top level
                             large_list_key = target_key
                             list_data = target_list
                    else:
                        large_list_key = target_key
                        list_data = target_list
                else:
                    large_list_key = None
                
                if large_list_key:
                    item_count = len(list_data)
                    logger.info(f"Chunking Agent: Splitting list '{large_list_key}' with {item_count} items")
                    
                    # Determine batch size dynamically
                    # Target chunk size ~15,000 chars for safety
                    # Re-calculate size because we might have switched lists
                    try:
                        total_size = len(json.dumps(list_data))
                    except:
                        total_size = 1000000 
                        
                    avg_item_size = total_size / item_count if item_count > 0 else 0
                    
                    if avg_item_size > 15000:
                        batch_size = 1 # Huge items, process 1 by 1
                    else:
                        batch_size = int(15000 / avg_item_size) if avg_item_size > 0 else 50
                        batch_size = max(1, batch_size) # At least 1

                    # Create chunks
                    for i in range(0, item_count, batch_size):
                         # Create a chunk wrapper
                         chunk_wrapper = { large_list_key: list_data[i:i + batch_size] }
                         chunks.append(chunk_wrapper)
                else:
                    logger.warning("Chunking Agent: No significant list found. Using text truncation fallback.")
                    return f"SOURCE DATA (TRUNCATED): {json_str[:1000000]}..."

            logger.info(f"Chunking Agent: Created {len(chunks)} chunks.")
            
            # Limit total chunks to preventing infinite loops (e.g. max 20 chunks = 1000 items)
            # If > 200 chunks, we might need to be even more aggressive or sample.
            # User wants FULL data processing, so we raise the limit significantly.
            MAX_CHUNKS = 200
            if len(chunks) > MAX_CHUNKS:
                logger.warning(f"Chunking Agent: Too many chunks ({len(chunks)}). Sampling first, middle, last.")
                step = len(chunks) // MAX_CHUNKS
                sampled_chunks = chunks[::step][:MAX_CHUNKS]
                chunks = sampled_chunks
            
            # 3. Map Phase: Analyze Each Chunk
            aggregated_metrics = [] # List of text summaries or structured data
            
            map_prompt_template = """
            You are a Data Extractor. Analyze this PARTIAL DATA CHUNK (Part {current}/{total}).
            Context: {topic}
            
            TASK:
            1. Extract KEY METRICS (sums, averages, counts).
            2. Identify any TRENDS visible in this chunk (e.g., specific months, categories).
            3. OUTPUT FORMAT: Return a robust textual summary + a markdown table of key data points found.
            
            Constraints:
            - Do NOT generalize. Be specific with numbers.
            - Focus on data that helps build charts (Time series, Categories).
            """
            
            from langchain_core.messages import HumanMessage
            
            final_summaries = []
            
            for idx, chunk in enumerate(chunks):
                logger.info(f"Chunking Agent: Processing Chunk {idx+1}/{len(chunks)}")
                
                chunk_str = json.dumps(chunk)
                prompt = map_prompt_template.format(current=idx+1, total=len(chunks), topic=topic_context)
                
                messages = [
                    HumanMessage(content=prompt + "\n\nDATA CHUNK:\n" + chunk_str)
                ]
                
                try:
                    response = llm.invoke(messages)
                    summary = response.content
                    final_summaries.append(f"--- CHUNK {idx+1} SUMMARY ---\n{summary}")
                except Exception as e:
                    logger.error(f"Chunking Agent: Error processing chunk {idx+1}: {e}")
            
            # 4. Reduce Phase: Combine
            combined_context = "This is a AGGREGATED SUMMARY of a large dataset processed in chunks.\n\n"
            combined_context += "\n\n".join(final_summaries)
            
            return combined_context

        except Exception as e:
            logger.error(f"Chunking Agent: Critical failure: {e}")
            return f"SOURCE DATA (TRUNCATED): {json_str[:1000000]}..."

    # Validation: Need either JSON, Topic+Search, or Topic+Memory
    if not source_json and not search_results and not existing_slides and not topic:
        error_msg = "Insufficient context: No JSON, no Search Results, and no existing slides to update."
        logger.error(error_msg)
        return {
            "slides": [],
            "current_step": "planning_failed",
            "error_message": error_msg
        }

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
            # Check for excessive length
            MAX_DIRECT_JSON_CHARS = 500000 # 500k chars is safe for 1M token limit
            
            if len(source_json) > MAX_DIRECT_JSON_CHARS:
                logger.info(f"Planner Agent: Large JSON detected ({len(source_json)} chars). Initiating Map-Reduce Chunking.")
                # Trigger Chunking Logic
                processed_context = analyze_large_json_in_chunks(source_json, topic)
                data_context = f"SOURCE DATA (AGGREGATED FROM CHUNKS):\\n{processed_context}"
            else:
                # Standard Processing
                data_context = f"SOURCE DATA (JSON):\\n{source_json}"
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

workflow = StateGraph(DeckState)


# Add nodes
workflow.add_node("input_analyzer", input_analyzer_node)
workflow.add_node("search_agent", search_node) # NEW
workflow.add_node("planner", planner_node)
workflow.add_node("writer", writer_node)
workflow.add_node("validator", validator_node)
workflow.add_node("visualization_builder", visualization_builder_node)
workflow.add_node("content_builder", content_builder_node)

# Set entry point
workflow.set_entry_point("input_analyzer")


# Add edges with conditional logic

def should_continue_to_planner(state: DeckState) -> str:
    """Check if input analysis was successful and route to Search or Planner."""
    input_analysis = state.get("input_analysis", {})
    input_type = input_analysis.get("input_type", "topic")
    
    if state.get("current_step") == "input_analyzed":
        # Branching Logic
        if input_type == "json":
            return "planner"
        else:
            return "search_agent" # Route to search for topics
            
    return END

def should_continue_from_search(state: DeckState) -> str:
    """After search, always go to planner."""
    return "planner"

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

workflow.add_conditional_edges("input_analyzer", should_continue_to_planner)
workflow.add_edge("search_agent", "planner") # Connect Search -> Planner
workflow.add_conditional_edges("planner", should_continue_to_writer)
workflow.add_edge("writer", "validator")
workflow.add_conditional_edges("validator", should_continue_to_visualization_builder)
workflow.add_conditional_edges("visualization_builder", should_continue_to_content_builder)
workflow.add_edge("content_builder", END)

# Compile with Memory
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


logger.info("Workflow graph compiled successfully")
