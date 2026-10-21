from app.routers.briefing import router as briefing_router
from app.routers.stock import router as stock_router
from app.routers.portfolio import router as portfolio_router
from app.routers.phones import router as phones_router
from app.routers.cards import router as cards_router
from app.routers.wallet_cards import router as wallet_cards_router
from app.routers.ai_monitor import router as ai_monitor_router
from app.routers.overseas_documents import router as overseas_documents_router

__all__ = [
    "briefing_router",
    "stock_router",
    "portfolio_router",
    "phones_router",
    "cards_router",
    "wallet_cards_router",
    "ai_monitor_router",
    "overseas_documents_router",
]
