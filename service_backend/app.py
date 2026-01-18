import time
import logging
import random
import os
from flask import Flask, request, jsonify, g, abort
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
    fileHandler = logging.FileHandler('/var/log/app/backend.log')
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
except Exception as e:
    print(f"Could not setup file logging: {e}")

# Prometheus Metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])

@app.before_request
def before_request():
    g.start_time = time.time()
    g.trace_id = request.headers.get('X-Trace-ID', 'unknown')

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
    
    logger.info("Backend request processed", extra={
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'latency': request_latency
    })
    return response

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/process', methods=['POST'])
def process():
    # Simulate Logic
    delay = random.uniform(0.1, 0.5)
    time.sleep(delay)
    
    # Simulate Random Failures
    if random.random() < 0.1: # 10% failure rate
        logger.error("Random processing error occurred")
        return jsonify({"error": "processing failed", "trace_id": g.trace_id}), 500

    return jsonify({"status": "processed", "trace_id": g.trace_id, "duration": delay}), 200

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
