import time
import requests
import random
import threading
import subprocess

GATEWAY_URL = "http://localhost:5001"

def traffic_generator():
    print("Starting traffic generator...")
    while True:
        try:
            resp = requests.post(f"{GATEWAY_URL}/analyze", json={"data": "test"})
            print(f"Request sent. Status: {resp.status_code}")
        except Exception as e:
            print(f"Request failed: {e}")
        time.sleep(random.uniform(0.1, 1.0))

def chaos_monkey():
    print("Starting Chaos Monkey...")
    # List of services to disrupt
    services = ["gateway", "backend"]
    
    while True:
        time.sleep(30) # Wait before next disruption
        target = random.choice(services)
        action = random.choice(["restart", "stop_start"])
        
        print(f"CHAOS: Performing {action} on {target}")
        
        if action == "restart":
            subprocess.run(["docker", "compose", "-f", "infra/docker-compose.yml", "restart", target])
        elif action == "stop_start":
            subprocess.run(["docker", "compose", "-f", "infra/docker-compose.yml", "stop", target])
            time.sleep(5)
            subprocess.run(["docker", "compose", "-f", "infra/docker-compose.yml", "start", target])
        
        print(f"CHAOS: {action} on {target} completed.")

if __name__ == "__main__":
    # Start traffic in background
    t = threading.Thread(target=traffic_generator)
    t.daemon = True
    t.start()
    
    # Start chaos
    try:
        chaos_monkey()
    except KeyboardInterrupt:
        print("Stopping Chaos Monkey")
