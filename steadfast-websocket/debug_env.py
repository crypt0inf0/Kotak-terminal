import sys
try:
    import websockets
    print(f"Websockets File: {websockets.__file__}")
    print(f"Websockets Version: {websockets.version.version}")
except ImportError:
    print("Websockets not installed")
except Exception as e:
    print(f"Error: {e}")

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
