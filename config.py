"""
Configuration for Jev Agent Safety Guardrail
"""

import os
from typing import Optional
from dataclasses import dataclass
from jev_client import JevClient
from guardrail import AgentSafetyGuardrail


@dataclass
class GuardrailConfig:
    """Configuration settings for the agent safety guardrail"""
    # Jev API settings
    jev_api_key: str = os.getenv("JEV_API_KEY", "your_jev_api_key_here")
    jev_api_url: str = "https://api.jevmodel.org/v1"

    # Guardrail behavior
    approval_threshold: float = 0.7
    rejection_threshold: float = 0.6
    noul_action: str = "request_clarification"  # request_clarification, block, suggest_alternative

    # Logging
    log_level: str = "INFO"
    enable_audit_log: bool = True
    audit_log_file: str = "guardrail_audit.log"

    # Safety defaults
    fail_closed: bool = True  # Block on errors if True
    require_registration: bool = False  # Require tools to be registered

    @classmethod
    def from_env(cls) -> 'GuardrailConfig':
        """Create configuration from environment variables"""
        return cls(
            jev_api_key=os.getenv("JEV_API_KEY", ""),
            jev_api_url=os.getenv("JEV_API_URL", "https://api.jevmodel.org/v1"),
            approval_threshold=float(os.getenv("GUARDRAIL_APPROVAL_THRESHOLD", "0.7")),
            rejection_threshold=float(os.getenv("GUARDRAIL_REJECTION_THRESHOLD", "0.6")),
            noul_action=os.getenv("GUARDRAIL_NOUL_ACTION", "request_clarification"),
            log_level=os.getenv("GUARDRAIL_LOG_LEVEL", "INFO"),
            enable_audit_log=os.getenv("GUARDRAIL_ENABLE_AUDIT_LOG", "true").lower() == "true",
            audit_log_file=os.getenv("GUARDRAIL_AUDIT_LOG_FILE", "guardrail_audit.log"),
            fail_closed=os.getenv("GUARDRAIL_FAIL_CLOSED", "true").lower() == "true",
            require_registration=os.getenv("GUARDRAIL_REQUIRE_REGISTRATION", "false").lower() == "true"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "jev_api_key": "***" if self.jev_api_key else "",  # Mask API key
            "jev_api_url": self.jev_api_url,
            "approval_threshold": self.approval_threshold,
            "rejection_threshold": self.rejection_threshold,
            "noul_action": self.noul_action,
            "log_level": self.log_level,
            "enable_audit_log": self.enable_audit_log,
            "audit_log_file": self.audit_log_file,
            "fail_closed": self.fail_closed,
            "require_registration": self.require_registration
        }


def create_guardrail_from_config(config: GuardrailConfig) -> AgentSafetyGuardrail:
    """Create a guardrail instance from configuration"""
    # Setup logging
    import logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create Jev client
    jev_client = JevClient(
        api_key=config.jev_api_key,
        api_url=config.jev_api_url
    )

    # Create guardrail
    guardrail = AgentSafetyGuardrail(
        jev_client=jev_client,
        approval_threshold=config.approval_threshold,
        rejection_threshold=config.rejection_threshold,
        noul_action=config.noul_action
    )

    return guardrail


def create_guardrail_from_env() -> AgentSafetyGuardrail:
    """Create guardrail from environment variables"""
    config = GuardrailConfig.from_env()
    return create_guardrail_from_config(config)


# Example configuration template
CONFIG_TEMPLATE = """
# Jev Agent Safety Guardrail Configuration
# Copy this to .env or set environment variables

# Jev API Settings (get your free API key from https://jevmodel.org/)
JEV_API_KEY=your-jev-api-key-here
JEV_API_URL=https://api.jevmodel.org/v1

# Guardrail Behavior
GUARDRAIL_APPROVAL_THRESHOLD=0.7
GUARDRAIL_REJECTION_THRESHOLD=0.6
GUARDRAIL_NOUL_ACTION=request_clarification  # options: request_clarification, block, suggest_alternative

# Logging
GUARDRAIL_LOG_LEVEL=INFO
GUARDRAIL_ENABLE_AUDIT_LOG=true
GUARDRAIL_AUDIT_LOG_FILE=guardrail_audit.log

# Safety Settings
GUARDRAIL_FAIL_CLOSED=true
GUARDRAIL_REQUIRE_REGISTRATION=false
"""


def write_config_template(filepath: str = ".env.template"):
    """Write configuration template to file"""
    with open(filepath, 'w') as f:
        f.write(CONFIG_TEMPLATE.strip())
    print(f"Configuration template written to {filepath}")


if __name__ == "__main__":
    # Example usage
    print("🔧 Jev Agent Safety Guardrail Configuration")
    print("=" * 50)

    # Show template
    print("\n📝 Configuration Template (.env):")
    print(CONFIG_TEMPLATE.strip())

    # Write template file
    write_config_template()

    # Show how to use
    print("\n🚀 Usage Examples:")
    print("1. Set environment variables:")
    print("   export JEV_API_KEY=\"your-api-key-here\"")
    print("   export GUARDRAIL_APPROVAL_THRESHOLD=0.8")
    print("")
    print("2. Or create config object:")
    print("   from config import GuardrailConfig, create_guardrail_from_config")
    print("   config = GuardrailConfig(jev_api_key=\"your-key-here\")")
    print("   guardrail = create_guardrail_from_config(config)")