import streamlit as st
import json
from src.mcp_server import (
    get_trial_summary_direct,
    get_safety_signals_direct,
    generate_plain_language_summary_direct,
    generate_competitive_brief_direct,
    get_regulatory_context_direct,
    save_content_version_direct,
    run_query
)

st.set_page_config(
    page_title="PharmaContent - Medical Affairs Generator",
    page_icon="📋",
    layout="wide"
)

st.title("📋 PharmaContent")
st.subheader("GenAI Content Generator for Medical Affairs")
st.markdown(
    "Generate plain language summaries, competitive intelligence briefs, "
    "and regulatory context - powered by Snowflake Cortex and MCP."
)

st.divider()

with st.sidebar:
    st.header("About")
    st.markdown("""
    **PharmaContent** uses MCP tools to:

    📝 **Plain Language Summaries**
    Convert trial data to patient/HCP/regulator language

    🔍 **Competitive Intelligence**
    Analyze competitor trial landscape

    📚 **Regulatory Context**
    Search FDA guidance documents

    🗂️ **Audit Trail**
    Every generated document versioned and tracked
    """)
    st.divider()
    st.header("MCP Tools Available")
    tools = [
        "get_trial_summary",
        "get_safety_signals",
        "generate_plain_language_summary",
        "generate_competitive_brief",
        "get_regulatory_context",
        "save_content_version"
    ]
    for tool in tools:
        st.markdown(f"- `{tool}`")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Plain Language Summary",
    "🔍 Competitive Intelligence",
    "📚 Regulatory Context",
    "🗂️ Audit Trail"
])

