import asyncio
import json
import os
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

app = Server("pharma-content-mcp")


def get_snowflake_connection():
    from cryptography.hazmat.primitives import serialization
    import os

    try:
        import streamlit as st
        private_key_text = st.secrets["private_key"]
        private_key = serialization.load_pem_private_key(
            private_key_text.encode(), password=None
        )
        account = st.secrets["SNOWFLAKE_ACCOUNT"]
        user = st.secrets["SNOWFLAKE_USER"]
        role = st.secrets["SNOWFLAKE_ROLE"]
        warehouse = st.secrets["SNOWFLAKE_WAREHOUSE"]
        database = st.secrets["SNOWFLAKE_DATABASE"]
        schema = st.secrets.get("SNOWFLAKE_SCHEMA", "marts")
    except Exception:
        with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None
            )
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        user = os.getenv("SNOWFLAKE_USER")
        role = os.getenv("SNOWFLAKE_ROLE")
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        database = os.getenv("SNOWFLAKE_DATABASE")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "marts")

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return snowflake.connector.connect(
        account=account,
        user=user,
        private_key=private_key_bytes,
        role=role,
        warehouse=warehouse,
        database=database,
        schema=schema
    )


def run_query(sql: str, database: str = None) -> list:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    if database:
        cursor.execute(f"USE DATABASE {database}")
    cursor.execute(sql)
    columns = [col[0].lower() for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def run_cortex_complete(prompt: str, model: str = "mistral-large2") -> str:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS response",
        (model, prompt)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_trial_summary",
            description="Get clinical trial data for content generation",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": "Cancer condition to filter trials"
                    },
                    "phase": {
                        "type": "string",
                        "description": "Trial phase e.g. Phase 3"
                    }
                }
            }
        ),
        types.Tool(
            name="get_safety_signals",
            description="Get pharmacovigilance safety signals for a drug",
            inputSchema={
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "Drug name to get safety signals for"
                    }
                },
                "required": ["drug_name"]
            }
        ),
        types.Tool(
            name="get_regulatory_context",
            description="Get FDA regulatory guidance context for a topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Regulatory topic to search for"
                    }
                },
                "required": ["topic"]
            }
        ),
        types.Tool(
            name="generate_plain_language_summary",
            description="Generate a plain language summary of clinical trial results",
            inputSchema={
                "type": "object",
                "properties": {
                    "trial_data": {
                        "type": "string",
                        "description": "Clinical trial data to summarize"
                    },
                    "audience": {
                        "type": "string",
                        "description": "Target audience: patient, hcp, or regulator"
                    }
                },
                "required": ["trial_data", "audience"]
            }
        ),
        types.Tool(
            name="generate_competitive_brief",
            description="Generate a competitive intelligence brief",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": "Disease condition for competitive analysis"
                    }
                },
                "required": ["condition"]
            }
        ),
        types.Tool(
            name="save_content_version",
            description="Save generated content to audit trail",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "description": "Type of content generated"
                    },
                    "source_document": {
                        "type": "string",
                        "description": "Source document or trial NCT ID"
                    },
                    "generated_content": {
                        "type": "string",
                        "description": "The generated content to save"
                    }
                },
                "required": ["content_type", "source_document", "generated_content"]
            }
        )
    ]


