import asyncio
import websockets
import json
import logging
import requests
import time

logging.basicConfig(level=logging.INFO)

# Global variables
client_data = {}
quote_queue = asyncio.Queue()
loop = None
polling_task = None

async def get_credentials():
    """Fetch credentials from backend"""
    print("Fetching credentials from backend...")
    try:
        from config import KOTAKNEO_WEBSOCKET_DATA_ENDPOINT
        response = requests.get(KOTAKNEO_WEBSOCKET_DATA_ENDPOINT)
        response.raise_for_status()
        data = response.json()
        
        usersession = data.get("usersession", "") 
        sid = data.get("sid", "")
        userid = data.get("userid", "")
        base_url = data.get("baseUrl", "")
        
        if usersession and base_url:
            print(f"Valid Kotak Neo credentials retrieved. BaseURL: {base_url}")
            return usersession, sid, userid, base_url
        else:
            print("Waiting for valid Kotak Neo credentials...")
            return None, None, None, None
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve credentials: {e}")
        return None, None, None, None

async def wait_for_data():
    """Wait for valid credentials"""
    while True:
        token, sid, userid, base_url = await get_credentials()
        if token:
            return token, sid, userid, base_url
        await asyncio.sleep(5)

async def setup_api_connection(token, sid, userid, base_url):
    """Store credentials for API calls"""
    global client_data
    print(f"Storing Kotak Neo credentials...")
    client_data = {
        'token': token,
        'sid': sid,
        'userid': userid,
        'baseUrl': base_url
    }
    print("Credentials stored successfully")
    return True

# Subscribed instruments
subscribed_instruments = set()

async def poll_quotes():
    """Poll Quotes API for LTP data"""
    global client_data, subscribed_instruments
    
    print("Starting LTP polling service...")
    
    while True:
        try:
            if not client_data.get('token') or not client_data.get('baseUrl') or not subscribed_instruments:
                await asyncio.sleep(2)
                continue
            
            # Build query string for all subscribed instruments
            queries = []
            for inst in subscribed_instruments:
                exchange = inst['exchange_segment']
                token = inst['instrument_token']
                queries.append(f"{exchange}|{token}")
            
            if not queries:
                await asyncio.sleep(2)
                continue
            
            query_string = ','.join(queries)
            
            # Call Quotes API
            base_url = client_data.get('baseUrl')
            url = f"{base_url}/script-details/1.0/quotes/neosymbol/{query_string}/ltp"
            
            headers = {
                'Authorization': client_data['token'],
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Process and queue the data
                if isinstance(data, list):
                    for item in data:
                        # Transform to match expected format
                        quote_data = {
                            'tk': item.get('exchange_token', ''),
                            'lp': item.get('ltp', '0'),
                            'pc': item.get('per_change', '0'),
                            'v': item.get('last_volume', '0')
                        }
                        await quote_queue.put(quote_data)
                        
            await asyncio.sleep(1)  # Poll every 1 second
            
        except Exception as e:
            print(f"Error polling quotes: {e}")
            await asyncio.sleep(2)

async def websocket_server(websocket):
    """Handle WebSocket connections from frontend"""
    print("New frontend client connected")
    
    try:
        send_task = asyncio.create_task(send_quote_updates(websocket))
        async for message in websocket:
            await handle_websocket_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        print("Frontend connection closed")
    except Exception as e:
        print(f"Websocket server error: {e}")
    finally:
        send_task.cancel()

async def send_quote_updates(websocket):
    """Send quote updates to frontend"""
    while True:
        try:
            quote = await quote_queue.get()
            await websocket.send(json.dumps(quote))
        except Exception as e:
            print(f"Error sending to frontend: {e}")
            await asyncio.sleep(1)

async def handle_websocket_message(websocket, message):
    """Handle messages from frontend"""
    global subscribed_instruments
    
    data = json.loads(message)
    
    if "action" in data:
        if data["action"] == "subscribe":
            print(f"Subscription request for: {data.get('symbols')}")
            for sym in data["symbols"]:
                try:
                    if '|' in sym:
                        parts = sym.split('|')
                    else:
                        parts = sym.split(' ')
                        
                    if len(parts) == 2:
                        exch = parts[0]
                        token = parts[1]
                        segment = ""
                        if exch == "NSE": segment = "nse_cm"
                        elif exch == "NFO": segment = "nse_fo"
                        elif exch == "BSE": segment = "bse_cm"
                        elif exch == "BFO": segment = "bse_fo"
                        
                        if segment:
                            subscribed_instruments.add(json.dumps({
                                "instrument_token": token,
                                "exchange_segment": segment
                            }))
                except Exception as e:
                    print(f"Error parsing symbol: {e}")
            
            print(f"Now tracking {len(subscribed_instruments)} instruments")
            
        elif data["action"] == "unsubscribe":
            print(f"Unsubscribe request for: {data.get('symbols')}")
            # Handle unsubscribe

async def main(port):
    """Main entry point"""
    global loop, polling_task
    loop = asyncio.get_running_loop()
    
    print(f"Starting Kotak Neo WebSocket on port {port}...")
    token, sid, userid, base_url = await wait_for_data()
    
    await setup_api_connection(token, sid, userid, base_url)
    
    # Start polling task
    polling_task = asyncio.create_task(poll_quotes())
    
    # Start WebSocket server
    server = await websockets.serve(websocket_server, "0.0.0.0", port)
    print(f"WebSocket server started on 0.0.0.0:{port}")
    await server.wait_closed()

if __name__ == "__main__":
    import sys
    from config import KOTAKNEO_WS_PORT
    
    port = KOTAKNEO_WS_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        
    asyncio.run(main(port))
