# langgraph
from langchain_community.utilities import SQLDatabase
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

from typing import TypedDict, Optional, List, Dict
from pathlib import Path
# Create the chain
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import re
import os
import json
from pathlib import Path
import logging
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,  # Use DEBUG for more detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),  # Logs to file
        logging.StreamHandler()           # Also logs to console
    ]
)

logger = logging.getLogger(__name__)

# db_path = Path("chinook-database-master/ChinookDatabase/DataSources/Chinook_Sqlite_AutoIncrementPKs.sqlite").resolve()
# db = SQLDatabase.from_uri(f"sqlite:///{db_path}")


load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

llm = ChatOpenAI(
    openai_api_base="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv('GROQ_API_KEY'),
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",  # or "llama3-70b-8192"
)

prompt = PromptTemplate.from_template(
    "You are an assistant that generates SQL queries for a SQLite database.\n\n"
    "- If the user input has spelling mistakes in table or column names, correct them by comparing with known "
    "table/column names.\n"
    "- Available tables and columns:\n"
    "{schema}\n\n"
    "- Do not use DROP, DELETE, TRUNCATE, ALTER, or UPDATE statements.\n"
    "- Only generate safe SELECT statements.\n\n"
    "Question: {question}\n\nSQL:"
)

# sql_chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
sql_chain = prompt | llm
# 1. Schema

# def get_schema_text(db: SQLDatabase) -> str:
#     schema_lines = []
#     with db._engine.connect() as conn:  # Use _engine (private attribute)
#         for table in db.get_usable_table_names():
#             result = conn.execute(text(f"PRAGMA table_info({table})"))
#             columns = [row["name"] for row in result.mappings()]
#             schema_lines.append(f"{table}: {', '.join(columns)}")
#     return "\n".join(schema_lines)


# Do this once
# schema_text = get_schema_text(db)

# schema_path = Path(__file__).parent / "schema.txt"
# with open(schema_path, "r") as f:
#     schema_text = f.read()


# 2. Answering Node
def answer_node(state):
    retry_count = state.get("retry_count", 0)
    schema_text = state.get("schema_text", "")
    if retry_count > 3:
        return {"error": "Max retry limit hit", "retry": False}

    try:
        question = state["question"]
        result = sql_chain.invoke({
            "question": question,
            "schema": schema_text
        })

        sql = result.content.strip()
        # print("🧠 Generated SQL:", sql)
        return {"answer": sql, "retry": False, "retry_count": retry_count}
    except Exception as e:
        return {"error": str(e), "retry": True, "retry_count": retry_count + 1}


# 3. Error Node — logs and returns to retry
def error_handler(state):
    print(f"Error occurred: {state['error']}")
    return {"retry": True}


extract_prompt = PromptTemplate.from_template("""
You are a SQL parser assistant.

Given this SQL query, extract all tables and the columns used from each table.

Return a list of dictionaries in **valid JSON format only**. Each dictionary must have:
- "table": the table name
- "columns": a list of column names used from that table

Only return JSON. Do NOT include explanations or markdown.

Example:
[
  {{ "table": "Customers", "columns": ["CustomerId", "FirstName"] }},
  {{ "table": "Invoices", "columns": ["InvoiceId", "Total"] }}
]

SQL Query:
{query}
""")


# extract_chain = LLMChain(llm=llm, prompt=extract_prompt)


# 4. Validation Node


def validate_node(state):
    destructive_keywords = ["drop", "delete", "truncate", "alter", "update"]
    answer = state.get("answer", "")
    # print("🧪 Raw LLM Output:", repr(answer))

    if answer:
        # ✅ Extract SQL from code block (keep only what's inside the first ```sql block)
        match = re.search(r"```sql(.*?)```", answer, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1)
        else:
            # fallback: take everything up to the first markdown heading or explanation
            cleaned = answer.split("\n\n")[0]

        # Remove comments
        cleaned = re.sub(r"--.*", "", cleaned)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        lowered = cleaned.lower()

        # print("🧪 Cleaned SQL:", repr(cleaned))

        if any(keyword in lowered for keyword in destructive_keywords):
            return {
                "error": "❌ Destructive query detected. Execution not allowed.",
                "retry": False
            }
            # ✅ LLM-powered table/column extraction
        # try:
        #     extract_response = extract_chain.invoke({"query": cleaned})["text"]
        #     print("🧠 Raw Extract Response:", repr(extract_response))
        #
        #     # Remove markdown ```json blocks
        #     json_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", extract_response, re.IGNORECASE)
        #     if json_match:
        #         json_text = json_match.group(1).strip()
        #     else:
        #         json_text = extract_response.strip()
        #
        #     table_column_map = json.loads(json_text)
        #
        # except Exception as e:
        #     print("⚠️ LLM-based extraction failed:", e)
        #     table_column_map = []

        return {
            "answer": cleaned,
            "final_output": f"✅ Validated: {cleaned}",
            # "table_column_map": table_column_map,
            "retry": False
        }

    else:
        return {
            "error": "Validation failed: No answer found.",
            "retry": True
        }


