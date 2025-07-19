from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from .agent import process_query
from pydantic import BaseModel
import pdfplumber
import logging
import os

logging.basicConfig(
    level=logging.INFO,  # Use DEBUG for more detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),  # Logs to file
        logging.StreamHandler()           # Also logs to console
    ]
)

logger = logging.getLogger(__name__)


app = FastAPI()

# Enable CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class QueryRequest(BaseModel):
    query: str

from fastapi.responses import JSONResponse

# @app.post("/ask")
# async def ask_agent(request: QueryRequest):
#     try:
#         sql_query = process_query(request.query)
#         return {"sql_query": sql_query}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

import re
import tempfile
import sqlite3

@app.post("/ask")
async def ask_agent(
    query: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        filename = file.filename.lower()
        # TXT
        if filename.endswith('.txt'):
            schema_text = (await file.read()).decode('utf-8')
        # PDF
        elif filename.endswith('.pdf'):
            with pdfplumber.open(file.file) as pdf:
                schema_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if not schema_text.strip():
                return JSONResponse(status_code=400, content={"error": "Could not extract text from PDF."})
        # SQLite

        elif filename.endswith('.sqlite'):
            try:
                with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
                    tmp.write(await file.read())
                    temp_path = tmp.name
                # Now explicitly close the file before connecting
                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()
                tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                schema_lines = []
                for (table,) in tables:
                    columns = cursor.execute(f"PRAGMA table_info({table})").fetchall()
                    col_names = [col[1] for col in columns]
                    schema_lines.append(f"{table}: {', '.join(col_names)}")
                schema_text = "\n".join(schema_lines)
                conn.close()
                os.remove(temp_path)  # Clean up temp file
                if not schema_text.strip():
                    return JSONResponse(status_code=400, content={"error": "No tables found in SQLite DB."})
            except Exception as e:
                import traceback
                print("SQLite extraction error:", traceback.format_exc())
                return JSONResponse(status_code=400, content={"error": f"SQLite parsing error: {e}"})


        # Postgres schema dump (assume .sql or .psql file)
        elif filename.endswith('.sql') or filename.endswith('.psql'):
            content = (await file.read()).decode('utf-8', errors='ignore')
            # Find all CREATE TABLE statements (multi-line, with columns)
            tables = re.findall(
                r'CREATE\s+TABLE\s+("?[\w\d]+"?)\s*\((.*?)\);',
                content,
                re.DOTALL | re.IGNORECASE
            )
            schema_lines = []
            for table_name, cols_block in tables:
                # Remove extra quotes if any
                table_name = table_name.replace('"', "")
                # Extract column names (lines that look like: colname TYPE ...)
                col_lines = [
                    l.strip() for l in cols_block.split(",")
                    if l.strip() and not l.lower().startswith("constraint")
                ]
                col_names = [re.split(r"\s+", l, 1)[0].replace('"', "") for l in col_lines]
                if col_names:
                    schema_lines.append(f"{table_name}: {', '.join(col_names)}")
            schema_text = "\n".join(schema_lines)
            if not schema_text.strip():
                return JSONResponse(status_code=400, content={"error": "No tables found in SQL file."})
        else:
            return JSONResponse(status_code=400, content={"error": "Supported files are: .txt, .pdf, .sqlite, .sql, .psql"})
        
        logger.info(f"{schema_text}")
        sql_query = process_query(query, schema_text)
        return {"sql_query": sql_query}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})