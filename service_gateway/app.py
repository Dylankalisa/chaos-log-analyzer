import time
import uuid
import logging
import random
import os
import requests
from flask import Flask, request, jsonify, g
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Configure JSON Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s trace_id=%(trace_id)s')

# Stream Handler
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# File Handler
try:
    os.makedirs('/var/log/app', exist_ok=True)
    fileHandler = logging.FileHandler('/var/log/app/gateway.log')
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
except Exception as e:
    print(f"Could not setup file logging: {e}")

# Prometheus Metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://backend:5000')

@app.before_request
def before_request():
    g.start_time = time.time()
    # Generate TraceID or propagate if receiving one (though Gateway usually starts it)
    g.trace_id = request.headers.get('X-Trace-ID', str(uuid.uuid4()))
    # Inject trace_id into log record factory or use an adapter.
    # For simplicity, we'll manually add it to log calls or context.
    # Better: Use a custom filter or adapter.
    
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = getattr(g, 'trace_id', 'N/A')
        return True

logger.addFilter(TraceIdFilter())

@app.after_request
def after_request(response):
    request_latency = time.time() - g.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint=request.path).observe(request_latency)
    
    logger.info("Request processed", extra={
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'latency': request_latency
    })
    return response

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    # Simulate some work
    time.sleep(random.uniform(0.01, 0.05))
    
    # Call Backend
    try:
        headers = {'X-Trace-ID': g.trace_id}
        resp = requests.post(f"{BACKEND_URL}/process", json={"data": "sample"}, headers=headers, timeout=2)
        backend_data = resp.json()
        return jsonify({"status": "analyzed", "trace_id": g.trace_id, "backend_response": backend_data}), 200
    except Exception as e:
        logger.error(f"Failed to call backend: {e}")
        return jsonify({"error": "backend unavailable", "trace_id": g.trace_id}), 503

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/alert', methods=['POST'])
def receive_alert():
    try:
        data = request.json
        logger.warning(f"ALERT RECEIVED: {data}", extra={'trace_id': g.trace_id})
        return jsonify({"status": "alert_received"}), 200
    except Exception as e:
        logger.error(f"Failed to process alert: {e}")
        return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
