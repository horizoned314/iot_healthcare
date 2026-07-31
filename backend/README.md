1. Run mosquitto
mosquitto -v -c mosquitto.conf

2. run gateway_service.py

3. run api_server.py
uvicorn api_service:app --reload