# Warehouse Service — Multi-tenant App (FastAPI + Streamlit)

This repository contains a multi-tenant-ready backend (FastAPI) and a Streamlit client for viewing PDF drawings with calibrated scaling, adding annotations, and submitting "Request Service" tickets.

## Features
- FastAPI backend with tenant-aware SQL models (Postgres)
- Local username/password authentication and Microsoft OAuth (placeholder integration)
- PDF rendering via PyMuPDF for crisp images
- Streamlit frontend for customer UI (annotations, calibration, request service)
- Docker + docker-compose for local dev (Postgres + backend + client)

## Quick start (local)
1. Copy `.env.example` to `.env` and fill secrets (especially `JWT_SECRET`).
2. Build and run:
   ```bash
   ./start.sh
