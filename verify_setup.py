
import sys
import os
import traceback

# Add the current directory to sys.path so we can import backend modules
sys.path.append(os.getcwd())

try:
    print("Checking imports...")
    import networkx
    print("networkx imported")
    import community
    print("python-louvain (community) imported")
    
    print("Checking backend.main...")
    from backend.main import app
    print("backend.main imported successfully")
    
    print("Checking routes...")
    routes = [route.path for route in app.routes]
    if "/api/graph/network/{provider_id}" in routes:
        print("Graph route found")
    else:
        print("WARNING: Graph route NOT found")
        
    if "/api/homecare/evv-fraud/{provider_id}" in routes:
        print("Homecare route found")
    else:
        print("WARNING: Homecare route NOT found")

    print("Verification Successful")

except ImportError as e:
    print(f"ImportError: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
