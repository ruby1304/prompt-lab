"""
Async Execution API Demo

This script demonstrates how to use the async execution API endpoints
for agents and pipelines.

Requirements: 8.5
"""

import requests
import time
import json
from typing import Dict, Any, Optional


# API base URL
BASE_URL = "http://localhost:8000/api/v1"


def start_async_agent_execution(
    agent_id: str,
    flow_id: str = "default",
    inputs: Dict[str, Any] = None,
    config: Dict[str, Any] = None,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start an asynchronous agent execution.
    
    Args:
        agent_id: Agent identifier
        flow_id: Flow identifier (default: "default")
        inputs: Input parameters for the agent
        config: Optional configuration overrides
        callback_url: Optional webhook URL for completion notification
        
    Returns:
        Response with execution_id and status_url
    """
    url = f"{BASE_URL}/executions"
    
    payload = {
        "type": "agent",
        "target_id": agent_id,
        "inputs": inputs or {},
        "config": config or {"flow_id": flow_id}
    }
    
    if callback_url:
        payload["callback_url"] = callback_url
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


def start_async_pipeline_execution(
    pipeline_id: str,
    inputs: Dict[str, Any],
    config: Dict[str, Any] = None,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start an asynchronous pipeline execution.
    
    Args:
        pipeline_id: Pipeline identifier
        inputs: Input parameters for the pipeline
        config: Optional configuration overrides
        callback_url: Optional webhook URL for completion notification
        
    Returns:
        Response with execution_id and status_url
    """
    url = f"{BASE_URL}/executions"
    
    payload = {
        "type": "pipeline",
        "target_id": pipeline_id,
        "inputs": inputs,
        "config": config or {}
    }
    
    if callback_url:
        payload["callback_url"] = callback_url
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


def get_execution_status(execution_id: str) -> Dict[str, Any]:
    """
    Get the status of an execution.
    
    Args:
        execution_id: Execution identifier
        
    Returns:
        Execution status information
    """
    url = f"{BASE_URL}/executions/{execution_id}"
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def wait_for_execution(
    execution_id: str,
    poll_interval: float = 1.0,
    timeout: float = 300.0
) -> Dict[str, Any]:
    """
    Wait for an execution to complete.
    
    Args:
        execution_id: Execution identifier
        poll_interval: Polling interval in seconds
        timeout: Maximum wait time in seconds
        
    Returns:
        Final execution status
        
    Raises:
        TimeoutError: If execution doesn't complete within timeout
    """
    start_time = time.time()
    
    while True:
        status = get_execution_status(execution_id)
        
        # Check if completed
        if status["status"] in ["completed", "failed", "cancelled"]:
            return status
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Execution {execution_id} did not complete within {timeout}s")
        
        # Print progress if available
        if "progress" in status and status["progress"]:
            progress = status["progress"]
            print(f"Progress: {progress['percentage']:.1f}% "
                  f"({progress['current_step']}/{progress['total_steps']})")
            if progress.get("current_step_name"):
                print(f"  Current step: {progress['current_step_name']}")
        
        # Wait before next poll
        time.sleep(poll_interval)


def list_executions(
    status: Optional[str] = None,
    execution_type: Optional[str] = None,
    target_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    """
    List executions with optional filtering.
    
    Args:
        status: Filter by status (pending, running, completed, failed, cancelled)
        execution_type: Filter by type (agent, pipeline)
        target_id: Filter by target agent/pipeline ID
        page: Page number
        page_size: Items per page
        
    Returns:
        List of executions with pagination info
    """
    url = f"{BASE_URL}/executions"
    
    params = {
        "page": page,
        "page_size": page_size
    }
    
    if status:
        params["status"] = status
    if execution_type:
        params["type"] = execution_type
    if target_id:
        params["target_id"] = target_id
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


def cancel_execution(execution_id: str) -> Dict[str, Any]:
    """
    Cancel a running execution.
    
    Args:
        execution_id: Execution identifier
        
    Returns:
        Cancellation confirmation
    """
    url = f"{BASE_URL}/executions/{execution_id}/cancel"
    response = requests.post(url)
    response.raise_for_status()
    
    return response.json()


def demo_agent_execution():
    """Demo: Execute an agent asynchronously."""
    print("\n" + "="*60)
    print("Demo: Async Agent Execution")
    print("="*60)
    
    # Start execution
    print("\n1. Starting async agent execution...")
    result = start_async_agent_execution(
        agent_id="mem_l1_summarizer",
        flow_id="default",
        inputs={
            "text": "This is a test input for the memory summarizer agent."
        }
    )
    
    execution_id = result["execution_id"]
    print(f"   Execution started: {execution_id}")
    print(f"   Status: {result['status']}")
    print(f"   Status URL: {result['status_url']}")
    
    # Wait for completion
    print("\n2. Waiting for execution to complete...")
    try:
        final_status = wait_for_execution(execution_id, poll_interval=0.5, timeout=60)
        
        print(f"\n3. Execution completed!")
        print(f"   Status: {final_status['status']}")
        
        if final_status["status"] == "completed":
            print(f"   Outputs: {json.dumps(final_status.get('outputs', {}), indent=2)}")
        elif final_status["status"] == "failed":
            error = final_status.get("error", {})
            print(f"   Error: {error.get('message', 'Unknown error')}")
            
    except TimeoutError as e:
        print(f"\n   Timeout: {e}")
        print("   Cancelling execution...")
        cancel_result = cancel_execution(execution_id)
        print(f"   Cancelled: {cancel_result['message']}")


def demo_pipeline_execution():
    """Demo: Execute a pipeline asynchronously."""
    print("\n" + "="*60)
    print("Demo: Async Pipeline Execution")
    print("="*60)
    
    # Start execution
    print("\n1. Starting async pipeline execution...")
    result = start_async_pipeline_execution(
        pipeline_id="customer_service_flow",
        inputs={
            "customer_query": "How do I reset my password?"
        },
        config={
            "max_workers": 4
        }
    )
    
    execution_id = result["execution_id"]
    print(f"   Execution started: {execution_id}")
    print(f"   Status: {result['status']}")
    
    # Wait for completion
    print("\n2. Waiting for execution to complete...")
    try:
        final_status = wait_for_execution(execution_id, poll_interval=0.5, timeout=120)
        
        print(f"\n3. Execution completed!")
        print(f"   Status: {final_status['status']}")
        
        if final_status["status"] == "completed":
            outputs = final_status.get("outputs", {})
            print(f"   Final output: {json.dumps(outputs, indent=2)}")
        elif final_status["status"] == "failed":
            error = final_status.get("error", {})
            print(f"   Error: {error.get('message', 'Unknown error')}")
            
    except TimeoutError as e:
        print(f"\n   Timeout: {e}")


def demo_list_executions():
    """Demo: List and filter executions."""
    print("\n" + "="*60)
    print("Demo: List Executions")
    print("="*60)
    
    # List all executions
    print("\n1. Listing all executions...")
    result = list_executions(page=1, page_size=10)
    
    print(f"   Total executions: {result['pagination']['total_items']}")
    print(f"   Page: {result['pagination']['page']}/{result['pagination']['total_pages']}")
    
    for exec in result["executions"]:
        print(f"\n   - {exec['execution_id']}")
        print(f"     Type: {exec['type']}")
        print(f"     Target: {exec['target_id']}")
        print(f"     Status: {exec['status']}")
        print(f"     Started: {exec['started_at']}")
    
    # Filter by status
    print("\n2. Listing completed executions...")
    result = list_executions(status="completed", page_size=5)
    print(f"   Completed executions: {len(result['executions'])}")
    
    # Filter by type
    print("\n3. Listing pipeline executions...")
    result = list_executions(execution_type="pipeline", page_size=5)
    print(f"   Pipeline executions: {len(result['executions'])}")


def demo_cancel_execution():
    """Demo: Cancel a running execution."""
    print("\n" + "="*60)
    print("Demo: Cancel Execution")
    print("="*60)
    
    # Start a long-running execution
    print("\n1. Starting execution...")
    result = start_async_pipeline_execution(
        pipeline_id="customer_service_flow",
        inputs={"customer_query": "Test query"}
    )
    
    execution_id = result["execution_id"]
    print(f"   Execution started: {execution_id}")
    
    # Wait a bit
    print("\n2. Waiting 2 seconds...")
    time.sleep(2)
    
    # Cancel execution
    print("\n3. Cancelling execution...")
    cancel_result = cancel_execution(execution_id)
    print(f"   {cancel_result['message']}")
    print(f"   Cancelled at: {cancel_result['data']['cancelled_at']}")
    
    # Check status
    print("\n4. Checking final status...")
    status = get_execution_status(execution_id)
    print(f"   Status: {status['status']}")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("Async Execution API Demo")
    print("="*60)
    print("\nThis demo shows how to use the async execution API.")
    print("Make sure the API server is running on http://localhost:8000")
    
    try:
        # Check if API is available
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print("\nError: API server is not responding")
            return
        
        # Run demos
        demo_agent_execution()
        demo_pipeline_execution()
        demo_list_executions()
        demo_cancel_execution()
        
        print("\n" + "="*60)
        print("Demo completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to API server")
        print("Please start the server with: python -m src.api.server")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