with tab1:
    st.header("Plain Language Summary Generator")
    st.markdown("Generate summaries of clinical trial data for different audiences.")
    col1, col2 = st.columns(2)
    with col1:
        condition = st.text_input(
            "Cancer condition",
            placeholder="e.g. breast cancer, leukemia"
        )
        phase = st.selectbox(
            "Trial phase",
            ["", "Phase 1", "Phase 2", "Phase 3", "Phase 1/2", "Phase 2/3"]
        )
    with col2:
        audience = st.selectbox(
            "Target audience",
            ["patient", "hcp", "regulator"],
            format_func=lambda x: {
                "patient": "Patient (plain language)",
                "hcp": "Healthcare Professional",
                "regulator": "Regulatory Reviewer"
            }[x]
        )
    if st.button("Fetch Trial Data", use_container_width=True):
        with st.spinner("Fetching trials via MCP..."):
            trial_data = get_trial_summary_direct({
                "condition": condition,
                "phase": phase
            })
            st.session_state.trial_data = trial_data
        trials = json.loads(trial_data)
        if trials:
            st.success(f"Found {len(trials)} trials")
            st.dataframe(
                [{
                    "NCT ID": t.get("nct_id"),
                    "Title": t.get("brief_title", "")[:60] + "...",
                    "Phase": t.get("trial_phase"),
                    "Status": t.get("trial_status"),
                    "Sponsor": t.get("lead_sponsor", "")[:30]
                } for t in trials],
                use_container_width=True
            )
        else:
            st.warning("No trials found for this condition/phase combination.")
    if "trial_data" in st.session_state:
        if st.button("Generate Summary", use_container_width=True):
            with st.spinner("Generating via MCP..."):
                summary = generate_plain_language_summary_direct({
                    "trial_data": st.session_state.trial_data,
                    "audience": audience
                })
                st.session_state.generated_summary = summary
    if "generated_summary" in st.session_state:
        st.divider()
        st.subheader("Generated Summary")
        edited = st.text_area(
            "Review and edit:",
            value=st.session_state.generated_summary,
            height=400
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve and Save", use_container_width=True):
                result = save_content_version_direct({
                    "content_type": "plain_language_summary_" + audience,
                    "source_document": condition or "oncology_trials",
                    "generated_content": edited
                })
                st.success(result)
        with col2:
            if st.button("Regenerate", use_container_width=True):
                del st.session_state.generated_summary
                st.rerun()

with tab2:
    st.header("Competitive Intelligence Brief")
    st.markdown("Analyze the competitor trial landscape for a disease condition.")
    condition_ci = st.text_input(
        "Disease condition",
        placeholder="e.g. lung cancer, lymphoma",
        key="ci_condition"
    )
    if st.button("Generate Competitive Brief", use_container_width=True):
        if condition_ci:
            with st.spinner("Analyzing competitor landscape via MCP..."):
                brief = generate_competitive_brief_direct({
                    "condition": condition_ci
                })
                st.session_state.competitive_brief = brief
        else:
            st.warning("Please enter a disease condition.")
    if "competitive_brief" in st.session_state:
        st.divider()
        st.subheader("Competitive Intelligence Brief")
        edited_brief = st.text_area(
            "Review and edit:",
            value=st.session_state.competitive_brief,
            height=400
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve and Save Brief", use_container_width=True):
                result = save_content_version_direct({
                    "content_type": "competitive_intelligence_brief",
                    "source_document": condition_ci,
                    "generated_content": edited_brief
                })
                st.success(result)
        with col2:
            if st.button("Regenerate Brief", use_container_width=True):
                del st.session_state.competitive_brief
                st.rerun()

with tab3:
    st.header("Regulatory Context Search")
    st.markdown("Search FDA guidance documents for regulatory context.")
    topic = st.text_input(
        "Regulatory topic",
        placeholder="e.g. dose escalation, safety monitoring, informed consent"
    )
    audience_reg = st.selectbox(
        "Generate summary for:",
        ["patient", "hcp", "regulator"],
        format_func=lambda x: {
            "patient": "Patient",
            "hcp": "Healthcare Professional",
            "regulator": "Regulatory Reviewer"
        }[x],
        key="reg_audience"
    )
    if st.button("Search Regulatory Documents", use_container_width=True):
        if topic:
            with st.spinner("Searching FDA guidance via MCP..."):
                context = get_regulatory_context_direct({"topic": topic})
                st.session_state.reg_context = context
            try:
                data = json.loads(context)
                if data:
                    st.success("Found regulatory context")
                    for item in data:
                        results_raw = item.get("results", {})
                        if isinstance(results_raw, str):
                            results_raw = json.loads(results_raw)
                        result_list = results_raw.get("results", [])
                        for r in result_list:
                            with st.expander(
                                str(r.get("file_name", "")) +
                                " - " +
                                str(r.get("section_heading", ""))[:50]
                            ):
                                st.markdown(
                                    str(r.get("chunk_text", ""))[:500]
                                )
            except Exception as ex:
                st.info(f"Context retrieved. {str(ex)}")
            with st.spinner("Generating regulatory summary via MCP..."):
                reg_summary = generate_plain_language_summary_direct({
                    "trial_data": context,
                    "audience": audience_reg
                })
                st.session_state.reg_summary = reg_summary
        else:
            st.warning("Please enter a regulatory topic.")
    if "reg_summary" in st.session_state:
        st.divider()
        st.subheader("Regulatory Summary")
        edited_reg = st.text_area(
            "Review and edit:",
            value=st.session_state.reg_summary,
            height=300
        )
        if st.button(
            "Approve and Save Regulatory Summary",
            use_container_width=True
        ):
            result = save_content_version_direct({
                "content_type": "regulatory_summary",
                "source_document": topic,
                "generated_content": edited_reg
            })
            st.success(result)

with tab4:
    st.header("Content Audit Trail")
    st.markdown("All generated and approved content with version history.")
    if st.button("Refresh Audit Trail", use_container_width=True):
        try:
            sql = (
                "SELECT version_id, content_type, source_document, "
                "model_used, status, created_at, "
                "LEFT(generated_content, 100) AS content_preview "
                "FROM pharma_content_db.audit.content_versions "
                "ORDER BY created_at DESC LIMIT 20"
            )
            records = run_query(sql)
            if records:
                st.dataframe(records, use_container_width=True)
                st.metric("Total documents generated", len(records))
            else:
                st.info(
                    "No content generated yet. "
                    "Use the other tabs to generate content."
                )
        except Exception as e:
            st.error(f"Error loading audit trail: {e}")