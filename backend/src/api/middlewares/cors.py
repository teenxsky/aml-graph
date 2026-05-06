from typing import Any, cast

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

__all__ = ['cors_middleware']


cors_middleware = Middleware(
    cast(Any, CORSMiddleware),
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)
