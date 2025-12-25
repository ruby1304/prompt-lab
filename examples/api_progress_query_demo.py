"""
Progress Query API Demo

This example demonstrates how to use the progress query API endpoints
to monitor execution progress in real-time.

Features demonstrated:
1. Starting an async execution
2. Polling for progress updates
3. Using WebSocket for real-time progress streaming
4. Handling different execution states

Requirements:
- API server running (python -m src.api.server)
- Valid agent or pipeline configuration
"""

import requests
import time
import json
from websocket import create_connection
import threading


# API base URL
BASE_URL = "http://localhost:8000/api/v1"


def start_execution():
    """Start an async pipeline execution."""
    print("=" * 60)
    print("Starting Async Execution")
    print("=" * 60)
    
    # Start execution
    response = requests.post(
        f"{BASE_URL}/executions",
        json={
            "type": "pipeline",
            "target_id": "customer_service_flow",
            "inputs": {
                "customer_query": "How do I reset my password?"
            },
            "config": {
                "max_workers": 4
            }
        }
    )
    
    if response.status_code == 202:
        data = response.json()
        execution_id = data["execution_id"]
        print(f"✓ Execution started: {execution_id}")
        print(f"  Status: {data['status']}")
        print(f"  Status URL: {data['status_url']}")
        return execution_id
    else:
        print(f"✗ Failed to start execution: {response.status_code}")
        print(f"  Error: {response.json()}")
        return None


