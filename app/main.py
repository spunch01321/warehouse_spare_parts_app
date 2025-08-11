# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from .routes import users, annotations, service
from .pdf_utils import render_pdf_page_to_png
from fastapi.responses import StreamingResponse
from fastapi import File, UploadFile

# Create DB tables (dev). In prod use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Warehouse Spare Parts API (multi-tenant)")

# CORS
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(annotations.router)
app.include_router(service.router)

@app.post("/pdf/render")
async def render_pdf(file: UploadFile = File(...), page: int = 0, zoom: float = 1.5):
    data = await file.read()
    png, w, h = render_pdf_page_to_png(data, page_number=page, zoom=zoom)
    return StreamingResponse(io.BytesIO(png), media_type="image/png")
