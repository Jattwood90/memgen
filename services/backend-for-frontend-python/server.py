from flask import Flask, jsonify, Response, request
import os
import logging
from o11yday_lib import fetch_from_service

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import StatusCode

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# OpenTelemetry setup
resource = Resource(attributes={
    "service.name": "backend-for-frontend-python"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)


honeycomb_exporter = OTLPSpanExporter(
    endpoint="https://api.eu1.honeycomb.io",
    headers={
        "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY") #sourced from .env file not uploaded
    }
)


span_processor = BatchSpanProcessor(honeycomb_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Flask application setup
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Route for health check
@app.route('/health')
@app.route('/')
def health():
    return jsonify({"message": "I am here", "status_code": 0})

# Route for creating a picture
@app.route('/createPicture', methods=['POST'])
def create_picture():

    try:
        with tracer.start_as_current_span("fetch_from_image_picker") as image_span:
            image_response = fetch_from_service('image-picker')
            if image_response and image_response.ok:
                image_result = image_response.json()
                image_span.set_attribute("image_result", "success")
            else:
                image_result = {"imageUrl": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Banana-Single.jpg/1360px-Banana-Single.jpg"}
                image_span.set_status(StatusCode.ERROR, "Failed to fetch image")
                image_span.set_attribute("image_result", "fallback")

            image_span.set_attribute("image_url", image_result["imageUrl"])

            # Fetch data from phrase-picker service
            with tracer.start_as_current_span("fetch_from_phrase_picker") as phrase_span:
                phrase_response = fetch_from_service('phrase-picker')
                if phrase_response and phrase_response.ok:
                    phrase_result = phrase_response.json()
                    phrase_span.set_attribute("phrase_result", "success")
                else:
                    phrase_result = {"phrase": "This is sparta"}
                    phrase_span.set_status(StatusCode.ERROR, "Failed to fetch phrase")
                    phrase_span.set_attribute("phrase_result", "fallback")

                phrase_span.set_attribute("phrase", phrase_result["phrase"])


            # Make a request to the meminator service
            body = {**phrase_result, **image_result}
            with tracer.start_as_current_span("fetch_from_meminator") as meminator:
                meminator_response = fetch_from_service('meminator', method="POST", body=body)
                if not meminator_response or not meminator_response.ok or meminator_response.content is None:
                    error_message = f"Failed to fetch picture from meminator: {meminator_response.status_code} {meminator_response.reason}"
                    logger.error(error_message)
                    meminator.set_attribute("meminator.response", meminator_response)
                    raise Exception(error_message)

                flask_response = Response(meminator_response.content, status=meminator_response.status_code, content_type=meminator_response.headers.get('content-type'))

            return flask_response
    
    except Exception as e:
        logger.error(f"Exception in create_picture: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(port=10115)