def poll_progress(execution_id: str, max_polls: int = 20):
    """Poll for progress updates using REST API."""
    print("\n" + "=" * 60)
    print("Polling for Progress (REST API)")
    print("=" * 60)
    
    for i in range(max_polls):
        # Get progress
        response = requests.get(f"{BASE_URL}/executions/{execution_id}/progress")
        
        if response.status_code == 200:
            progress = response.json()
            print(f"\n[Poll {i+1}] Progress Update:")
            print(f"  Step: {progress['current_step']}/{progress['total_steps']}")
            print(f"  Percentage: {progress['percentage']:.1f}%")
            if progress.get('current_step_name'):
                print(f"  Current Step: {progress['current_step_name']}")
        elif response.status_code == 204:
            print(f"\n[Poll {i+1}] No progress data available")
        else:
            print(f"\n[Poll {i+1}] Error: {response.status_code}")
            break
        
        # Check execution status
        status_response = requests.get(f"{BASE_URL}/executions/{execution_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            current_status = status_data['status']
            
            if current_status in ['completed', 'failed', 'cancelled']:
                print(f"\n✓ Execution {current_status}")
                if current_status == 'completed' and status_data.get('outputs'):
                    print(f"  Outputs: {json.dumps(status_data['outputs'], indent=2)}")
                elif current_status == 'failed' and status_data.get('error'):
                    print(f"  Error: {status_data['error']['message']}")
                break
        
        # Wait before next poll
        time.sleep(1)


def stream_progress_websocket(execution_id: str):
    """Stream progress updates using WebSocket."""
    print("\n" + "=" * 60)
    print("Streaming Progress (WebSocket)")
    print("=" * 60)
    
    # Connect to WebSocket
    ws_url = f"ws://localhost:8000/api/v1/executions/{execution_id}/progress/ws"
    
    try:
        ws = create_connection(ws_url)
        print(f"✓ WebSocket connected: {execution_id}")
        
        # Receive messages
        while True:
            try:
                message = ws.recv()
                data = json.loads(message)
                
                msg_type = data.get('type')
                timestamp = data.get('timestamp', '')
                
                if msg_type == 'status':
                    print(f"\n[{timestamp}] Initial Status:")
                    print(f"  Status: {data['status']}")
                    if data.get('progress'):
                        progress = data['progress']
                        print(f"  Progress: {progress['percentage']:.1f}%")
                
                elif msg_type == 'started':
                    print(f"\n[{timestamp}] Execution Started")
                
                elif msg_type == 'progress':
                    progress = data['progress']
                    print(f"\n[{timestamp}] Progress Update:")
                    print(f"  Step: {progress['current_step']}/{progress['total_steps']}")
                    print(f"  Percentage: {progress['percentage']:.1f}%")
                    if progress.get('current_step_name'):
                        print(f"  Current Step: {progress['current_step_name']}")
                
                elif msg_type == 'completed':
                    print(f"\n[{timestamp}] ✓ Execution Completed")
                    if data.get('outputs'):
                        print(f"  Outputs: {json.dumps(data['outputs'], indent=2)}")
                    break
                
                elif msg_type == 'failed':
                    print(f"\n[{timestamp}] ✗ Execution Failed")
                    if data.get('error'):
                        error = data['error']
                        print(f"  Error Type: {error['type']}")
                        print(f"  Message: {error['message']}")
                    break
                
                elif msg_type == 'cancelled':
                    print(f"\n[{timestamp}] ⊗ Execution Cancelled")
                    break
                
                elif msg_type == 'error':
                    print(f"\n[{timestamp}] ✗ WebSocket Error:")
                    print(f"  Message: {data['message']}")
                    break
                
            except Exception as e:
                print(f"\n✗ Error receiving message: {e}")
                break
        
        ws.close()
        print("\n✓ WebSocket connection closed")
        
    except Exception as e:
        print(f"\n✗ WebSocket connection failed: {e}")


def compare_polling_vs_websocket():
    """Compare polling vs WebSocket approaches."""
    print("\n" + "=" * 60)
    print("Comparison: Polling vs WebSocket")
    print("=" * 60)
    
    # Start two executions
    print("\nStarting two executions for comparison...")
    
    exec_id_1 = start_execution()
    if not exec_id_1:
        return
    
    time.sleep(0.5)
    
    exec_id_2 = start_execution()
    if not exec_id_2:
        return
    
    # Monitor first with polling
    print("\n--- Monitoring Execution 1 with Polling ---")
    poll_start = time.time()
    poll_progress(exec_id_1, max_polls=10)
    poll_duration = time.time() - poll_start
    
    # Monitor second with WebSocket
    print("\n--- Monitoring Execution 2 with WebSocket ---")
    ws_start = time.time()
    stream_progress_websocket(exec_id_2)
    ws_duration = time.time() - ws_start
    
    # Compare
    print("\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)
    print(f"Polling Duration: {poll_duration:.2f}s")
    print(f"WebSocket Duration: {ws_duration:.2f}s")
    print(f"\nWebSocket is typically more efficient for real-time updates")
    print(f"as it eliminates polling overhead and provides instant notifications.")


def demo_progress_query_basic():
    """Basic progress query demo."""
    print("\n" + "=" * 60)
    print("Basic Progress Query Demo")
    print("=" * 60)
    
    # Start execution
    execution_id = start_execution()
    if not execution_id:
        return
    
    # Wait a moment for execution to start
    time.sleep(0.5)
    
    # Query progress
    print("\nQuerying progress...")
    response = requests.get(f"{BASE_URL}/executions/{execution_id}/progress")
    
    if response.status_code == 200:
        progress = response.json()
        print("✓ Progress retrieved:")
        print(f"  Current Step: {progress['current_step']}/{progress['total_steps']}")
        print(f"  Percentage: {progress['percentage']:.1f}%")
        if progress.get('current_step_name'):
            print(f"  Step Name: {progress['current_step_name']}")
    elif response.status_code == 204:
        print("ℹ No progress data available yet")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")


def demo_websocket_basic():
    """Basic WebSocket demo."""
    print("\n" + "=" * 60)
    print("Basic WebSocket Demo")
    print("=" * 60)
    
    # Start execution
    execution_id = start_execution()
    if not execution_id:
        return
    
    # Stream progress
    stream_progress_websocket(execution_id)


def demo_concurrent_monitoring():
    """Demo monitoring multiple executions concurrently."""
    print("\n" + "=" * 60)
    print("Concurrent Execution Monitoring")
    print("=" * 60)
    
    # Start multiple executions
    execution_ids = []
    for i in range(3):
        exec_id = start_execution()
        if exec_id:
            execution_ids.append(exec_id)
        time.sleep(0.2)
    
    if not execution_ids:
        return
    
    print(f"\n✓ Started {len(execution_ids)} executions")
    
    # Monitor all executions with WebSocket in separate threads
    threads = []
    for exec_id in execution_ids:
        thread = threading.Thread(
            target=stream_progress_websocket,
            args=(exec_id,),
            name=f"Monitor-{exec_id}"
        )
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("\n✓ All executions completed")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Progress Query API Demo")
    print("=" * 60)
    print("\nThis demo shows how to monitor execution progress using:")
    print("1. REST API polling")
    print("2. WebSocket streaming")
    print("3. Concurrent monitoring")
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print("\n✗ API server is not running!")
            print("  Start it with: python -m src.api.server")
            return
    except Exception as e:
        print(f"\n✗ Cannot connect to API server: {e}")
        print("  Start it with: python -m src.api.server")
        return
    
    # Run demos
    try:
        # Demo 1: Basic progress query
        demo_progress_query_basic()
        
        # Demo 2: Basic WebSocket
        demo_websocket_basic()
        
        # Demo 3: Comparison
        # compare_polling_vs_websocket()
        
        # Demo 4: Concurrent monitoring
        # demo_concurrent_monitoring()
        
    except KeyboardInterrupt:
        print("\n\n✗ Demo interrupted by user")
    except Exception as e:
        print(f"\n✗ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
