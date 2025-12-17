#!/usr/bin/env python3
"""
Local server for receiving annotations from Chrome extension.
Saves annotations to ../data/manual/

Usage:
    uvicorn annotation_server:app --host localhost --port 8000
    OR
    python annotation_server.py
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# Pydantic models
class Annotation(BaseModel):
    html: str
    label: dict[str, Any]
    url: str
    timestamp: str


class SaveResponse(BaseModel):
    success: bool
    filename: str
    path: str


class URLListResponse(BaseModel):
    success: bool
    urls: list[str]
    count: int


class ErrorResponse(BaseModel):
    success: bool
    error: str


# FastAPI app
app = FastAPI(title="HTML Fragment Annotation Server")

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/urls", response_model=URLListResponse)
async def get_urls():
    """Get list of URLs from selected_url_list.txt"""
    try:
        # Read URL list from data/selected_url_list.txt
        url_file = Path(__file__).parent.parent / 'data' / 'selected_url_list.txt'

        if not url_file.exists():
            raise HTTPException(status_code=404, detail="selected_url_list.txt not found")

        # Read URLs (skip empty lines)
        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"📋 Loaded {len(urls)} URLs from selected_url_list.txt")

        return URLListResponse(success=True, urls=urls, count=len(urls))

    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error loading URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save", response_model=SaveResponse)
async def save_annotation(annotation: Annotation):
    """Save annotation to data/manual directory"""
    try:
        # Generate filename
        fragment_type = annotation.label.get('type', 'unknown')
        timestamp = annotation.timestamp.replace(':', '-').replace('.', '-')[:19]
        filename = f"annotation_{fragment_type}_{timestamp}.json"

        # Save to data/manual directory
        save_dir = Path(__file__).parent.parent / 'data' / 'manual'
        save_dir.mkdir(parents=True, exist_ok=True)

        filepath = save_dir / filename

        # Write JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(annotation.model_dump(), f, indent=2, ensure_ascii=False)

        # Log success
        print(f"✓ Saved: {filename} ({len(annotation.html)} chars)")
        print(f"  Type: {fragment_type}")
        print(f"  URL: {annotation.url[:80]}...")

        return SaveResponse(success=True, filename=filename, path=str(filepath))

    except Exception as e:
        print(f"✗ Error saving annotation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "HTML Fragment Annotation Server",
        "endpoints": {
            "/urls": "GET - Fetch URL list",
            "/save": "POST - Save annotation"
        }
    }


def main():
    """Run server with uvicorn"""
    import uvicorn

    print("=" * 60)
    print("🚀 Annotation Server Running")
    print("=" * 60)
    print("Listening on: http://localhost:8000")
    print("Saving to: ../data/manual/")
    print()
    print("Endpoints:")
    print("  GET  /urls  - Fetch URL list")
    print("  POST /save  - Save annotation")
    print()
    print("Instructions:")
    print("1. Keep this server running")
    print("2. Use Chrome extension to annotate HTML fragments")
    print("3. Annotations will be automatically saved here")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    uvicorn.run(app, host="localhost", port=8000)


if __name__ == '__main__':
    main()
