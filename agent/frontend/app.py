import streamlit as st
import httpx
import os

st.set_page_config(
    page_title="Autonomous AI Agent Document Builder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    .main {
        background-color: #f7f9fc;
        font-family: 'Inter', sans-serif;
    }
    h1 {
        color: #1F4E79;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .subtitle {
        color: #7F7F7F;
        font-size: 1.15rem;
        margin-bottom: 25px;
    }
    .card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
    }
    .badge {
        background-color: #E2ECF6;
        color: #1F4E79;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    .log-box {
        background-color: #1E1E1E;
        color: #33FF33;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 8px;
        height: 250px;
        overflow-y: scroll;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>Autonomous AI Document Builder</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Powered by LangGraph, FastAPI, and Multi-Step Plan-Execute-Review Loop</p>", unsafe_allow_html=True)

# Layout
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Generate Document")
    user_request = st.text_area(
        "Enter your document request or description:",
        placeholder="e.g. Create a project plan for launching a mobile app in Q3.",
        height=180
    )
    
    api_url = st.text_input("Backend API URL", value="http://127.0.0.1:8000/agent")
    submit_btn = st.button("Generate autonomously", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Sample Prompts")
    st.markdown("""
    * **Standard Request**: *\"Create a project plan for launching a mobile app in Q3.\"* (Sails through review)
    * **Complex Request**: *\"Write a business proposal for a new client.\"* (Requires the agent to make assumptions and triggers retry/replan loops due to lack of details)
    """)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    if submit_btn:
        if not user_request.strip():
            st.error("Please enter a valid request.")
        else:
            with st.spinner("Agent routing, planning, drafting and reviewing..."):
                try:
                    # Make post request to backend
                    response = httpx.post(api_url, json={"request": user_request}, timeout=120.0)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            st.success("Document generated successfully!")
                            
                            # Download link section
                            docx_path = data.get("docx_path", "")
                            if docx_path:
                                filename = os.path.basename(docx_path)
                                download_url = f"http://127.0.0.1:8000/download/{filename}"
                                st.markdown(f"### 🎉 [Download Generated Word Document (.docx)]({download_url})")
                            
                            # Tabs for output detail
                            tab1, tab2, tab3, tab4 = st.tabs(["📝 Generated Content", "🧭 Planning & Assumptions", "🏁 Interactive Timeline", "⚙️ Raw Logs"])
                            
                            with tab1:
                                for idx, section in enumerate(data.get("sections", [])):
                                    st.markdown(f"### {section['heading']}")
                                    st.write(section['body'])
                                    st.divider()
                                    
                            with tab2:
                                st.markdown("#### Plan Steps")
                                for idx, step in enumerate(data.get("plan", [])):
                                    st.markdown(f"**Step {idx+1}: {step['step']}**")
                                    st.caption(step['description'])
                                
                                st.divider()
                                st.markdown("#### Assumptions Made")
                                for assumption in data.get("assumptions", []):
                                    st.info(assumption)
                                    
                            with tab3:
                                st.markdown("#### Agent Execution Steps & Loop Timeline")
                                for log in data.get("logs", []):
                                    if "Initial state prepared" in log:
                                        st.markdown(f"⚡ **System:** {log}")
                                    elif "Planning" in log or "Generated plan" in log or "Replanning" in log:
                                        with st.chat_message("planner", avatar="📝"):
                                            st.markdown(log)
                                    elif "Executing step" in log or "Executor failed" in log:
                                        with st.chat_message("executor", avatar="⚙️"):
                                            st.markdown(log)
                                    elif "Review SUCCESS" in log:
                                        with st.chat_message("reviewer_success", avatar="✅"):
                                            st.markdown(log)
                                    elif "Review FAILURE" in log or "Reviewing draft" in log or "Reviewer node failed" in log:
                                        with st.chat_message("reviewer", avatar="🔍"):
                                            st.markdown(log)
                                    elif "Successfully saved" in log or "Building final" in log:
                                        with st.chat_message("builder", avatar="📄"):
                                            st.markdown(log)
                                    else:
                                        st.markdown(f"🔹 {log}")
                                    
                            with tab4:
                                st.markdown("#### Execution Trace Logs")
                                log_text = "\n".join(data.get("logs", []))
                                st.code(log_text, language="text")
                                
                        else:
                            st.error(f"Execution failed: {data.get('error')}")
                            
                    else:
                        st.error(f"HTTP error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend API: {str(e)}")
    else:
        st.info("Enter a prompt on the left and click 'Generate autonomously' to begin the workflow.")
