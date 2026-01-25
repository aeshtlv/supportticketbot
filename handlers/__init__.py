from handlers.user_handlers import router as user_router
from handlers.support_handlers import router as support_router
from handlers.admin_handlers import router as admin_router

__all__ = ["user_router", "support_router", "admin_router"]
