import logging
import json
import traceback
from datetime import datetime
from starlette.requests import Request

class StructuredJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add any extra attributes passed in `extra`
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "provider"):
            log_data["provider"] = record.provider
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "outcome"):
            log_data["outcome"] = record.outcome
            
        # Add dynamic kwargs passed via extra
        if hasattr(record, 'extra_fields') and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                log_data[k] = v

        if record.exc_info:
            log_data["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(log_data)

def setup_logger(name="lenny"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = StructuredJSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger()

def log_event(event: str, request: Request = None, level=logging.INFO, **kwargs):
    extra = {"event": event, "extra_fields": kwargs}
    
    if request and hasattr(request.state, "request_id"):
        extra["request_id"] = request.state.request_id
        
    # Extract known top-level fields
    for field in ["session_id", "provider", "latency_ms", "outcome"]:
        if field in kwargs:
            extra[field] = kwargs.pop(field)
            
    logger.log(level, event, extra=extra)
