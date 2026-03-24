import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    Returns the connection object or None if failed.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def test_connection():
    """
    Tests the database connection.
    """
    conn = get_db_connection()
    if conn:
        logger.info("Successfully connected to the database!")
        conn.close()
        return True
    return False

def get_all_table_names():
    """
    Retrieves a list of all table names in the public schema.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        logger.error(f"Error fetching table names: {e}")
        if conn:
            conn.close()
        return []

def get_schema_summary(table_names = None):
    """
    Retrieves a summary of the database schema (tables and columns).
    Args:
        table_names (list, optional): List of table names to filter by.
    Returns:
        str: String representation of the schema.
    """
    conn = get_db_connection()
    if not conn:
        return "Error: Could not connect to database."

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query based on filter
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        if table_names:
            tables_str = "', '".join(table_names)
            query += f" AND table_name IN ('{tables_str}')"
            
        cursor.execute(query)
        tables = cursor.fetchall()
        
        schema_summary = ""
        
        for table in tables:
            table_name = table['table_name']
            schema_summary += f"Table: {table_name}\n"
            
            # Get columns for this table
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)
            columns = cursor.fetchall()
            
            for col in columns:
                schema_summary += f"  - {col['column_name']} ({col['data_type']})\n"
            schema_summary += "\n"
            
        conn.close()
        return schema_summary
    except Exception as e:
        logger.error(f"Error fetching schema: {e}")
        if conn:
            conn.close()
        return f"Error fetching schema: {e}"

def execute_read_query(query: str):
    """
    Executes a read-only SQL query and returns the results.
    """
    query_clean = query.lower().strip()
    if not (query_clean.startswith("select") or query_clean.startswith("with")):
        return {"error": "Only SELECT queries are allowed."}

    conn = get_db_connection()
    if not conn:
        return {"error": "Could not connect to database."}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convert RealDictCursor to list of dicts for easier handling
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()
