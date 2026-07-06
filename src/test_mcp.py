from src.mcp_server import generate_plain_language_summary_direct

result = generate_plain_language_summary_direct({
    "trial_data": "Phase 3 oncology trial with 500 patients showing 40% reduction in tumor size with acceptable safety profile",
    "audience": "patient"
})
print(result)