"""
API Demo Script

This script demonstrates how to interact with the Prompt Lab API.
It shows basic API usage including health checks and error handling.

Usage:
    # Start the API server first:
    python -m src.api.server
    
    # Then run this demo in another terminal:
    python examples/api_demo.py
"""

import requests
import json
from typing import Dict, Any


class PromptLabAPIClient:
    """Simple client for interacting with the Prompt Lab API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Dict containing health status information
        """
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_root(self) -> Dict[str, Any]:
        """
        Get root API information.
        
        Returns:
            Dict containing API information
        """
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()
        return response.json()


def main():
    """Run the API demo."""
    print("=" * 60)
    print("Prompt Lab API Demo")
    print("=" * 60)
    print()
    
    # Initialize client
    client = PromptLabAPIClient()
    
    # Test 1: Health Check
    print("Test 1: Health Check")
    print("-" * 60)
    try:
        health = client.health_check()
        print(f"✓ API Status: {health['status']}")
        print(f"  Service: {health['service']}")
        print(f"  Version: {health['version']}")
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to API server")
        print("  Make sure the server is running:")
        print("  python -m src.api.server")
        return
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    print()
    
    # Test 2: Root Endpoint
    print("Test 2: Root Endpoint")
    print("-" * 60)
    try:
        root = client.get_root()
        print(f"✓ Message: {root['message']}")
        print(f"  Version: {root['version']}")
        print(f"  Documentation: {root['docs']}")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()
    
    # Test 3: OpenAPI Documentation
    print("Test 3: OpenAPI Documentation")
    print("-" * 60)
    try:
        response = client.session.get(f"{client.base_url}/openapi.json")
        response.raise_for_status()
        openapi = response.json()
        print(f"✓ OpenAPI Version: {openapi['openapi']}")
        print(f"  API Title: {openapi['info']['title']}")
        print(f"  API Version: {openapi['info']['version']}")
        print(f"  Available Endpoints: {len(openapi['paths'])}")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()
    
    # Summary
    print("=" * 60)
    print("Demo Complete!")
    print()
    print("Next Steps:")
    print("  1. Visit http://localhost:8000/docs for interactive API docs")
    print("  2. Visit http://localhost:8000/redoc for alternative docs")
    print("  3. Future tasks will add more endpoints (agents, pipelines, etc.)")
    print("=" * 60)


if __name__ == "__main__":
    main()
