# Agent Safety Guardrail with Jev

This project implements a safety guardrail for AI agents using Jev (TypeSafe AI's System One Model) to validate tool calls before execution.

## What is Jev?

Jev is a specialized AI model that provides typed, structured decisions (Choice, Score, or Noul) from application state, enabling safe routing, risk checks, and tool-call guardrails without replacing LLMs.

## How the Guardrail Works

1. **Intercept Tool Calls**: When an AI agent wants to execute a tool, the request is intercepted
2. **State Analysis**: Current agent state + proposed tool details are sent to Jev API
3. **Structured Decision**: Jev returns a calibrated decision:
   - **Choice**: Approved/Rejected/Suggested Alternative
   - **Score**: Confidence level (0-1)
   - **Noul**: No decision (uncertainty)
4. **Enforce Decision**: Based on Jev's response:
   - Allow tool execution if approved with high confidence
   - Block if rejected or low confidence
   - Suggest alternatives if provided
   - Request clarification if noul/uncertain

## Project Structure

```
jev-agent-guardrail/
├── guardrail.py          # Core guardrail logic
├── jev_client.py         # Jev API client wrapper
├── config.py             # Configuration (includes your API key)
├── requirements.txt      # Dependencies
├── streamlit_app.py      # Interactive Streamlit dashboard
├── RUN_STREAMLIT.md      # How to run the Streamlit app
├── demo.py               # Quick demonstration script
└── examples/
    ├── simple_agent.py   # Example agent using the guardrail
    └── file_operations_agent.py # Example with file operation tools
```

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

Configure your Jev API key in `config.py` or as an environment variable:
```bash
export JEV_API_KEY="your_jev_api_key_here"
```

### Option 1: Run the Quick Demo
```bash
python demo.py
```

### Option 2: Run the Interactive Dashboard (Recommended)
```bash
streamlit run streamlit_app.py
```
Then open your browser to http://localhost:8501

### Option 3: Run the Examples
```bash
python examples/simple_agent.py
python examples/file_operations_agent.py
```

## Usage in Your Own Agent

```python
from config import create_guardrail_from_env
from guardrail import ToolCallRequest

# Initialize guardrail
guardrail = create_guardrail_from_env()

# Define your agent state
agent_state = {
    "user_role": "developer",
    "current_task": "processing user data",
    "permissions": ["read", "write"],
    "recent_actions": ["start_processing"],
    "risk_tolerance": "medium"
}

# Create tool call request
request = ToolCallRequest(
    tool_name="write_file",
    parameters={"file_path": "/tmp/output.txt", "content": "Hello World"},
    agent_state=agent_state,
    context="User wants to save processing results"
)

try:
    # Execute through guardrail (will block unsafe calls)
    result = guardrail.execute_tool_call(request, your_tool_executor_function)
    print(f"✅ Tool executed: {result}")
except PermissionError as e:
    print(f"❌ Blocked by guardrail: {e}")
```

## How Jev Enhances Safety

Traditional LLMs can hallucinate or make unsafe decisions when deciding which tools to call. Jev provides:
- **Structured Output**: No free-form text that could be misinterpreted
- **Calibrated Probabilities**: Reliable confidence scores
- **Fast Decision Making**: Optimized for real-time validation
- **Specialized Training**: Focused on decision-making rather than general conversation

## API Integration

The guardrail integrates with Jev's API via HTTP requests. Your API key is already configured.

## Example Workflow

```
AI Agent: "I want to call write_file('/etc/passwd', 'malicious content')"
        ↓
Guardrail: Intercepts request, prepares state
        ↓
Jev API: Analyzes state + request → Returns: {choice: "REJECTED", score: 0.98}
        ↓
Guardrail: Blocks the tool call, logs the attempt
        ↓
AI Agent: Receives block notification, considers safer alternatives
```

## Extending the Guardrail

You can customize the guardrail by:
- Adjusting confidence thresholds for different tool types
- Adding domain-specific state information to Jev inputs
- Implementing custom fallback logic for noul responses
- Adding audit logging and alerting

## Files Created

1. **jev_client.py** - Handles communication with Jev API
2. **guardrail.py** - Core guardrail logic that intercepts and validates tool calls
3. **config.py** - Configuration management (includes your API key)
4. **requirements.txt** - Python dependencies (now includes Streamlit)
5. **examples/simple_agent.py** - Basic demonstration with mock tools
6. **examples/file_operations_agent.py** - Real file operations with sandboxing
7. **demo.py** - Quick demonstration script
8. **streamlit_app.py** - Interactive dashboard for monitoring and testing
9. **RUN_STREAMLIT.md** - Detailed instructions for running the Streamlit app
10. **.gitignore** - Git ignore rules

## References

- [Jev AI API & AI Agents: A Practical Guide](https://huggingface.co/blog/sora-2/jev-ai-api-ai-agents-a-practical-guide-to-reliable)
- [Introducing System One Models & Jev - TypeSafe AI Blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [Jev Model Documentation](https://jevmodel.org/)