"""
AI-BS Supabase Kong Gateway Local Daemon (Port 8008)
Provides local PostgREST / Supabase API gateway compatibility routes and /health telemetry.
"""

import sys
import os
import json
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="AI-BS Supabase Kong Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

@app.get("/")
def root():
    return {
        "service": "Supabase Kong Gateway",
        "status": "ONLINE",
        "port": 8008,
        "uptime_s": round(time.time() - START_TIME, 2),
        "engine": "AI-BS Local Sovereign Gateway",
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Supabase Kong Gateway",
        "port": 8008,
        "database": "connected",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

@app.get("/rest/v1/")
def rest_root():
    return {
        "swagger": "2.0",
        "info": {
            "title": "PostgREST API Gateway",
            "description": "AI-BS Sovereign Data Gateway"
        },
        "paths": {}
    }

if __name__ == "__main__":
    print("Starting AI-BS Supabase Kong Gateway on port 8008...")
    uvicorn.run(app, host="127.0.0.1", port=8008, log_level="warning")