@app.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:

    if name == "get_trial_summary":
        condition = arguments.get("condition", "")
        phase = arguments.get("phase", "")
        where_clauses = []
        if condition:
            where_clauses.append(
                f"lower(conditions_list) like '%{condition.lower()}%'"
            )
        if phase:
            where_clauses.append(f"trial_phase = '{phase}'")
        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        sql = f"""
            SELECT
                nct_id, brief_title, trial_phase,
                trial_status, lead_sponsor, enrollment_count,
                start_date, completion_date, conditions_list,
                interventions_list, outcomes_list
            FROM pharma_agent_db.marts.trial_analytics
            {where}
            ORDER BY start_date DESC
            LIMIT 10
        """
        results = run_query(sql)
        return [types.TextContent(
            type="text",
            text=json.dumps(results, default=str)
        )]

    elif name == "get_safety_signals":
        drug_name = arguments.get("drug_name", "")
        sql = f"""
            SELECT
                drug_name, reaction, signal_strength,
                reporting_odds_ratio, serious_rate_pct,
                observed_count, requires_human_review
            FROM pharma_agent_db.marts.safety_signals
            WHERE lower(drug_name) like '%{drug_name.lower()}%'
            ORDER BY reporting_odds_ratio DESC
            LIMIT 10
        """
        results = run_query(sql)
        return [types.TextContent(
            type="text",
            text=json.dumps(results, default=str)
        )]

    elif name == "get_regulatory_context":
        topic = arguments.get("topic", "")
        sql = f"""
            SELECT PARSE_JSON(
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    'pharma_rag_db.marts.pharma_search_service',
                    '{{"query": "{topic}", "columns": ["file_name", "section_heading", "chunk_text"], "limit": 3}}'
                )
            ) AS results
        """
        try:
            results = run_query(sql)
            return [types.TextContent(
                type="text",
                text=json.dumps(results, default=str)
            )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Regulatory search unavailable: {str(e)}"
            )]

    elif name == "generate_plain_language_summary":
        trial_data = arguments.get("trial_data", "")
        audience = arguments.get("audience", "patient")

        audience_instructions = {
            "patient": "Write for patients with no medical background. Use simple words, avoid jargon, explain what the trial means for patients like them.",
            "hcp": "Write for healthcare professionals. Use appropriate medical terminology, focus on clinical outcomes and safety profile.",
            "regulator": "Write for regulatory reviewers. Be precise, cite specific data points, use regulatory terminology."
        }

        instruction = audience_instructions.get(
            audience,
            audience_instructions["patient"]
        )

        prompt = f"""You are a medical affairs writer.
Generate a plain language summary of this clinical trial data.

Target audience: {audience}
Instructions: {instruction}

Trial Data:
{trial_data}

Generate a clear, structured summary with:
1. What the trial studied
2. Key findings
3. Safety information
4. What this means for the audience

Keep it under 300 words."""

        content = run_cortex_complete(prompt)
        return [types.TextContent(type="text", text=content)]

    elif name == "generate_competitive_brief":
        condition = arguments.get("condition", "")
        sql = f"""
            SELECT
                lead_sponsor,
                COUNT(*) AS trial_count,
                array_agg(DISTINCT trial_phase) AS phases,
                array_agg(DISTINCT trial_status) AS statuses,
                AVG(enrollment_count) AS avg_enrollment
            FROM pharma_agent_db.marts.trial_analytics
            WHERE lower(conditions_list) like '%{condition.lower()}%'
            GROUP BY lead_sponsor
            ORDER BY trial_count DESC
            LIMIT 10
        """
        results = run_query(sql)

        prompt = f"""You are a competitive intelligence analyst in pharma.
Generate a competitive intelligence brief for {condition}.

Competitor trial data:
{json.dumps(results, default=str)}

Include:
1. Competitive landscape overview
2. Key players and their trial activity
3. Phase distribution across competitors
4. Strategic implications
5. Gaps and opportunities

Keep it under 400 words. Use professional pharma business language."""

        content = run_cortex_complete(prompt)
        return [types.TextContent(type="text", text=content)]

    elif name == "save_content_version":
        content_type = arguments.get("content_type", "")
        source_document = arguments.get("source_document", "")
        generated_content = arguments.get("generated_content", "")

        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pharma_content_db.audit.content_versions (
                content_type, source_document,
                prompt_version, model_used, generated_content
            ) SELECT %s, %s, %s, %s, %s
        """, (
            content_type,
            source_document,
            "v1.0",
            "mistral-large2",
            generated_content
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return [types.TextContent(
            type="text",
            text="Content saved successfully to audit trail."
        )]

    return [types.TextContent(type="text", text="Unknown tool")]

def get_trial_summary_direct(arguments: dict) -> str:
    condition = arguments.get("condition", "")
    phase = arguments.get("phase", "")
    where_clauses = []
    if condition:
        where_clauses.append(
            f"lower(conditions_list) like '%{condition.lower()}%'"
        )
    if phase:
        where_clauses.append(f"trial_phase = '{phase}'")
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = f"""
        SELECT
            nct_id, brief_title, trial_phase,
            trial_status, lead_sponsor, enrollment_count,
            start_date, completion_date, conditions_list,
            interventions_list, outcomes_list
        FROM pharma_agent_db.marts.trial_analytics
        {where}
        ORDER BY start_date DESC
        LIMIT 10
    """
    results = run_query(sql)
    return json.dumps(results, default=str)


def get_safety_signals_direct(arguments: dict) -> str:
    drug_name = arguments.get("drug_name", "")
    sql = f"""
        SELECT
            drug_name, reaction, signal_strength,
            reporting_odds_ratio, serious_rate_pct,
            observed_count, requires_human_review
        FROM pharma_agent_db.marts.safety_signals
        WHERE lower(drug_name) like '%{drug_name.lower()}%'
        ORDER BY reporting_odds_ratio DESC
        LIMIT 10
    """
    results = run_query(sql)
    return json.dumps(results, default=str)


def generate_plain_language_summary_direct(arguments: dict) -> str:
    trial_data = arguments.get("trial_data", "")
    audience = arguments.get("audience", "patient")
    audience_instructions = {
        "patient": "Write for patients with no medical background. Use simple words.",
        "hcp": "Write for healthcare professionals. Use appropriate medical terminology.",
        "regulator": "Write for regulatory reviewers. Be precise and cite data points."
    }
    instruction = audience_instructions.get(audience, audience_instructions["patient"])
    prompt = f"""You are a medical affairs writer.
