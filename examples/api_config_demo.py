"""
Configuration API Demo

This script demonstrates how to use the Configuration API endpoints
to read and update agent and pipeline configuration files.

Requirements: 8.4
"""

import requests
import json
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


def get_agent_config(agent_id: str) -> Dict[str, Any]:
    """
    Read agent configuration.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Agent configuration response
    """
    response = requests.get(f"{BASE_URL}/config/agents/{agent_id}")
    response.raise_for_status()
    return response.json()


def update_agent_config(agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update agent configuration.
    
    Args:
        agent_id: Agent identifier
        config: New configuration dictionary
        
    Returns:
        Update response
    """
    response = requests.put(
        f"{BASE_URL}/config/agents/{agent_id}",
        json={"config": config}
    )
    response.raise_for_status()
    return response.json()


def get_pipeline_config(pipeline_id: str) -> Dict[str, Any]:
    """
    Read pipeline configuration.
    
    Args:
        pipeline_id: Pipeline identifier
        
    Returns:
        Pipeline configuration response
    """
    response = requests.get(f"{BASE_URL}/config/pipelines/{pipeline_id}")
    response.raise_for_status()
    return response.json()


def update_pipeline_config(pipeline_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update pipeline configuration.
    
    Args:
        pipeline_id: Pipeline identifier
        config: New configuration dictionary
        
    Returns:
        Update response
    """
    response = requests.put(
        f"{BASE_URL}/config/pipelines/{pipeline_id}",
        json={"config": config}
    )
    response.raise_for_status()
    return response.json()


def demo_agent_config():
    """Demonstrate agent configuration management."""
    print("=" * 60)
    print("Agent Configuration Demo")
    print("=" * 60)
    
    agent_id = "mem_l1_summarizer"
    
    # Read current configuration
    print(f"\n1. Reading configuration for agent: {agent_id}")
    try:
        result = get_agent_config(agent_id)
        print(f"   ✓ Successfully read configuration")
        print(f"   File: {result['file_path']}")
        print(f"   Last modified: {result['last_modified']}")
        print(f"   Model: {result['config'].get('model', 'N/A')}")
        
        # Store original config
        original_config = result['config'].copy()
        
        # Update configuration
        print(f"\n2. Updating configuration...")
        updated_config = original_config.copy()
        updated_config['temperature'] = 0.8
        updated_config['_demo_field'] = 'This is a demo update'
        
        update_result = update_agent_config(agent_id, updated_config)
        print(f"   ✓ {update_result['message']}")
        
        # Read updated configuration
        print(f"\n3. Verifying update...")
        result = get_agent_config(agent_id)
        if result['config'].get('_demo_field') == 'This is a demo update':
            print(f"   ✓ Configuration updated successfully")
        
        # Restore original configuration
        print(f"\n4. Restoring original configuration...")
        update_agent_config(agent_id, original_config)
        print(f"   ✓ Configuration restored")
        
    except requests.exceptions.HTTPError as e:
        print(f"   ✗ Error: {e.response.status_code} - {e.response.json()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def demo_pipeline_config():
    """Demonstrate pipeline configuration management."""
    print("\n" + "=" * 60)
    print("Pipeline Configuration Demo")
    print("=" * 60)
    
    pipeline_id = "customer_service_flow"
    
    # Read current configuration
    print(f"\n1. Reading configuration for pipeline: {pipeline_id}")
    try:
        result = get_pipeline_config(pipeline_id)
        print(f"   ✓ Successfully read configuration")
        print(f"   File: {result['file_path']}")
        print(f"   Last modified: {result['last_modified']}")
        print(f"   Name: {result['config'].get('name', 'N/A')}")
        print(f"   Version: {result['config'].get('version', 'N/A')}")
        print(f"   Steps: {len(result['config'].get('steps', []))}")
        
        # Store original config
        original_config = result['config'].copy()
        
        # Update configuration
        print(f"\n2. Updating configuration...")
        updated_config = original_config.copy()
        updated_config['description'] = 'Updated via API demo'
        updated_config['_demo_timestamp'] = '2024-12-17T10:00:00Z'
        
        update_result = update_pipeline_config(pipeline_id, updated_config)
        print(f"   ✓ {update_result['message']}")
        
        # Read updated configuration
        print(f"\n3. Verifying update...")
        result = get_pipeline_config(pipeline_id)
        if result['config'].get('_demo_timestamp'):
            print(f"   ✓ Configuration updated successfully")
        
        # Restore original configuration
        print(f"\n4. Restoring original configuration...")
        update_pipeline_config(pipeline_id, original_config)
        print(f"   ✓ Configuration restored")
        
    except requests.exceptions.HTTPError as e:
        print(f"   ✗ Error: {e.response.status_code} - {e.response.json()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("Error Handling Demo")
    print("=" * 60)
    
    # Test non-existent agent
    print("\n1. Testing non-existent agent...")
    try:
        get_agent_config("nonexistent_agent")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"   ✓ Correctly returned 404 Not Found")
            error_detail = e.response.json()['detail']
            print(f"   Error: {error_detail['message']}")
    
    # Test non-existent pipeline
    print("\n2. Testing non-existent pipeline...")
    try:
        get_pipeline_config("nonexistent_pipeline")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"   ✓ Correctly returned 404 Not Found")
            error_detail = e.response.json()['detail']
            print(f"   Error: {error_detail['message']}")
    
    # Test invalid configuration data
    print("\n3. Testing invalid configuration data...")
    try:
        # This will fail Pydantic validation (422)
        response = requests.put(
            f"{BASE_URL}/config/agents/mem_l1_summarizer",
            json={"config": "not a dictionary"}
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            print(f"   ✓ Correctly returned 422 Unprocessable Entity")
            print(f"   Pydantic validation rejected invalid data")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Configuration API Demo")
    print("=" * 60)
    print("\nThis demo shows how to use the Configuration API to:")
    print("- Read agent and pipeline configurations")
    print("- Update configurations")
    print("- Handle errors gracefully")
    print("\nMake sure the API server is running on http://localhost:8000")
    print("=" * 60)
    
    try:
        # Test if API is available
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code == 200:
            print("\n✓ API server is running")
        else:
            print("\n✗ API server returned unexpected status")
            return
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to API server")
        print("Please start the server with: python -m src.api.server")
        return
    
    # Run demos
    demo_agent_config()
    demo_pipeline_config()
    demo_error_handling()
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
