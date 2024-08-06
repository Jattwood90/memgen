import os
import subprocess
from flask import Flask, jsonify, send_file, request
from flask import Flask
import logging

# opentelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


from download import generate_random_filename, download_image

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

resource = Resource(attributes={
    "service.name": "meminator-python"
})


trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)


honeycomb_exporter = OTLPSpanExporter(
    endpoint="https://api.eu1.honeycomb.io",
    headers={
        "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY")
    }
)

IMAGE_MAX_WIDTH_PX=1000
IMAGE_MAX_HEIGHT_PX=1000

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Route for health check
@app.route('/health')
def health():
    result = {"message": "I am here", "status_code": 0}
    return jsonify(result)


@app.route('/applyPhraseToPicture', methods=['POST', 'GET'])
def meminate():
    with tracer.start_as_current_span("applyPhraseToPicture") as span:
        
        input = request.json or { "phrase": "I got you"}
        phrase = input.get("phrase", "words go here").upper()
        imageUrl = input.get("imageUrl", "http://missing.booo/no-url-here.png")
        
        span.set_attribute("input", input)
        span.set_attribute("phrase", phrase)
        span.set_attribute("imageUrl", imageUrl) # definite duplication here
    

    # Get the absolute path to the PNG file - productID as url?
        input_image_path = download_image(imageUrl)
        with tracer.start_as_current_span("download_image") as download_image_span:
            # Check if the file exists
            if not os.path.exists(input_image_path):
                message = 'downloaded image file not found'
                download_image_span.set_attribute("error_message", message)
                logger.error(message)
                return message, 500

        
            # Define the output image path
            output_image_path = generate_random_filename(input_image_path)

            command = ['convert',
                    input_image_path,
                    '-resize', f'{IMAGE_MAX_WIDTH_PX}x{IMAGE_MAX_HEIGHT_PX}>',
                    '-gravity', 'North',
                    '-pointsize', '48',
                    '-fill', 'white',
                    '-undercolor', '#00000080',
                    '-font', 'Angkor-Regular',
                    '-annotate', '0', phrase,
                    output_image_path]

            # #  Execute ImageMagick command to apply text to the image
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                exception_message = f"Subprocess failed with return code: {result.returncode}"
                logger.error(exception_message)
                raise Exception(exception_message)

            # Serve the modified image
            return send_file(
                output_image_path,
                mimetype='image/png'
            )

if __name__ == '__main__':
    app.run(port=10117)
