import requests
import logging
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


# log config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

resource = Resource(attributes={
    "service.name": "backend-for-frontend-python"
})


trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)


honeycomb_exporter = OTLPSpanExporter(
    endpoint="https://api.eu1.honeycomb.io",
    headers={
        "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY")
    }
)
# local urls for invoking container apps
SERVICES = {
    'image-picker': 'http://image-picker:10116/imageUrl',
    'meminator': 'http://meminator:10117/applyPhraseToPicture', 
    'phrase-picker': 'http://phrase-picker:10118/phrase',
    
}


def fetch_from_service(service, method='GET', body=None):
    """
    Fetches data from a remote service over HTTP.

    Args:
        service (str): One of the services in SERVICES
        method: 'GET' or 'POST'
    Returns:
        dict: The JSON response from the remote service.
    """
   
    with tracer.start_as_current_span(f"fetch_from_{service}") as span:
        span.set_attribute("service.name", service)
        span.set_attribute("http.method", method)

        try:
            url = SERVICES[service]
            span.set_attribute("http.url", url)
        except KeyError:
            error_msg = f"Service '{service}' not found in SERVICES dictionary"
            logger.error(error_msg)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            span.record_exception(KeyError(error_msg))
            span.add_event("Exception", {"error": "KeyError", "message": error_msg})
            return None

        try:
            if method == 'GET':
                response = requests.get(url)
            elif method == 'POST':
                response = requests.post(url, json=body)
            else:
                error_msg = f"Method {method} not supported"
                logger.error(error_msg)
                span.set_status(Status(StatusCode.ERROR, error_msg))
                span.add_event("Unsupported Method", {"method": method})
                return None

            response.raise_for_status()
            
            span.set_attribute("http.status_code", response.status_code)
            span.add_event("Request Successful", {"status_code": response.status_code})
            return response

        except requests.RequestException as e:
            error_msg = f"Error fetching data from {url}: {str(e)}"
            logger.error(error_msg)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            span.record_exception(e)
            span.add_event("RequestException", {"error": str(e)})
            return None
