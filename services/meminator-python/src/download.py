import os
import uuid
import requests
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import StatusCode



resource = Resource(attributes={
    "service.name": os.getenv("OTEL_SERVICE_NAME", "meminator-python")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


honeycomb_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://api.eu1.honeycomb.io"),
    headers={
        "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY")
    }
)


span_processor = BatchSpanProcessor(honeycomb_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

def download_image(url):
    with tracer.start_as_current_span("download_image") as span:
        span.set_attribute("image.url", url)
        
        # Send a GET request to the URL
        response = requests.get(url)
        
        # Check if the request was successful (status code 200)
        logger.info(f"Status code {response.status_code}")
        span.set_attribute("response.status_code", response.status_code)
        
        if response.status_code == 200:
            # Open the file in binary mode and write the image content
            filename = generate_random_filename(url)
            span.set_attribute("random.filename", filename)
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            span.set_attribute("branch", "success")
            span.add_event("Image downloaded successfully")
            return filename
        else:
            fallback_filename = os.path.abspath('tmp/BusinessWitch.png')
            span.set_status(StatusCode.ERROR, f"Failed to download image: {response.status_code}")
            span.set_attribute("branch", "fallback")
            span.set_attribute("fallback.filename", fallback_filename)  # picked up witch with this attribute
            span.add_event("Using fallback image")
            return fallback_filename

def generate_random_filename(input_filename):

    # Extract the extension from the input filename
    extension = get_file_extension(input_filename)

    # Generate a UUID and convert it to a string
    random_uuid = uuid.uuid4()
    # Convert UUID to string and remove dashes
    random_filename = str(random_uuid).replace("-", "")

    # Append the extension to the random filename
    random_filename_with_extension = random_filename + extension

    random_filepath = os.path.join("/tmp", random_filename_with_extension)

    return random_filepath

def get_file_extension(url):
    # Split the URL by "." and get the last part
    parts = url.split(".")
    if len(parts) > 1:
        return "." + parts[-1]
    else:
        return ""