# def execute_sql_node(state):
#     from sqlalchemy.exc import SQLAlchemyError
#
#     sql = state.get("answer")
#     print(f"🔍 Raw SQL to run: {repr(sql)}")
#     try:
#         if not sql:
#             raise ValueError("No SQL query provided.")
#
#         result1 = db.run(sql)
#         print("*******************", result1, "**********************")
#         return {
#             "final_output": f"✅ Executed successfully:\n{result1}",
#             "retry": False
#         }
#     except SQLAlchemyError as e:
#         return {
#             "error": f"SQL execution failed: {str(e)}",
#             "retry": True,
#             "retry_count": state.get("retry_count", 0) + 1
#         }
#     except Exception as e:
#         return {
#             "error": f"Execution error: {str(e)}",
#             "retry": True,
#             "retry_count": state.get("retry_count", 0) + 1
#         }


def log_activity(state):
    log_lines = [
        f"timestamp: {datetime.now().isoformat()}",
        f"request_id: {state.get('request_id')}",
        f"question: {state.get('question')}",
        f"generated_sql: {state.get('answer')}",
        f"final_output: {state.get('final_output')}",
        f"error: {state.get('error')}",
        f"retry: {state.get('retry')}",
        f"retry_count: {state.get('retry_count')}",
        f"table_column_map: {state.get('table_column_map')}"
    ]

    log_entry = "\n".join(log_lines) + "\n" + ("=" * 60) + "\n"

    with open("query_logs.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)

    return state  # Continue passing unchanged state forward


# Define the state structure
class GraphState(TypedDict):
    question: str
    answer: Optional[str]
    error: Optional[str]
    final_output: Optional[str]
    retry: Optional[bool]
    retry_count: int  # Track attempts
    # table_column_map: Optional[List[Dict[str, List[str]]]]


# Build the graph with schema
graph = StateGraph(GraphState)
graph.add_node("generate_answer", answer_node)
graph.add_node("error_handler", error_handler)
graph.add_node("validate_output", validate_node)  # This was missing!
graph.add_node("log_activity", log_activity)
# graph.add_node("execute_sql", RunnableLambda(execute_sql_node))

graph.set_entry_point("generate_answer")

# Conditional transition from generate_answer
graph.add_conditional_edges(
    "generate_answer",
    lambda state: "error_handler" if state.get("retry", False) else "validate_output",
    {
        "error_handler": "error_handler",
        "validate_output": "validate_output"
    }
)

graph.add_conditional_edges(
    "validate_output",
    # lambda state: "error_handler" if state.get("retry", False) else "execute_sql",
    lambda state: "error_handler" if state.get("retry", False) else "log_activity",
    {
        "error_handler": "error_handler",
        # "execute_sql": "execute_sql"
        "log_activity": "log_activity"
    }
)

graph.add_edge("error_handler", "generate_answer")
# graph.add_edge("execute_sql", "log_activity")
graph.add_edge("log_activity", END)

import datetime

from datetime import datetime

# Compile the graph

app = graph.compile()


# Run it
def process_query(query, schema_text, request_id=None):
    global app
    state = {
        "question": query,
        "schema_text": schema_text,
        "retry_count": 0,  # always start with zero
        "answer": None,
        "error": None,
        "final_output": None,
        # "table_column_map": None, # if you activate table_column_map
    }
    if request_id:
        state["request_id"] = request_id

    result = app.invoke(state)
    # Prefer to return values rather than print, so the API can use them
    if result.get("final_output"):
        return result["final_output"]
    elif result.get("answer"):
        return result["answer"]
    elif result.get("error"):
        return f"Error: {result['error']}"
    else:
        return "Unexpected failure"
