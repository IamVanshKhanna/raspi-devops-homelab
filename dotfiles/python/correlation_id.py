"""
Correlation ID Middleware for Python Services
Usage: Add to FastAPI/Starlette/Flask apps
"""

import uuid
import contextvars
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for correlation ID propagation
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)

CORRELATION_ID_HEADER = "X-Correlation-ID"

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """ASGI middleware to extract/generate correlation IDs and propagate them."""
    
    async def dispatch(self, request: Request, call_next):
        # Extract correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set context variable for the request lifecycle
        token = correlation_id_var.set(correlation_id)
        
        try:
            response: Response = await call_next(request)
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)

def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()

def set_correlation_id(correlation_id: str) -> contextvars.Token:
    """Set correlation ID in context (for manual tracing)."""
    return correlation_id_var.set(correlation_id)

class CorrelationIDFilter(logging.Filter):
    """Logging filter to inject correlation ID into log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "none"
        return True

def setup_correlation_logging():
    """Configure logging with correlation ID support."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [correlation_id=%(correlation_id)s] %(name)s: %(message)s'
    ))
    handler.addFilter(CorrelationIDFilter())
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

# Example FastAPI integration
def create_fastapi_app_with_correlation():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="Homelab Service", version="1.0.0")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIDMiddleware)
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "correlation_id": get_correlation_id()}
    
    return app

# Example usage in services
def trace_operation(operation_name: str, correlation_id: Optional[str] = None):
    """Context manager for tracing operations with correlation ID."""
    class OperationTracer:
        def __enter__(self):
            self.cid = correlation_id or get_correlation_id() or str(uuid.uuid4())
            self.token = correlation_id_var.set(self.cid)
            logging.info(f"Starting operation: {operation_name}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                logging.error(f"Operation {operation_name} failed: {exc_val}", exc_info=True)
            else:
                logging.info(f"Operation {operation_name} completed")
            correlation_id_var.reset(self.token)
    
    return OperationTracer()