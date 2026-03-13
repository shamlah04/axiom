from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address, 
    default_limits=["200/minute"],
    enabled=not settings.TESTING
)
