from handlers.user_handlers import router as user_router
from handlers.operator_handlers import router as operator_router
from handlers.common_handlers import router as common_router

__all__ = ["user_router", "operator_router", "common_router"]

