"""
Agent Management API Demo

This script demonstrates how to use the Agent Management API endpoints.

Usage:
    # Start the API server first:
    python -m src.api.server
    
    # Then run this demo:
    python examples/api_agents_demo.py
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api/v1"


def print_response(response: requests.Response, title: str = "Response"):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def demo_list_agents():
    """Demo: List all agents."""
    print("\n\n### Demo 1: List All Agents ###")
    response = requests.get(f"{BASE_URL}/agents")
    print_response(response, "List All Agents")
    
    # List with pagination
    print("\n\n### Demo 1.1: List with Pagination ###")
    response = requests.get(f"{BASE_URL}/agents?page=1&page_size=5")
    print_response(response, "List Agents (Page 1, Size 5)")


def demo_filter_agents():
    """Demo: Filter agents by category and tags."""
    print("\n\n### Demo 2: Filter Agents ###")
    
    # Filter by category
    response = requests.get(f"{BASE_URL}/agents?category=production")
    print_response(response, "Filter by Category: production")
    
    # Filter by tags
    response = requests.get(f"{BASE_URL}/agents?tags=memory")
    print_response(response, "Filter by Tags: memory")
    
    # Search agents
    response = requests.get(f"{BASE_URL}/agents?search=summarizer")
    print_response(response, "Search: summarizer")


def demo_get_agent():
    """Demo: Get agent details."""
    print("\n\n### Demo 3: Get Agent Details ###")
    
    # Get existing agent
    response = requests.get(f"{BASE_URL}/agents/mem_l1_summarizer")
    print_response(response, "Get Agent: mem_l1_summarizer")
    
    # Try to get non-existent agent
    response = requests.get(f"{BASE_URL}/agents/nonexistent_agent")
    print_response(response, "Get Non-existent Agent (Expected 404)")


def demo_create_agent():
    """Demo: Create a new agent."""
    print("\n\n### Demo 4: Create New Agent ###")
    
    new_agent = {
        "id": "demo_agent",
        "name": "Demo Agent",
        "category": "example",
        "environment": "demo",
        "owner": "demo-team",
        "version": "1.0.0",
        "location": "agents/demo_agent",
        "description": "A demo agent created via API",
        "tags": ["demo", "example", "api"]
    }
    
    response = requests.post(f"{BASE_URL}/agents", json=new_agent)
    print_response(response, "Create Agent")
    
    # Try to create duplicate
    response = requests.post(f"{BASE_URL}/agents", json=new_agent)
    print_response(response, "Create Duplicate Agent (Expected 409)")


def demo_update_agent():
    """Demo: Update agent metadata."""
    print("\n\n### Demo 5: Update Agent ###")
    
    # First create an agent to update
    new_agent = {
        "id": "update_demo_agent",
        "name": "Update Demo Agent",
        "category": "example",
        "environment": "demo",
        "owner": "demo-team",
        "version": "1.0.0",
        "location": "agents/update_demo_agent"
    }
    
    response = requests.post(f"{BASE_URL}/agents", json=new_agent)
    print_response(response, "Create Agent for Update Demo")
    
    # Update the agent
    update_data = {
        "version": "2.0.0",
        "description": "Updated via API",
        "tags": ["updated", "demo"]
    }
    
    response = requests.put(f"{BASE_URL}/agents/update_demo_agent", json=update_data)
    print_response(response, "Update Agent")
    
    # Verify the update
    response = requests.get(f"{BASE_URL}/agents/update_demo_agent")
    print_response(response, "Get Updated Agent")


def demo_full_workflow():
    """Demo: Complete workflow - create, list, update, get."""
    print("\n\n### Demo 6: Full Workflow ###")
    
    agent_id = "workflow_demo_agent"
    
    # Step 1: Create
    print("\nStep 1: Create Agent")
    new_agent = {
        "id": agent_id,
        "name": "Workflow Demo Agent",
        "category": "example",
        "environment": "demo",
        "owner": "demo-team",
        "version": "1.0.0",
        "location": f"agents/{agent_id}",
        "description": "Demonstrating full workflow",
        "tags": ["workflow", "demo"]
    }
    
    response = requests.post(f"{BASE_URL}/agents", json=new_agent)
    print(f"Created: {response.status_code == 201}")
    
    # Step 2: List and verify it's there
    print("\nStep 2: List Agents")
    response = requests.get(f"{BASE_URL}/agents")
    agents = response.json()["agents"]
    agent_ids = [a["id"] for a in agents]
    print(f"Agent in list: {agent_id in agent_ids}")
    
    # Step 3: Get details
    print("\nStep 3: Get Agent Details")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}")
    agent = response.json()
    print(f"Agent name: {agent['name']}")
    print(f"Agent version: {agent['version']}")
    
    # Step 4: Update
    print("\nStep 4: Update Agent")
    update_data = {
        "version": "2.0.0",
        "description": "Updated in workflow demo",
        "status": "experimental"
    }
    response = requests.put(f"{BASE_URL}/agents/{agent_id}", json=update_data)
    print(f"Updated: {response.status_code == 200}")
    
    # Step 5: Verify update
    print("\nStep 5: Verify Update")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}")
    agent = response.json()
    print(f"New version: {agent['version']}")
    print(f"New description: {agent['description']}")
    print(f"New status: {agent['status']}")


def main():
    """Run all demos."""
    print("="*60)
    print("Agent Management API Demo")
    print("="*60)
    print("\nMake sure the API server is running:")
    print("  python -m src.api.server")
    print("\nPress Enter to continue...")
    input()
    
    try:
        # Check if API is running
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            print("Error: API server is not responding correctly")
            return
        
        print("✓ API server is running")
        
        # Run demos
        demo_list_agents()
        demo_filter_agents()
        demo_get_agent()
        demo_create_agent()
        demo_update_agent()
        demo_full_workflow()
        
        print("\n\n" + "="*60)
        print("Demo Complete!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to API server")
        print("Please start the server with: python -m src.api.server")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
