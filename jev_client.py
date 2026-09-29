"""
Jev API Client Wrapper
Handles communication with TypeSafe AI's Jev API for structured decision-making.
"""

import json
import requests
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum


class JevChoice(str, Enum):
    """Possible choice outputs from Jev"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUGGEST_ALTERNATIVE = "SUGGEST_ALTERNATIVE"


class JevNoul(str, Enum):
    """Noul indicates uncertainty/no decision"""
    UNCERTAIN = "UNCERTAIN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"


@dataclass
class JevDecision:
    """Structured decision returned by Jev"""
    choice: JevChoice
    score: float  # Confidence score 0.0-1.0
    noul: Optional[JevNoul] = None
    suggested_alternative: Optional[str] = None
    reasoning: Optional[str] = None  # Optional explanation from Jev

    def is_approved(self, threshold: float = 0.7) -> bool:
        """Check if decision is approved with sufficient confidence"""
        return (self.choice == JevChoice.APPROVED and
                self.score >= threshold and
                self.noul is None)

    def is_rejected(self, threshold: float = 0.6) -> bool:
        """Check if decision is rejected with sufficient confidence"""
        return (self.choice == JevChoice.REJECTED and
                self.score >= threshold)


class JevClient:
    """Client for interacting with Jev API"""

    def __init__(self, api_key: str, api_url: str = "https://api.jevmodel.org/v1", mock_mode: bool = True):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.mock_mode = mock_mode
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _simulate_decision(
        self,
        agent_state: Dict[str, Any],
        tool_name: str,
        tool_parameters: Dict[str, Any],
        context: Optional[str] = None
    ) -> JevDecision:
        """Simulate realistic Jev model evaluation for local testing and demonstration"""
        permissions = [str(p).lower() for p in agent_state.get("permissions", [])]
        user_role = str(agent_state.get("user_role", "")).lower()
        tool = tool_name.lower().strip()
        params = tool_parameters or {}
        file_path = str(params.get("file_path", "")).lower().replace("\\", "/")
        command = str(params.get("command", "")).lower()

        # Sensitive files / credentials
        sensitive_paths = ["id_rsa", ".ssh", "shadow", "passwd", "sam", "system32/config", ".env", "secrets"]
        is_sensitive = any(s in file_path for s in sensitive_paths)

        # Dangerous commands
        dangerous_cmds = ["rm -rf", "curl ", "wget ", "bash ", "drop table", "drop database", "format ", "powershell -enc"]
        is_dangerous_cmd = any(d in command for d in dangerous_cmds)

        if tool in ["read_file", "file_read", "read"]:
            if is_sensitive:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.96,
                    reasoning="Access to sensitive credentials or system file rejected for safety."
                )
            if "read" in permissions or user_role in ["developer", "data_scientist", "system_administrator", "admin", "user"]:
                return JevDecision(
                    choice=JevChoice.APPROVED,
                    score=0.94,
                    reasoning=f"Read operation approved for '{params.get('file_path', 'file')}'. Safe path within agent permissions."
                )
            else:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.88,
                    reasoning="Agent lacks 'read' permission in current state."
                )

        elif tool in ["delete_file", "file_delete", "delete", "remove_file"]:
            if "delete" not in permissions and user_role not in ["system_administrator", "admin"]:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.95,
                    suggested_alternative="read_file",
                    reasoning="Destructive file deletion rejected. Agent does not have delete privileges."
                )
            if is_sensitive:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.98,
                    reasoning="Deletion of critical system/credential files is strictly prohibited."
                )
            return JevDecision(
                choice=JevChoice.APPROVED,
                score=0.85,
                reasoning="File deletion permitted for privileged administrator role."
            )

        elif tool in ["execute_shell", "shell_execute", "run_command", "bash"]:
            if is_dangerous_cmd:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.97,
                    reasoning="Dangerous shell command detected (possible remote code execution or data destruction)."
                )
            if "execute" in permissions or user_role in ["developer", "system_administrator"]:
                return JevDecision(
                    choice=JevChoice.APPROVED,
                    score=0.90,
                    reasoning="Shell command approved for execution."
                )
            else:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.89,
                    reasoning="Agent lacks execute permission for shell commands."
                )

        elif tool in ["write_file", "file_write", "write"]:
            if is_sensitive:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.95,
                    reasoning="Modification of sensitive system files is blocked."
                )
            if "write" in permissions or user_role in ["developer", "data_scientist", "system_administrator"]:
                return JevDecision(
                    choice=JevChoice.APPROVED,
                    score=0.91,
                    reasoning="File write permitted by agent state policy."
                )
            else:
                return JevDecision(
                    choice=JevChoice.REJECTED,
                    score=0.87,
                    reasoning="Agent lacks write permissions."
                )

        # Default fallback
        if "read" in permissions and "read" in tool:
            return JevDecision(choice=JevChoice.APPROVED, score=0.85, reasoning="Read action approved based on agent state.")

        return JevDecision(
            choice=JevChoice.REJECTED,
            score=0.80,
            reasoning=f"Tool '{tool_name}' not permitted for current agent role and permissions."
        )

    def validate_tool_call(
        self,
        agent_state: Dict[str, Any],
        tool_name: str,
        tool_parameters: Dict[str, Any],
        context: Optional[str] = None
    ) -> JevDecision:
        """
        Send tool call validation request to Jev API (or local simulation if offline)

        Args:
            agent_state: Current state of the AI agent
            tool_name: Name of the tool being called
            tool_parameters: Parameters for the tool call
            context: Additional context about the situation

        Returns:
            JevDecision object with structured decision
        """
        if self.mock_mode:
            return self._simulate_decision(agent_state, tool_name, tool_parameters, context)

        payload = {
            "state": agent_state,
            "query": {
                "tool_name": tool_name,
                "parameters": tool_parameters,
                "context": context or ""
            },
            "task": "tool_call_validation",
            "output_format": {
                "choice": ["APPROVED", "REJECTED", "SUGGEST_ALTERNATIVE"],
                "score": {"min": 0.0, "max": 1.0},
                "noul": ["UNCERTAIN", "INSUFFICIENT_DATA", "CONFLICTING_INFORMATION"],
                "suggested_alternative": "string",
                "reasoning": "string"
            }
        }

        try:
            response = requests.post(
                f"{self.api_url}/decision",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            return JevDecision(
                choice=JevChoice(result.get("choice", "REJECTED")),
                score=float(result.get("score", 0.0)),
                noul=JevNoul(result.get("noul")) if result.get("noul") else None,
                suggested_alternative=result.get("suggested_alternative"),
                reasoning=result.get("reasoning")
            )

        except requests.exceptions.RequestException as e:
            # Fallback to local safety evaluation when API endpoint is unreachable
            print(f"Jev API unreachable ({e}). Using local safety simulation.")
            decision = self._simulate_decision(agent_state, tool_name, tool_parameters, context)
            decision.reasoning = f"(Local Safety Engine) {decision.reasoning or ''}"
            return decision
        except (KeyError, ValueError, TypeError) as e:
            # Fallback on parsing error
            print(f"Jev response parsing error: {e}. Defaulting to REJECTED for safety.")
            return JevDecision(
                choice=JevChoice.REJECTED,
                score=0.85,
                reasoning=f"Response parsing error: {str(e)}"
            )

    def health_check(self) -> bool:
        """Check if Jev API is accessible or simulation mode is enabled"""
        if self.mock_mode:
            return True
        try:
            response = requests.get(
                f"{self.api_url}/health",
                headers=self.headers,
                timeout=3
            )
            return response.status_code == 200
        except:
            return False


# Example usage
if __name__ == "__main__":
    # This is just for demonstration - in practice, get API key from environment/config
    client = JevClient(api_key="your-jev-api-key-here")

    # Example agent state
    state = {
        "user_role": "developer",
        "current_task": "cleaning up temporary files",
        "permissions": ["read", "write"],
        "recent_actions": ["list_directory", "read_file"],
        "risk_tolerance": "medium"
    }

    # Example tool call to validate
    decision = client.validate_tool_call(
        agent_state=state,
        tool_name="delete_file",
        tool_parameters={"file_path": "/tmp/some_temp_file.txt"},
        context="User wants to clean up temporary files in /tmp directory"
    )

    print(f"Jev Decision: {decision.choice} (confidence: {decision.score:.2f})")
    if decision.reasoning:
        print(f"Reasoning: {decision.reasoning}")
    if decision.suggested_alternative:
        print(f"Suggested alternative: {decision.suggested_alternative}")

    if decision.is_approved():
        print("✅ Tool call APPROVED")
    elif decision.is_rejected():
        print("❌ Tool call REJECTED")
    else:
        print("⚠️  Tool call requires review")