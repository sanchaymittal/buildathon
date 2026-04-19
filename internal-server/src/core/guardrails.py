"""
Guardrails Module - Provides security and safety guardrails for DevOps agent operations.

This module implements guardrails to prevent potentially harmful operations,
detect sensitive information, and ensure secure agent behavior.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

from agents import Agent, Runner, GuardrailFunctionOutput, RunContextWrapper
from agents import input_guardrail, output_guardrail

# Configure logging
logger = logging.getLogger(__name__)


class SecurityCheckOutput(BaseModel):
    """Output model for security check guardrail."""
    is_malicious: bool = Field(
        description="Whether the input is potentially malicious"
    )
    reasoning: str = Field(
        description="Reasoning for the security determination"
    )


class SensitiveInfoOutput(BaseModel):
    """Output model for sensitive information check guardrail."""
    contains_sensitive_info: bool = Field(
        description="Whether the output contains sensitive information"
    )
    reasoning: str = Field(
        description="Reasoning for the sensitive information determination"
    )


def check_security(input_text: str) -> SecurityCheckOutput:
    """
    Check if input text contains potentially malicious content.
    
    Args:
        input_text: The text to check
        
    Returns:
        SecurityCheckOutput with the check result
    """
    # List of potentially dangerous patterns
    dangerous_patterns = [
        r"rm\s+-rf\s+[/~]",  # Remove root or home directory
        r"dd\s+if=/dev/zero\s+of=/dev/[hs]d[a-z]",  # Disk wipe
        r":(){ :\|:& };:",  # Fork bomb
        r"wget\s+.+\s+\|\s+bash",  # Download and execute
        r"curl\s+.+\s+\|\s+bash",  # Download and execute
        r"sudo\s+rm\s+-rf\s+--no-preserve-root\s+/",  # Remove root with no preserve
        r"mkfs\s+/dev/[hs]d[a-z]",  # Format disk
        r"DROP\s+TABLE",  # SQL injection
        r"DELETE\s+FROM\s+.+\s+WHERE",  # SQL deletion
        r"shutdown\s+-h\s+now",  # Shutdown system
        r"halt",  # Halt system
        r"poweroff",  # Power off system
        r"sudo\s+passwd\s+root",  # Change root password
        r"chmod\s+-R\s+777\s+/",  # Change permissions on root
        r"chown\s+-R\s+[^:]+:[^:]+\s+/",  # Change ownership on root
    ]
    
    # Check for dangerous patterns
    for pattern in dangerous_patterns:
        if re.search(pattern, input_text, re.IGNORECASE):
            return SecurityCheckOutput(
                is_malicious=True,
                reasoning=f"Input contains potentially dangerous command pattern: {pattern}"
            )
    
    # Check for dangerous Docker options
    if re.search(r"--privileged", input_text):
        return SecurityCheckOutput(
            is_malicious=True,
            reasoning="Input contains --privileged flag which grants full container access"
        )
    
    if re.search(r"--network\s+=?\s*host", input_text):
        return SecurityCheckOutput(
            is_malicious=True,
            reasoning="Input uses host network which bypasses container isolation"
        )
    
    if re.search(r"volume.*:/|bind.*:/", input_text, re.IGNORECASE):
        if re.search(r":/", input_text):
            check_paths = re.findall(r"([^\\s]*:/[^\\s]*)", input_text)
            for p in check_paths:
                if p.startswith("/host") or p.startswith("/root") or p.startswith("/etc"):
                    return SecurityCheckOutput(
                        is_malicious=True,
                        reasoning=f"Input mounts sensitive path: {p}"
                    )
    
    # Check for GitHub tokens
    if re.search(r"(github_token|GITHUB_TOKEN|ghp_[a-zA-Z0-9]{36})", input_text):
        return SecurityCheckOutput(
            is_malicious=True,
            reasoning="Input contains GitHub token information"
        )
    
    # Check for private keys
    if re.search(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----", input_text):
        return SecurityCheckOutput(
            is_malicious=True,
            reasoning="Input contains private key information"
        )
    
    # If no dangerous patterns found, return safe
    return SecurityCheckOutput(
        is_malicious=False,
        reasoning="Input does not contain any known dangerous patterns"
    )


def check_sensitive_info(output_text: str) -> SensitiveInfoOutput:
    """
    Check if output text contains sensitive information.
    
    Args:
        output_text: The text to check
        
    Returns:
        SensitiveInfoOutput with the check result
    """
    # Patterns for sensitive information
    sensitive_patterns = [
        # Docker credentials
        r"(DOCKER_[A-Z_]+)",  # Docker env vars
        
        # GitHub tokens
        r"(github_pat_[a-zA-Z0-9_]{22,})",
        r"(ghp_[a-zA-Z0-9]{36})",
        
        # Private keys
        r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----",
        
        # IP addresses (internal)
        r"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})",
        r"(172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})",
        r"(192\.168\.\d{1,3}\.\d{1,3})",
        
        # Passwords
        r"(password|passwd|pwd)[\s:=]+[^\s]+",
        
        # API keys
        r"(api[_-]?key|apikey)[\s:=]+[^\s]+",
        
        # Database connection strings
        r"(jdbc:|\bdb_connection|\bconnection_string)",
    ]
    
    # Check for sensitive patterns
    for pattern in sensitive_patterns:
        match = re.search(pattern, output_text, re.IGNORECASE)
        if match:
            return SensitiveInfoOutput(
                contains_sensitive_info=True,
                reasoning=f"Output contains sensitive information matching pattern: {pattern}"
            )
    
    # If no sensitive patterns found, return safe
    return SensitiveInfoOutput(
        contains_sensitive_info=False,
        reasoning="Output does not contain any known sensitive information patterns"
    )


@input_guardrail
async def security_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    input_text: str
) -> GuardrailFunctionOutput:
    """
    Security guardrail to prevent potentially harmful operations.
    
    Args:
        ctx: Run context
        agent: The agent being used
        input_text: The input text to check
        
    Returns:
        GuardrailFunctionOutput with the check result
    """
    logger.info("Running security guardrail check")
    
    # Check for potentially malicious content
    check_result = check_security(input_text)
    
    # Log the result
    if check_result.is_malicious:
        logger.warning(f"Security guardrail triggered: {check_result.reasoning}")
    else:
        logger.info("Security guardrail check passed")
    
    # Return the result
    return GuardrailFunctionOutput(
        tripwire_triggered=check_result.is_malicious,
        output_info=check_result
    )


@output_guardrail
async def sensitive_info_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    output_text: str
) -> GuardrailFunctionOutput:
    """
    Sensitive information guardrail to prevent leaking sensitive data.
    
    Args:
        ctx: Run context
        agent: The agent being used
        output_text: The output text to check
        
    Returns:
        GuardrailFunctionOutput with the check result
    """
    logger.info("Running sensitive information guardrail check")
    
    # Check for sensitive information
    check_result = check_sensitive_info(output_text)
    
    # Log the result
    if check_result.contains_sensitive_info:
        logger.warning(f"Sensitive information guardrail triggered: {check_result.reasoning}")
    else:
        logger.info("Sensitive information guardrail check passed")
    
    # Return the result
    return GuardrailFunctionOutput(
        tripwire_triggered=check_result.contains_sensitive_info,
        output_info=check_result
    )