import streamlit as st
import time
import json
from guardrail import AgentSafetyGuardrail, ToolCallRequest
from jev_client import JevClient
from config import GuardrailConfig

# Page configuration
st.set_page_config(
    page_title="Jev Safety Guardrail Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .status-allowed { color: #00C851; font-weight: bold; }
    .status-blocked { color: #ff4444; font-weight: bold; }
    .status-uncertain { color: #ffbb33; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Jev Agent Safety Guardrail Dashboard")
st.markdown("*Monitor and test your AI agent's safety guardrail powered by TypeSafe AI's Jev Model*")

# Initialize guardrail (uses your API key from config)
@st.cache_resource
def get_guardrail():
    try:
        config = GuardrailConfig.from_env()
        jev_client = JevClient(api_key=config.jev_api_key, api_url=config.jev_api_url, mock_mode=True)
        return AgentSafetyGuardrail(
            jev_client=jev_client,
            approval_threshold=config.approval_threshold,
            rejection_threshold=config.rejection_threshold,
            noul_action=config.noul_action
        )
    except Exception as e:
        st.error(f"Failed to initialize guardrail: {str(e)}")
        st.info("Make sure your Jev API key is configured in config.py")
        return None

guardrail = get_guardrail()

if guardrail is None:
    st.stop()

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Guardrail Configuration")

    # Mode toggle at top
    use_simulation = st.toggle(
        "Local Simulation Mode",
        value=True,
        help="Use realistic local safety guardrail evaluation without requiring an external API connection."
    )
    guardrail.jev_client.mock_mode = use_simulation

    # API Status right at top
    if guardrail.jev_client.mock_mode:
        st.success("🟢 Simulation Active")
        st.caption("Testing enabled with built-in safety policies")
    else:
        try:
            if guardrail.jev_client.health_check():
                st.success("✅ Jev API Connected")
            else:
                st.error("❌ Jev API Disconnected")
                st.caption("Auto-fallbacks to local rules on error")
        except:
            st.warning("⚠️ Cannot reach Jev API")

    st.divider()

    # Threshold sliders
    approval_thresh = st.slider(
        "Approval Threshold",
        0.0, 1.0,
        guardrail.approval_threshold,
        0.01,
        help="Minimum confidence score to allow a tool call"
    )

    rejection_thresh = st.slider(
        "Rejection Threshold",
        0.0, 1.0,
        guardrail.rejection_threshold,
        0.01,
        help="Minimum confidence score to block a tool call"
    )

    noul_action = st.selectbox(
        "Action on Uncertain (Noul)",
        ["request_clarification", "block", "suggest_alternative"],
        index=["request_clarification", "block", "suggest_alternative"].index(guardrail.noul_action),
        help="What to do when Jev returns uncertain/no decision"
    )

    # Update guardrail if thresholds changed
    if approval_thresh != guardrail.approval_threshold:
        guardrail.approval_threshold = approval_thresh
    if rejection_thresh != guardrail.rejection_threshold:
        guardrail.rejection_threshold = rejection_thresh
    guardrail.noul_action = noul_action

    st.divider()

    # Quick stats
    st.subheader("📊 Quick Stats")
    stats = guardrail.get_statistics()
    st.metric("Total Validations", stats.get("total_calls", 0))
    st.metric("Approval Rate", f"{stats.get('approval_rate', 0):.1%}")
    st.metric("Block Rate", f"{stats.get('block_rate', 0):.1%}")

# Main interface
tab1, tab2, tab3, tab4 = st.tabs(["🧪 Test Tool Call", "📈 Live Monitor", "📜 Audit Log", "📋 Documentation"])

with tab1:
    st.subheader("Test a Tool Call with Jev")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Tool Configuration")
        tool_name = st.text_input(
            "Tool Name",
            "delete_file",
            help="Name of the tool to validate (e.g., read_file, delete_file, execute_shell)"
        )

        # Predefined tool templates
        tool_templates = {
            "Custom": "",
            "File Read": '{"file_path": "/path/to/file.txt"}',
            "File Write": '{"file_path": "/path/to/output.txt", "content": "Hello World"}',
            "File Delete": '{"file_path": "/path/to/delete.txt"}',
            "Shell Execute": '{"command": "ls -la"}',
            "Network Request": '{"url": "https://api.example.com/data", "method": "GET"}',
            "Database Query": '{"query": "SELECT * FROM users", "database": "prod"}'
        }

        selected_template = st.selectbox("Quick Template", list(tool_templates.keys()))
        if selected_template != "Custom":
            params_str = tool_templates[selected_template]
        else:
            params_str = st.session_state.get('params_str', '{"key": "value"}')

        params_str = st.text_area(
            "Parameters (JSON)",
            params_str,
            height=100,
            help="Tool parameters as JSON object"
        )

        # Store in session state for persistence
        st.session_state.params_str = params_str

    with col2:
        st.markdown("#### Agent Context")

        # Predefined state templates
        state_templates = {
            "Custom": {},
            "Developer (Low Risk)": {
                "user_role": "developer",
                "current_task": "working on feature development",
                "permissions": ["read", "write"],
                "recent_actions": ["start_work", "load_dependencies"],
                "risk_tolerance": "low"
            },
            "Data Scientist (Medium Risk)": {
                "user_role": "data_scientist",
                "current_task": "analyzing customer data",
                "permissions": ["read", "write", "execute"],
                "recent_actions": ["load_dataset", "start_analysis"],
                "risk_tolerance": "medium"
            },
            "System Admin (High Risk)": {
                "user_role": "system_administrator",
                "current_task": "performing system maintenance",
                "permissions": ["read", "write", "execute", "delete"],
                "recent_actions": ["system_check", "backup_start"],
                "risk_tolerance": "high"
            },
            "Untrusted User": {
                "user_role": "guest",
                "current_task": "exploring system capabilities",
                "permissions": ["read"],
                "recent_actions": ["login"],
                "risk_tolerance": "low"
            }
        }

        selected_state = st.selectbox("Agent State Template", list(state_templates.keys()))
        if selected_state != "Custom":
            agent_state = state_templates[selected_state]
            agent_state_str = json.dumps(agent_state, indent=2)
        else:
            agent_state_str = st.session_state.get('agent_state_str', '{"user_role": "user", "current_task": "testing", "permissions": ["read"], "recent_actions": ["start"], "risk_tolerance": "medium"}')

        agent_state_str = st.text_area(
            "Agent State (JSON)",
            agent_state_str,
            height=150,
            help="Current state of your AI agent as JSON"
        )

        st.session_state.agent_state_str = agent_state_str

        context = st.text_input(
            "Additional Context",
            "User attempting to access system file",
            help="Any additional context about why this tool is being called"
        )

    # Test button
    if st.button("🔍 Validate with Jev", type="primary", use_container_width=True):
        try:
            # Parse JSON inputs
            params = json.loads(params_str) if params_str.strip() else {}
            agent_state = json.loads(agent_state_str) if agent_state_str.strip() else {}

            if not tool_name.strip():
                st.error("Please enter a tool name")
            else:
                # Create tool call request
                request = ToolCallRequest(
                    tool_name=tool_name.strip(),
                    parameters=params,
                    agent_state=agent_state,
                    context=context.strip()
                )

                # Show processing
                with st.spinner("Querying Jev for decision..."):
                    # Get Jev decision directly
                    jev_decision = guardrail.jev_client.validate_tool_call(
                        agent_state=agent_state,
                        tool_name=tool_name.strip(),
                        tool_parameters=params,
                        context=context.strip()
                    )

                # Display results in a nice format
                st.markdown("#### 🎯 Jev Decision Results")

                # Decision cards
                res_col1, res_col2, res_col3, res_col4 = st.columns(4)

                with res_col1:
                    choice_color = {
                        "APPROVED": "#00C851",
                        "REJECTED": "#ff4444",
                        "SUGGEST_ALTERNATIVE": "#ffbb33"
                    }.get(jev_decision.choice.value, "#666")
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background-color: {choice_color}20; border-radius: 0.5rem; border-left: 4px solid {choice_color};">
                        <h3 style="color: {choice_color}; margin: 0;">{jev_decision.choice.value}</h3>
                        <p style="margin: 0; font-size: 0.9em;">Decision</p>
                    </div>
                    """, unsafe_allow_html=True)

                with res_col2:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background-color: #33b5e520; border-radius: 0.5rem; border-left: 4px solid #33b5e5;">
                        <h3 style="color: #33b5e5; margin: 0;">{jev_decision.score:.2f}</h3>
                        <p style="margin: 0; font-size: 0.9em;">Confidence Score</p>
                    </div>
                    """, unsafe_allow_html=True)

                with res_col3:
                    noul_value = jev_decision.noul.value if jev_decision.noul else "None"
                    noul_color = "#ffbb33" if noul_value != "None" else "#999"
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background-color: {noul_color}20; border-radius: 0.5rem; border-left: 4px solid {noul_color};">
                        <h3 style="color: {noul_color}; margin: 0;">{noul_value}</h3>
                        <p style="margin: 0; font-size: 0.9em;">Noul (Uncertainty)</p>
                    </div>
                    """, unsafe_allow_html=True)

                with res_col4:
                    # Determine guardrail action
                    guardrail_decision = guardrail._make_guardrail_decision(jev_decision, request)
                    action_color = {
                        "ALLOW": "#00C851",
                        "BLOCK": "#ff4444",
                        "SUGGEST_ALTERNATIVE": "#ffbb33",
                        "REQUEST_CLARIFICATION": "#ffbb33"
                    }.get(guardrail_decision.action.value, "#666")
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background-color: {action_color}20; border-radius: 0.5rem; border-left: 4px solid {action_color};">
                        <h3 style="color: {action_color}; margin: 0;">{guardrail_decision.action.value}</h3>
                        <p style="margin: 0; font-size: 0.9em;">Guardrail Action</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Additional details
                if jev_decision.reasoning:
                    st.info(f"**💭 Jev Reasoning:** {jev_decision.reasoning}")

                if jev_decision.suggested_alternative:
                    st.warning(f"**🔄 Suggested Alternative:** {jev_decision.suggested_alternative}")

                if guardrail_decision.reason and guardrail_decision.reason not in ["Approved by Jev", "Rejected by Jev"]:
                    if guardrail_decision.action.value == "BLOCK":
                        st.error(f"**🛡️ Guardrail Reason:** {guardrail_decision.reason}")
                    elif guardrail_decision.action.value == "SUGGEST_ALTERNATIVE":
                        st.warning(f"**🔄 Guardrail Suggestion:** {guardrail_decision.reason}")
                    else:
                        st.info(f"**ℹ️ Guardrail Info:** {guardrail_decision.reason}")

                # Final decision banner
                if guardrail_decision.action.value == "ALLOW":
                    st.success("✅ **TOOL CALL ALLOWED** - Proceed with execution")
                elif guardrail_decision.action.value == "BLOCK":
                    st.error("❌ **TOOL CALL BLOCKED** - Safety violation prevented")
                else:
                    st.warning(f"⚠️ **TOOL CALL {guardrail_decision.action.value}** - {guardrail_decision.reason}")

                # Automatically record this validation to audit history and live monitor
                guardrail._record_call(request, jev_decision)
                st.caption("📝 Validation logged to Live Monitor & Audit Log")

        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            st.error(f"Error during validation: {str(e)}")
            st.exception(e)

with tab2:
    st.subheader("Live Validation Monitor")

    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh (every 5 seconds)", value=False)
    with col2:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    with col3:
        st.write(f"Last updated: {time.strftime('%H:%M:%S')}")

    # Real-time stats display
    stats_placeholder = st.empty()

    def update_stats():
        stats = guardrail.get_statistics()
        with stats_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Calls", stats.get("total_calls", 0))
            with col2:
                st.metric("Approved", stats.get("approved", 0),
                         delta=f"+{stats.get('approved', 0) - st.session_state.get('last_approved', 0)}"
                         if 'last_approved' in st.session_state else None)
            with col3:
                st.metric("Blocked", stats.get("blocked", 0),
                         delta=f"+{stats.get('blocked', 0) - st.session_state.get('last_blocked', 0)}"
                         if 'last_blocked' in st.session_state else None)
            with col4:
                st.metric("Uncertain", stats.get("uncertain", 0))

            # Rates
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Approval Rate", f"{stats.get('approval_rate', 0):.1%}")
            with col2:
                st.metric("Block Rate", f"{stats.get('block_rate', 0):.1%}")

            # Update session state for deltas
            st.session_state.last_approved = stats.get("approved", 0)
            st.session_state.last_blocked = stats.get("blocked", 0)

    # Initial stats display
    update_stats()

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(5)
        st.rerun()

    st.divider()

    # Recent activity chart (if we have data)
    history = guardrail.get_call_history(limit=20)
    if history and len(history) > 0:
        st.subheader("📊 Recent Validation Activity")

        # Prepare data for chart
        chart_data = []
        for i, call in enumerate(reversed(history)):  # Most recent first
            chart_data.append({
                "Time": len(history) - i,  # Reverse order for chart
                "Tool": call["tool_name"],
                "Decision": call["jev_choice"],
                "Score": call["jev_score"],
                "Timestamp": call["timestamp"]
            })

        # Display as dataframe
        import pandas as pd
        df = pd.DataFrame(chart_data)

        # Style the dataframe
        def color_decision(val):
            color_map = {
                "APPROVED": "background-color: #d4edda; color: #155724",
                "REJECTED": "background-color: #f8d7da; color: #721c24",
                "SUGGEST_ALTERNATIVE": "background-color: #fff3cd; color: #856404",
                "UNCERTAIN": "background-color: #d1ecf1; color: #0c5460",
                "INSUFFICIENT_DATA": "background-color: #d1ecf1; color: #0c5460",
                "CONFLICTING_INFORMATION": "background-color: #d1ecf1; color: #0c5460"
            }
            return color_map.get(val, "")

        styled_df = df.style.applymap(color_decision, subset=["Decision"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("📊 No validation history yet. Test some tool calls in the 'Test Tool Call' tab to see activity here.")

with tab3:
    st.subheader("📜 Complete Audit Log")

    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        show_details = st.checkbox("Show full JSON details", value=False)
    with col2:
        if st.button("🗑️ Clear Audit Log"):
            guardrail.call_history.clear()
            if hasattr(guardrail, "audit_log_path") and os.path.exists(guardrail.audit_log_path):
                try:
                    open(guardrail.audit_log_path, "w", encoding="utf-8").close()
                except Exception:
                    pass
            st.success("Audit log cleared!")
            st.rerun()

    # Get audit log
    history = guardrail.get_call_history(limit=100)  # Get more for audit view

    if history:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Entries", len(history))
        with col2:
            approved_count = sum(1 for h in history if h["jev_choice"] == "APPROVED" and h["jev_score"] >= guardrail.approval_threshold)
            st.metric("Approved", approved_count)
        with col3:
            blocked_count = sum(1 for h in history if h["jev_choice"] == "REJECTED" and h["jev_score"] >= guardrail.rejection_threshold)
            st.metric("Blocked", blocked_count)
        with col4:
            uncertain_count = sum(1 for h in history if h["jev_noul"] is not None)
            st.metric("Uncertain", uncertain_count)

        st.divider()

        # Display entries
        for i, call in enumerate(reversed(history)):  # Most recent first
            with st.expander(
                f"🕒 {call['timestamp'][-8:] if len(call['timestamp']) > 8 else call['timestamp']} | "
                f"{call['tool_name']} | "
                f"{call['jev_choice']} ({call['jev_score']:.2f})"
            ):
                if show_details:
                    st.json(call)
                else:
                    # Nice formatted display
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Tool Call Details**")
                        st.text(f"Tool: {call['tool_name']}")
                        st.text(f"Parameters: {json.dumps(call.get('parameters', {}), indent=2)}")
                        st.text(f"Context: {call.get('context', 'N/A')}")
                    with col2:
                        st.markdown("**Jev Decision**")
                        decision_color = {
                            "APPROVED": "#00C851",
                            "REJECTED": "#ff4444",
                            "SUGGEST_ALTERNATIVE": "#ffbb33"
                        }.get(call["jev_choice"], "#666")
                        st.markdown(f"<span style='color: {decision_color}; font-weight: bold;'>{call['jev_choice']}</span>", unsafe_allow_html=True)
                        st.text(f"Confidence: {call['jev_score']:.2f}")
                        st.text(f"Noul: {call['jev_noul'] or 'None'}")
                        if call.get('reasoning'):
                            st.text(f"Reasoning: {call['reasoning']}")
                        if call.get('suggested_alternative'):
                            st.text(f"Alternative: {call['suggested_alternative']}")
    else:
        st.info("📭 Audit log is empty. Test some tool calls to populate the log.")
        st.markdown("""
        ### How to populate the audit log:
        1. Go to the **"Test Tool Call"** tab
        2. Configure a tool call (tool name, parameters, agent state, context)
        3. Click **"🔍 Validate with Jev"**
        4. (Optional) Check **"Log this test call to audit history"**
        5. The call will appear here with full details
        """)

with tab4:
    st.subheader("📋 Documentation & Help")

    st.markdown("""
    ## 🛡️ Jev Safety Guardrail Dashboard

    This dashboard provides a visual interface for monitoring and testing your AI agent's safety guardrail powered by **TypeSafe AI's Jev Model**.

    ### 🔧 How It Works

    1. **Interception**: When your AI agent attempts to execute a tool, the call is intercepted by the guardrail
    2. **Analysis**: Current agent state + tool details are sent to the Jev API for evaluation
    3. **Decision**: Jev returns a structured decision:
       - **Choice**: APPROVED, REJECTED, or SUGGEST_ALTERNATIVE
       - **Score**: Confidence level (0.0-1.0)
       - **Noul**: Indicates uncertainty when Jev cannot make a confident decision
    4. **Enforcement**: The guardrail enforces the decision based on configured thresholds

    ### 📊 Understanding the Metrics

    - **Approval Threshold**: Minimum confidence score required to allow a tool call (default: 0.7)
    - **Rejection Threshold**: Minimum confidence score required to block a tool call (default: 0.6)
    - **Approval Rate**: Percentage of tool calls that were approved
    - **Block Rate**: Percentage of tool calls that were blocked
    - **Noul Rate**: Percentage of tool calls where Jev was uncertain

    ### 🛠️ Configuration Tips

    - **For higher safety**: Increase rejection threshold, decrease approval threshold
    - **For fewer false blocks**: Increase both thresholds (requires higher confidence)
    - **For noul handling**:
      - `request_clarification`: Ask for more context when uncertain (recommended)
      - `block`: Block uncertain calls (maximum safety)
      - `suggest_alternative`: Use Jev's suggested alternative when available

    ### 🔌 Integration with Your AI Agent

    To use this guardrail in your own AI agent:

    ```python
    from config import create_guardrail_from_env
    from guardrail import ToolCallRequest

    # Initialize (uses your API key from config.py)
    guardrail = create_guardrail_from_env()

    # When your agent wants to execute a tool:
    request = ToolCallRequest(
        tool_name="tool_name",
        parameters={"param": "value"},
        agent_state=your_agent_state_dict,
        context="Why this tool is needed"
    )

    try:
        result = guardrail.execute_tool_call(request, your_tool_function)
        # Tool executed successfully
    except PermissionError as e:
        # Guardrail blocked the call
        print(f"Safety block: {e}")
    ```

    ### 📚 Resources

    - [Jev Model Documentation](https://jevmodel.org/)
    - [TypeSafe AI Blog: Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
    - [Jev AI API & AI Agents: Practical Guide](https://huggingface.co/blog/sora-2/jev-ai-api-ai-agents-a-practical-guide-to-reliable)

    ### 💡 Best Practices

    1. **Monitor regularly**: Check the dashboard for unusual patterns
    2. **Tune thresholds**: Adjust based on your agent's behavior and risk tolerance
    3. **Review audit log**: Look for patterns in blocked/allowed calls
    4. **Provide rich state**: The more context you give Jev, the better its decisions
    5. **Test edge cases**: Use the test tab to verify your configuration works as expected
    """)

    # Show current configuration
    with st.expander("🔧 Current Guardrail Configuration"):
        config_dict = {
            "Jev API URL": guardrail.jev_client.api_url,
            "Approval Threshold": guardrail.approval_threshold,
            "Rejection Threshold": guardrail.rejection_threshold,
            "Noul Action": guardrail.noul_action,
            "API Key Configured": bool(guardrail.jev_client.api_key)
        }
        for key, value in config_dict.items():
            st.text(f"{key}: {value}")

# Footer
st.divider()
st.caption("🛡️ Jev Safety Guardrail Dashboard • Powered by TypeSafe AI's Jev Model • Built with Streamlit")
st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")