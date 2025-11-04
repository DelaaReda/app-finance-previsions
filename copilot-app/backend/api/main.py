from fastapi import FastAPI
from core.middleware import FinanceMiddleware
from api.routes.health import router as health_router
from api.routes.news import router as news_router
from api.routes.forecasts import router as forecasts_router

app = FastAPI(title="Finance Copilot API")
app.add_middleware(FinanceMiddleware)
app.include_router(health_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(forecasts_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)