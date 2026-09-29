"""
Agent Safety Guardrail Core
Implements the safety guardrail that intercepts and validates tool calls using Jev.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from jev_client import JevClient, JevDecision, JevChoice


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolCallAction(str, Enum):
    """Actions the guardrail can take"""
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    SUGGEST_ALTERNATIVE = "SUGGEST_ALTERNATIVE"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"


@dataclass
class ToolCallRequest:
    """Represents a tool call request to be validated"""
    tool_name: str
    parameters: Dict[str, Any]
    agent_state: Dict[str, Any]
    context: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class GuardrailDecision:
    """Decision made by the guardrail"""
    action: ToolCallAction
    jev_decision: Optional[JevDecision] = None
    reason: str = ""
    alternative_suggestion: Optional[str] = None
    blocked_tool_call: Optional[ToolCallRequest] = None


@dataclass
class ToolDefinition:
    """Definition of a tool that can be guarded"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    risk_level: str = "medium"  # low, medium, high
    requires_approval: bool = False


class AgentSafetyGuardrail:
    """
    Main guardrail class that validates tool calls using Jev before execution.
    """

    def __init__(
        self,
        jev_client: JevClient,
        approval_threshold: float = 0.7,
        rejection_threshold: float = 0.6,
        noul_action: ToolCallAction = ToolCallAction.REQUEST_CLARIFICATION
    ):
        self.jev_client = jev_client
        self.approval_threshold = approval_threshold
        self.rejection_threshold = rejection_threshold
        self.noul_action = noul_action
        self.tools: Dict[str, ToolDefinition] = {}
        self.call_history: List[Dict[str, Any]] = []

        # Load existing audit history if present
        self.audit_log_path = "guardrail_audit.log"
        if os.path.exists(self.audit_log_path):
            try:
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.call_history.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Could not load audit log: {e}")

        # Register some common dangerous tools by default
        self._register_default_tools()

    def _register_default_tools(self):
        """Register some common tools with predefined risk levels"""
        dangerous_tools = [
            ToolDefinition("delete_file", "Delete a file", {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}, "high", True),
            ToolDefinition("execute_shell", "Execute shell command", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, "high", True),
            ToolDefinition("write_file", "Write content to a file", {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}, "medium", False),
            ToolDefinition("read_file", "Read content from a file", {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}, "low", False),
            ToolDefinition("network_request", "Make HTTP network request", {"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "data": {"type": "object"}}, "required": ["url", "method"]}, "medium", False),
        ]

        for tool in dangerous_tools:
            self.register_tool(tool)

    def register_tool(self, tool: ToolDefinition):
        """Register a tool definition with the guardrail"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (risk: {tool.risk_level})")

    def validate_tool_call(self, request: ToolCallRequest) -> GuardrailDecision:
        """
        Validate a tool call request using Jev

        Args:
            request: The tool call request to validate

        Returns:
            GuardrailDecision with the action to take
        """
        logger.info(f"Validating tool call: {request.tool_name}")

        # Check if tool is registered
        if request.tool_name not in self.tools:
            logger.warning(f"Unregistered tool: {request.tool_name}")
            # Still validate with Jev but note it's unregistered

        # Get Jev decision
        try:
            jev_decision = self.jev_client.validate_tool_call(
                agent_state=request.agent_state,
                tool_name=request.tool_name,
                tool_parameters=request.parameters,
                context=request.context
            )
        except Exception as e:
            logger.error(f"Error communicating with Jev: {e}")
            # Fail closed - block on error for safety
            return GuardrailDecision(
                action=ToolCallAction.BLOCK,
                reason=f"Guardrail error: {str(e)}",
                blocked_tool_call=request
            )

        # Record the call for audit/history
        self._record_call(request, jev_decision)

        # Make guardrail decision based on Jev's output
        return self._make_guardrail_decision(jev_decision, request)

    def _make_guardrail_decision(
        self,
        jev_decision: JevDecision,
        request: ToolCallRequest
    ) -> GuardrailDecision:
        """Convert Jev decision to guardrail action"""

        # Check for explicit approval
        if jev_decision.is_approved(self.approval_threshold):
            return GuardrailDecision(
                action=ToolCallAction.ALLOW,
                jev_decision=jev_decision,
                reason=f"Approved by Jev (confidence: {jev_decision.score:.2f})"
            )

        # Check for explicit rejection
        if jev_decision.is_rejected(self.rejection_threshold):
            return GuardrailDecision(
                action=ToolCallAction.BLOCK,
                jev_decision=jev_decision,
                reason=f"Rejected by Jev (confidence: {jev_decision.score:.2f})",
                blocked_tool_call=request
            )

        # Handle noul/uncertain cases
        if jev_decision.noul is not None:
            logger.warning(f"Jev uncertain: {jev_decision.noul}")
            if self.noul_action == ToolCallAction.REQUEST_CLARIFICATION:
                return GuardrailDecision(
                    action=ToolCallAction.REQUEST_CLARIFICATION,
                    jev_decision=jev_decision,
                    reason=f"Jev uncertain ({jev_decision.noul.value}) - clarification needed",
                    blocked_tool_call=request
                )
            elif self.noul_action == ToolCallAction.BLOCK:
                return GuardrailDecision(
                    action=ToolCallAction.BLOCK,
                    jev_decision=jev_decision,
                    reason=f"Jev uncertain ({jev_decision.noul.value}) - blocking for safety",
                    blocked_tool_call=request
                )

        # Handle suggested alternative
        if jev_decision.choice == JevChoice.SUGGEST_ALTERNATIVE and jev_decision.suggested_alternative:
            return GuardrailDecision(
                action=ToolCallAction.SUGGEST_ALTERNATIVE,
                jev_decision=jev_decision,
                reason=f"Jev suggested alternative: {jev_decision.suggested_alternative}",
                alternative_suggestion=jev_decision.suggested_alternative,
                blocked_tool_call=request
            )

        # Default to blocking for safety when uncertain
        return GuardrailDecision(
            action=ToolCallAction.BLOCK,
            jev_decision=jev_decision,
            reason=f"Unclear Jev decision - blocking for safety (choice: {jev_decision.choice}, score: {jev_decision.score:.2f})",
            blocked_tool_call=request
        )

    def execute_tool_call(
        self,
        request: ToolCallRequest,
        tool_executor: Callable[[ToolCallRequest], Any]
    ) -> Any:
        """
        Execute a tool call through the guardrail

        Args:
            request: The tool call request
            tool_executor: Function that actually executes the tool

        Returns:
            Result of tool execution or exception if blocked
        """
        # Validate the call
        decision = self.validate_tool_call(request)

        # Take action based on decision
        if decision.action == ToolCallAction.ALLOW:
            logger.info(f"Allowing tool call: {request.tool_name}")
            try:
                result = tool_executor(request)
                # Log successful execution
                logger.info(f"Tool call executed successfully: {request.tool_name}")
                return result
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                raise

        elif decision.action == ToolCallAction.BLOCK:
            logger.warning(f"Blocking tool call: {request.tool_name} - {decision.reason}")
            raise PermissionError(f"Guardrail blocked tool call: {decision.reason}")

        elif decision.action == ToolCallAction.SUGGEST_ALTERNATIVE:
            logger.info(f"Suggesting alternative for: {request.tool_name} - {decision.alternative_suggestion}")
            raise PermissionError(
                f"Guardrail suggests alternative: {decision.alternative_suggestion}. "
                f"Original call blocked: {decision.reason}"
            )

        elif decision.action == ToolCallAction.REQUEST_CLARIFICATION:
            logger.warning(f"Clarification requested for: {request.tool_name} - {decision.reason}")
            raise PermissionError(
                f"Guardrail requires clarification: {decision.reason}. "
                f"Please provide more context or rephrase the tool call."
            )

    def _record_call(self, request: ToolCallRequest, jev_decision: JevDecision):
        """Record tool call for audit/history"""
        entry = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "tool_name": request.tool_name,
            "parameters": request.parameters,
            "jev_choice": jev_decision.choice.value,
            "jev_score": jev_decision.score,
            "jev_noul": jev_decision.noul.value if jev_decision.noul else None,
            "context": request.context
        }
        self.call_history.append(entry)

        # Write to persistent audit log
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Could not write to audit log: {e}")

        # Keep history manageable
        if len(self.call_history) > 1000:
            self.call_history = self.call_history[-500:]

    def get_call_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent tool call history"""
        return self.call_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.call_history:
            return {"total_calls": 0}

        total = len(self.call_history)
        approved = sum(1 for call in self.call_history if call["jev_choice"] == "APPROVED" and call["jev_score"] >= self.approval_threshold)
        blocked = sum(1 for call in self.call_history if call["jev_choice"] == "REJECTED" and call["jev_score"] >= self.rejection_threshold)
        uncertain = sum(1 for call in self.call_history if call["jev_noul"] is not None)

        return {
            "total_calls": total,
            "approved": approved,
            "blocked": blocked,
            "uncertain": uncertain,
            "approval_rate": approved / total if total > 0 else 0,
            "block_rate": blocked / total if total > 0 else 0
        }


# Convenience function for quick setup
def create_guardrail(api_key: str, **kwargs) -> AgentSafetyGuardrail:
    """Create a guardrail with Jev client configured"""
    jev_client = JevClient(api_key=api_key)
    return AgentSafetyGuardrail(jev_client=jev_client, **kwargs)


# Example usage
if __name__ == "__main__":
    # Example setup
    guardrail = create_guardrail(api_key="your-jev-api-key-here")

    # Example tool executor function
    def example_tool_executor(request: ToolCallRequest) -> str:
        if request.tool_name == "delete_file":
            file_path = request.parameters.get("file_path", "unknown")
            return f"Deleted file: {file_path}"
        elif request.tool_name == "read_file":
            file_path = request.parameters.get("file_path", "unknown")
            return f"Contents of {file_path}: [file content]"
        else:
            return f"Executed {request.tool_name}"

    # Example agent state
    agent_state = {
        "user_role": "junior_developer",
        "current_task": "cleaning up temporary files",
        "permissions": ["read", "write"],
        "recent_actions": ["list_directory"],
        "risk_tolerance": "low"
    }

    # Test 1: Safe operation
    safe_request = ToolCallRequest(
        tool_name="read_file",
        parameters={"file_path": "/tmp/readme.txt"},
        agent_state=agent_state,
        context="User wants to read documentation file"
    )

    try:
        result = guardrail.execute_tool_call(safe_request, example_tool_executor)
        print(f"✅ Safe call result: {result}")
    except PermissionError as e:
        print(f"❌ Safe call blocked: {e}")

    # Test 2: Potentially dangerous operation
    dangerous_request = ToolCallRequest(
        tool_name="delete_file",
        parameters={"file_path": "/etc/passwd"},
        agent_state=agent_state,
        context="User wants to delete system file"
    )

    try:
        result = guardrail.execute_tool_call(dangerous_request, example_tool_executor)
        print(f"✅ Dangerous call result: {result}")
    except PermissionError as e:
        print(f"❌ Dangerous call blocked: {e}")

    # Print statistics
    print("\n📊 Guardrail Statistics:")
    stats = guardrail.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")