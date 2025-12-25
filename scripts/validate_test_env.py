#!/usr/bin/env python3
"""
Test Environment Validation Script

This script validates that the test environment is properly configured
for running integration tests with Doubao Pro API.

Usage:
    python scripts/validate_test_env.py
    python scripts/validate_test_env.py --env-file .env.test
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def check_env_file(env_file: Path) -> bool:
    """Check if environment file exists"""
    if not env_file.exists():
        print_error(f"Environment file not found: {env_file}")
        print_info(f"Please create {env_file} based on .env.example")
        return False
    
    print_success(f"Environment file found: {env_file}")
    return True


def load_env_file(env_file: Path) -> bool:
    """Load environment variables from file"""
    try:
        load_dotenv(env_file, override=True)
        print_success(f"Loaded environment variables from {env_file}")
        return True
    except Exception as e:
        print_error(f"Failed to load environment file: {e}")
        return False


def check_required_vars() -> Tuple[bool, List[str]]:
    """Check if all required environment variables are set"""
    required_vars = [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL_NAME"
    ]
    
    missing_vars = []
    configured_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here":
            missing_vars.append(var)
            print_error(f"{var} is not configured")
        else:
            configured_vars.append(var)
            # Mask API key for security
            if "KEY" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print_success(f"{var} = {masked_value}")
            else:
                print_success(f"{var} = {value}")
    
    return len(missing_vars) == 0, missing_vars


def check_optional_vars():
    """Check optional environment variables"""
    optional_vars = {
        "OPENAI_TEMPERATURE": "0.3",
        "OPENAI_MAX_TOKENS": "2000",
        "TEST_TIMEOUT": "60",
        "TEST_MAX_RETRIES": "3",
        "LOG_LEVEL": "INFO"
    }
    
    print_info("\nOptional configuration:")
    for var, default in optional_vars.items():
        value = os.getenv(var, default)
        print(f"  {var} = {value}")


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key:
        return False
    
    # Basic validation - should not be placeholder
    if api_key in ["your_api_key_here", "your_doubao_api_key_here"]:
        print_error("API key is still a placeholder value")
        return False
    
    # Check minimum length
    if len(api_key) < 10:
        print_warning("API key seems too short - please verify")
        return False
    
    print_success("API key format looks valid")
    return True


def validate_model_name(model_name: str) -> bool:
    """Validate model name"""
    if not model_name:
        print_error("Model name is not set")
        return False
    
    # Check if it's a Doubao model
    if "doubao" not in model_name.lower():
        print_warning(f"Model name '{model_name}' does not contain 'doubao'")
        print_info("Expected a Doubao Pro model like 'doubao-1-5-pro-32k-250115'")
        return False
    
    print_success(f"Model name '{model_name}' looks valid")
    return True


def validate_api_endpoint(endpoint: str) -> bool:
    """Validate API endpoint"""
    if not endpoint:
        print_error("API endpoint is not set")
        return False
    
    # Check if it's a valid URL
    if not endpoint.startswith(("http://", "https://")):
        print_error(f"API endpoint '{endpoint}' is not a valid URL")
        return False
    
    # Check if it's the Doubao endpoint
    if "volces.com" in endpoint:
        print_success(f"API endpoint '{endpoint}' is a Doubao endpoint")
        return True
    else:
        print_warning(f"API endpoint '{endpoint}' is not a standard Doubao endpoint")
        print_info("Expected: https://ark.cn-beijing.volces.com/api/v3")
        return True  # Still valid, just not standard


def test_api_connection() -> bool:
    """Test API connection with a simple request"""
    print_info("\nTesting API connection...")
    
    try:
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model_name = os.getenv("OPENAI_MODEL_NAME")
        
        # Create a simple LLM instance
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.3,
            max_tokens=50
        )
        
        # Try a simple invocation
        print_info("Sending test request to API...")
        response = llm.invoke("Say 'Hello' in one word.")
        
        if response and response.content:
            print_success(f"API connection successful! Response: {response.content[:50]}")
            return True
        else:
            print_error("API returned empty response")
            return False
            
    except ImportError as e:
        print_warning(f"Cannot test API connection: {e}")
        print_info("Install langchain-openai to enable API testing: pip install langchain-openai")
        return True  # Don't fail if dependencies are missing
        
    except Exception as e:
        print_error(f"API connection failed: {e}")
        print_info("Please verify your API credentials and endpoint")
        return False


def check_test_directories():
    """Check if test directories exist"""
    print_info("\nChecking test directories...")
    
    directories = [
        "tests/fixtures",
        "tests/output",
        "tests/.cache"
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        if path.exists():
            print_success(f"Directory exists: {dir_path}")
        else:
            print_warning(f"Directory not found: {dir_path}")
            print_info(f"Creating directory: {dir_path}")
            try:
                path.mkdir(parents=True, exist_ok=True)
                print_success(f"Created directory: {dir_path}")
            except Exception as e:
                print_error(f"Failed to create directory: {e}")


def print_summary(all_checks_passed: bool, missing_vars: List[str]):
    """Print validation summary"""
    print_header("Validation Summary")
    
    if all_checks_passed:
        print_success("All validation checks passed!")
        print_info("\nYou can now run integration tests with:")
        print(f"  {Colors.BOLD}pytest tests/ -m integration{Colors.RESET}")
        print(f"  {Colors.BOLD}pytest tests/ -v{Colors.RESET}")
        return 0
    else:
        print_error("Some validation checks failed")
        
        if missing_vars:
            print_info("\nMissing required environment variables:")
            for var in missing_vars:
                print(f"  - {var}")
            
            print_info("\nPlease configure these variables in your .env.test file")
            print_info("You can copy from .env.example and update the values")
        
        return 1


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description="Validate test environment configuration"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env.test"),
        help="Path to environment file (default: .env.test)"
    )
    parser.add_argument(
        "--skip-api-test",
        action="store_true",
        help="Skip API connection test"
    )
    
    args = parser.parse_args()
    
    print_header("Test Environment Validation")
    
    # Check if env file exists
    if not check_env_file(args.env_file):
        return 1
    
    # Load environment variables
    if not load_env_file(args.env_file):
        return 1
    
    # Check required variables
    print_info("\nChecking required environment variables:")
    vars_ok, missing_vars = check_required_vars()
    
    # Check optional variables
    check_optional_vars()
    
    # Validate configuration values
    print_info("\nValidating configuration values:")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model_name = os.getenv("OPENAI_MODEL_NAME", "")
    endpoint = os.getenv("OPENAI_BASE_URL", "")
    
    key_valid = validate_api_key_format(api_key)
    model_valid = validate_model_name(model_name)
    endpoint_valid = validate_api_endpoint(endpoint)
    
    config_valid = key_valid and model_valid and endpoint_valid
    
    # Test API connection
    api_test_passed = True
    if not args.skip_api_test and vars_ok and config_valid:
        api_test_passed = test_api_connection()
    elif args.skip_api_test:
        print_info("\nSkipping API connection test (--skip-api-test)")
    
    # Check test directories
    check_test_directories()
    
    # Print summary
    all_checks_passed = vars_ok and config_valid and api_test_passed
    return print_summary(all_checks_passed, missing_vars)


if __name__ == "__main__":
    sys.exit(main())
