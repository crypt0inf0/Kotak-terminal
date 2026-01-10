from neo_api_client import NeoAPI
import time

# Test script to verify Kotak Neo SDK WebSocket
# Replace with actual credentials
access_token = "YOUR_SESSION_TOKEN_HERE"

def on_message(message):
    print(f"✅ Message received: {message}")

def on_error(error):
    print(f"❌ Error: {error}")

def on_close(message):
    print(f"🔴 Connection closed: {message}")

def on_open(message):
    print(f"🟢 Connection opened: {message}")

# Initialize client
client = NeoAPI(access_token=access_token, environment='prod')

# Try method 1: set_neowebsocket_callbacks
print("Method 1: Using set_neowebsocket_callbacks...")
try:
    client.set_neowebsocket_callbacks(
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    print("✅ Callbacks set successfully")
except Exception as e:
    print(f"❌ Failed: {e}")

# Subscribe to a test instrument
print("\nSubscribing to test instrument...")
try:
    client.subscribe(instrument_tokens=[
        {"instrument_token": "11536", "exchange_segment": "nse_cm"}
    ])
    print("✅ Subscription sent")
except Exception as e:
    print(f"❌ Subscribe failed: {e}")

# Wait for messages
print("\nWaiting for messages (30 seconds)...")
time.sleep(30)
print("Test complete")