Generate a plain language summary of this clinical trial data.
Target audience: {audience}
Instructions: {instruction}
Trial Data: {trial_data}
Generate a structured summary under 300 words covering:
1. What the trial studied
2. Key findings
3. Safety information
4. What this means for the audience"""
    return run_cortex_complete(prompt)


def generate_competitive_brief_direct(arguments: dict) -> str:
    condition = arguments.get("condition", "")
    sql = f"""
        SELECT
            lead_sponsor,
            COUNT(*) AS trial_count,
            AVG(enrollment_count) AS avg_enrollment
        FROM pharma_agent_db.marts.trial_analytics
        WHERE lower(conditions_list) like '%{condition.lower()}%'
        GROUP BY lead_sponsor
        ORDER BY trial_count DESC
        LIMIT 10
    """
    results = run_query(sql)
    prompt = f"""You are a competitive intelligence analyst in pharma.
Generate a competitive intelligence brief for {condition}.
Competitor trial data: {json.dumps(results, default=str)}
Include:
1. Competitive landscape overview
2. Key players and trial activity
3. Strategic implications
4. Gaps and opportunities
Keep under 400 words."""
    return run_cortex_complete(prompt)


def get_regulatory_context_direct(arguments: dict) -> str:
    topic = arguments.get("topic", "")
    sql = f"""
        SELECT PARSE_JSON(
            SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                'pharma_rag_db.marts.pharma_search_service',
                '{{"query": "{topic}", "columns": ["file_name", "section_heading", "chunk_text"], "limit": 3}}'
            )
        ) AS results
    """
    try:
        results = run_query(sql)
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Regulatory search unavailable: {str(e)}"


def save_content_version_direct(arguments: dict) -> str:
    content_type = arguments.get("content_type", "")
    source_document = arguments.get("source_document", "")
    generated_content = arguments.get("generated_content", "")
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pharma_content_db.audit.content_versions (
            content_type, source_document,
            prompt_version, model_used, generated_content
        ) SELECT %s, %s, %s, %s, %s
    """, (
        content_type,
        source_document,
        "v1.0",
        "mistral-large2",
        generated_content
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return "Content saved successfully to audit trail."

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())