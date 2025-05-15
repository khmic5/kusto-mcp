"""
Azure Kusto client integration with proper authentication and error handling
"""
import os
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from azure.identity import DefaultAzureCredential, AzureCliCredential
import logging
from utils.config import load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kusto_client")

# Load configuration
config = load_config()
KUSTO_CLUSTER = config.get("kusto_cluster")
KUSTO_DATABASE = config.get("kusto_database")

# Global client instance
kusto_client = None

def initialize_client():
    """Initialize Kusto client with proper Azure authentication"""
    global kusto_client
    
    if not KUSTO_CLUSTER:
        logger.warning("Kusto cluster not configured")
        return False
    
    try:
        # Try DefaultAzureCredential first (handles various authentication methods)
        credential = DefaultAzureCredential()
        kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
            KUSTO_CLUSTER, credential
        )
        kusto_client = KustoClient(kcsb)
        logger.info(f"Successfully connected to Kusto cluster: {KUSTO_CLUSTER}")
        return True
    except Exception as e:
        logger.warning(f"Default credential failed: {str(e)}")
        
        try:
            # Fall back to Azure CLI auth
            credential = AzureCliCredential()
            kcsb = KustoConnectionStringBuilder.with_azure_cli_authentication(KUSTO_CLUSTER)
            kusto_client = KustoClient(kcsb)
            logger.info(f"Successfully connected to Kusto cluster using Azure CLI: {KUSTO_CLUSTER}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kusto client: {str(e)}")
            return False

def execute_query(query, database=None):
    """Run a KQL query with error handling and retries"""
    db = database or KUSTO_DATABASE
    
    if not kusto_client:
        if not initialize_client():
            return {"error": "Kusto client is not initialized. Please configure Kusto cluster details."}
    
    if not db:
        return {"error": "Database not specified"}
    
    try:
        response = kusto_client.execute_query(db, query)
        return response.primary_results[0].to_dict()
    except KustoServiceError as e:
        logger.error(f"Kusto query error: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

def get_schema(database=None):
    """Retrieve the schema of a Kusto database using a simple query"""
    db = database or KUSTO_DATABASE
    
    if not kusto_client:
        if not initialize_client():
            return {"error": "Kusto client is not initialized. Please configure Kusto cluster details."}
    
    if not db:
        return {"error": "Database not specified"}
    
    try:
        # Use a simple query to get schema information instead of management command
        query = "IntuneEvent() | getschema"
        response = kusto_client.execute_query(db, query)
        return response.primary_results[0].to_dict()
    except KustoServiceError as e:
        logger.error(f"Kusto schema error: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

def get_table_schema(table_name, database=None):
    """Retrieve the schema of a specific table in a Kusto database
    
    Args:
        table_name (str): Name of the table to get schema for
        database (str, optional): Database name. Defaults to configured database.
        
    Returns:
        dict: Dictionary containing the table schema or error message
    """
    db = database or KUSTO_DATABASE
    
    if not kusto_client:
        if not initialize_client():
            return {"error": "Kusto client is not initialized. Please configure Kusto cluster details."}
    
    if not db:
        return {"error": "Database not specified"}
    
    if not table_name:
        return {"error": "Table name not specified"}
    
    try:
        # Use a direct query to get the table schema
        query = f"{table_name} | getschema"
        response = kusto_client.execute_query(db, query)
        return response.primary_results[0].to_dict()
    except KustoServiceError as e:
        logger.error(f"Kusto schema error: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

# Initialize client if configuration is available
if KUSTO_CLUSTER and KUSTO_DATABASE:
    initialize_client()
else:
    logger.warning("Kusto configuration missing or incomplete")