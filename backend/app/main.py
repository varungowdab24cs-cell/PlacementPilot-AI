from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import get_settings
from backend.app.database import init_db
from backend.app.routers.auth import router as auth_router
from backend.app.routers.assessments import router as assessments_router
from backend.app.routers.adaptive import router as adaptive_router
from backend.app.routers.catalog import router as catalog_router
from backend.app.routers.chat import router as chat_router
from backend.app.routers.external_problems import router as external_problems_router
from backend.app.routers.research import router as research_router
from backend.app.routers.health import router as health_router
from backend.app.routers.questions import router as questions_router
from backend.app.routers.students import router as students_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(questions_router)
app.include_router(assessments_router)
app.include_router(adaptive_router)
app.include_router(students_router)
app.include_router(chat_router)
app.include_router(external_problems_router)
app.include_router(research_router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred."},
    )
