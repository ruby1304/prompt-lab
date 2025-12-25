#!/usr/bin/env python3
"""
OpenAPI Documentation Demo

This script demonstrates how to access and use the Prompt Lab API documentation.

The API provides three documentation interfaces:
1. Swagger UI (Interactive): http://localhost:8000/docs
2. ReDoc (Documentation): http://localhost:8000/redoc
3. OpenAPI JSON (Specification): http://localhost:8000/openapi.json

Usage:
    # Start the API server first
    python -m src.api.server
    
    # Then run this demo
    python examples/api_documentation_demo.py
"""

import requests
import json
from typing import Dict, Any


def check_documentation_endpoints():
    """Check that all documentation endpoints are accessible."""
    base_url = "http://localhost:8000"
    
    print("=" * 70)
    print("Prompt Lab API Documentation Demo")
    print("=" * 70)
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        if response.status_code == 200:
            print("✅ API Server is running")
            health_data = response.json()
            print(f"   Service: {health_data.get('service')}")
            print(f"   Version: {health_data.get('version')}")
            print(f"   Status: {health_data.get('status')}")
        else:
            print("❌ API Server returned unexpected status")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API Server is not running")
        print("   Please start the server with: python -m src.api.server")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False
    
    print()
    print("-" * 70)
    print("Documentation Endpoints")
    print("-" * 70)
    print()
    
    # Check Swagger UI
    print("1. Swagger UI (Interactive Documentation)")
    print(f"   URL: {base_url}/docs")
    try:
        response = requests.get(f"{base_url}/docs", timeout=2)
        if response.status_code == 200:
            print("   ✅ Accessible")
            print("   Features:")
            print("      - Interactive API testing")
            print("      - Try out endpoints directly")
            print("      - View request/response schemas")
            print("      - Execute API calls with custom parameters")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Check ReDoc
    print("2. ReDoc (Clean Documentation)")
    print(f"   URL: {base_url}/redoc")
    try:
        response = requests.get(f"{base_url}/redoc", timeout=2)
        if response.status_code == 200:
            print("   ✅ Accessible")
            print("   Features:")
            print("      - Clean, readable layout")
            print("      - Three-panel design")
            print("      - Full-text search")
            print("      - Deep linking support")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Check OpenAPI JSON
    print("3. OpenAPI Specification (JSON)")
    print(f"   URL: {base_url}/openapi.json")
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        if response.status_code == 200:
            print("   ✅ Accessible")
            spec = response.json()
            print(f"   OpenAPI Version: {spec.get('openapi')}")
            print(f"   API Title: {spec.get('info', {}).get('title')}")
            print(f"   API Version: {spec.get('info', {}).get('version')}")
            print(f"   Endpoints: {len(spec.get('paths', {}))} paths")
            print(f"   Tags: {len(spec.get('tags', []))} categories")
            print()
            print("   Uses:")
            print("      - Import to Postman/Insomnia")
            print("      - Generate client SDKs")
            print("      - API management tools")
            print("      - Version control")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("-" * 70)
    print("OpenAPI Specification Details")
    print("-" * 70)
    print()
    
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        if response.status_code == 200:
            spec = response.json()
            
            # Show info
            info = spec.get('info', {})
            print("API Information:")
            print(f"  Title: {info.get('title')}")
            print(f"  Version: {info.get('version')}")
            print(f"  Description: {info.get('description', '')[:100]}...")
            
            # Show contact
            contact = info.get('contact', {})
            if contact:
                print(f"  Contact: {contact.get('name')} <{contact.get('email')}>")
            
            # Show license
            license_info = info.get('license', {})
            if license_info:
                print(f"  License: {license_info.get('name')}")
            
            print()
            
            # Show servers
            servers = spec.get('servers', [])
            if servers:
                print(f"Servers ({len(servers)}):")
                for server in servers:
                    print(f"  - {server.get('url')}: {server.get('description')}")
                print()
            
            # Show tags
            tags = spec.get('tags', [])
            if tags:
                print(f"Endpoint Categories ({len(tags)}):")
                for tag in tags:
                    print(f"  - {tag.get('name')}: {tag.get('description')}")
                print()
            
            # Show paths
            paths = spec.get('paths', {})
            if paths:
                print(f"API Endpoints ({len(paths)} paths):")
                for path, methods in list(paths.items())[:10]:
                    method_list = [m.upper() for m in methods.keys() if m != 'parameters']
                    print(f"  {path}")
                    print(f"    Methods: {', '.join(method_list)}")
                if len(paths) > 10:
                    print(f"  ... and {len(paths) - 10} more endpoints")
                print()
    except Exception as e:
        print(f"Error fetching OpenAPI spec: {e}")
    
    print("-" * 70)
    print("Next Steps")
    print("-" * 70)
    print()
    print("1. Open Swagger UI in your browser:")
    print(f"   {base_url}/docs")
    print()
    print("2. Try out an endpoint:")
    print("   - Click on 'GET /api/v1/agents'")
    print("   - Click 'Try it out'")
    print("   - Click 'Execute'")
    print("   - View the response")
    print()
    print("3. View clean documentation:")
    print(f"   {base_url}/redoc")
    print()
    print("4. Download OpenAPI specification:")
    print(f"   curl {base_url}/openapi.json > openapi.json")
    print()
    print("5. Import to Postman:")
    print("   - Open Postman")
    print("   - Click 'Import'")
    print("   - Enter URL: http://localhost:8000/openapi.json")
    print()
    
    return True


def demonstrate_api_call():
    """Demonstrate making an API call using the documentation."""
    base_url = "http://localhost:8000"
    
    print("=" * 70)
    print("Example API Call")
    print("=" * 70)
    print()
    
    print("Let's list available agents:")
    print(f"GET {base_url}/api/v1/agents?page=1&page_size=5")
    print()
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/agents",
            params={"page": 1, "page_size": 5},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            agents = data.get('agents', [])
            pagination = data.get('pagination', {})
            
            print(f"✅ Success! Found {pagination.get('total_items', 0)} agents")
            print()
            
            if agents:
                print("Sample Agents:")
                for agent in agents[:3]:
                    print(f"  - {agent.get('id')}")
                    print(f"    Name: {agent.get('name')}")
                    print(f"    Category: {agent.get('category')}")
                    print(f"    Status: {agent.get('status')}")
                    print()
            
            print("Pagination Info:")
            print(f"  Page: {pagination.get('page')}/{pagination.get('total_pages')}")
            print(f"  Items: {len(agents)}/{pagination.get('total_items')}")
            print(f"  Has Next: {pagination.get('has_next')}")
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


if __name__ == "__main__":
    # Check documentation endpoints
    if check_documentation_endpoints():
        print()
        # Demonstrate an API call
        demonstrate_api_call()
    
    print("=" * 70)
    print("Documentation Demo Complete")
    print("=" * 70)
    print()
    print("For more information, see:")
    print("  - docs/reference/openapi-documentation-guide.md")
    print("  - docs/reference/openapi-quick-reference.md")
    print()
