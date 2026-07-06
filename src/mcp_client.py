import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call an MCP tool directly by importing the server functions."""
    from src.mcp_server import (
        get_trial_summary_direct,
        get_safety_signals_direct,
        get_regulatory_context_direct,
        generate_plain_language_summary_direct,
        generate_competitive_brief_direct,
        save_content_version_direct
    )

    tool_map = {
        "get_trial_summary": get_trial_summary_direct,
        "get_safety_signals": get_safety_signals_direct,
        "get_regulatory_context": get_regulatory_context_direct,
        "generate_plain_language_summary": generate_plain_language_summary_direct,
        "generate_competitive_brief": generate_competitive_brief_direct,
        "save_content_version": save_content_version_direct
    }

    func = tool_map.get(tool_name)
    if func:
        return func(arguments)
    return "Tool not found"