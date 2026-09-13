import uuid
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if X-Request-ID exists and is safe
        request_id = request.headers.get("X-Request-ID")
        
        # Validate request_id length and character set to prevent malicious headers
        if not request_id or len(request_id) > 64 or not re.match(r'^[\w\-]+$', request_id):
            request_id = str(uuid.uuid4())
            
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
