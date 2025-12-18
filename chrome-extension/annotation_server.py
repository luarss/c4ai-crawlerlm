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


class GoldenAnnotation(BaseModel):
    example_html: str
    expected_json: dict[str, Any]


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


class CountsResponse(BaseModel):
    success: bool
    counts: dict[str, int]


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
    """Get list of domains from DOMAIN_LIST.md"""
    try:
        # Read domain list from DOMAIN_LIST.md
        domain_file = Path(__file__).parent.parent / "DOMAIN_LIST.md"

        if not domain_file.exists():
            raise HTTPException(status_code=404, detail="DOMAIN_LIST.md not found")

        # Parse markdown to extract domains
        domains = []
        with open(domain_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines, headers, and comments
                if not line or line.startswith("#") or line.startswith("**Note"):
                    continue
                # Extract domains from markdown list items
                if line.startswith("-"):
                    # Format: "- **domain.com** - Description" or "- domain.com - Description"
                    parts = line.split("**")
                    # Extract from bold markdown or plain text after dash
                    domain = parts[1].strip() if len(parts) >= 3 else line.split("-", 1)[1].strip().split()[0]

                    # Clean domain (remove trailing slashes, paths, etc.)
                    domain = domain.split("/")[0].strip()

                    if domain and "." in domain:
                        # Add https:// prefix
                        url = f"https://{domain}"
                        if url not in domains:
                            domains.append(url)

        print(f"📋 Loaded {len(domains)} domains from DOMAIN_LIST.md")

        return URLListResponse(success=True, urls=domains, count=len(domains))

    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error loading domains: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/counts", response_model=CountsResponse)
async def get_counts():
    """Get count of annotations by type"""
    try:
        # Initialize counts for all fragment types
        counts = {
            "recipe": 0,
            "event": 0,
            "pricing_table": 0,
            "job_posting": 0,
            "person": 0,
            "error_page": 0,
            "auth_required": 0,
            "empty_shell": 0,
        }

        # Count existing annotations in data/manual directory
        save_dir = Path(__file__).parent.parent / "data" / "manual"

        if save_dir.exists():
            for filepath in save_dir.glob("annotation_*.json"):
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)
                        fragment_type = data.get("expected_json", {}).get("type")
                        if fragment_type in counts:
                            counts[fragment_type] += 1
                except Exception as e:
                    print(f"Warning: Could not read {filepath.name}: {e}")
                    continue

        print(f"📊 Annotation counts: {counts}")
        return CountsResponse(success=True, counts=counts)

    except Exception as e:
        print(f"✗ Error counting annotations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/save", response_model=SaveResponse)
async def save_annotation(annotation: Annotation):
    """Save annotation to data/manual directory in golden.jsonl format"""
    try:
        # Generate filename
        fragment_type = annotation.label.get("type", "unknown")
        timestamp = annotation.timestamp.replace(":", "-").replace(".", "-")[:19]
        filename = f"annotation_{fragment_type}_{timestamp}.json"

        # Save to data/manual directory
        save_dir = Path(__file__).parent.parent / "data" / "manual"
        save_dir.mkdir(parents=True, exist_ok=True)

        filepath = save_dir / filename

        # Convert to golden.jsonl format
        golden_format = GoldenAnnotation(example_html=annotation.html, expected_json=annotation.label)

        # Write JSON file in golden.jsonl format
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(golden_format.model_dump(), f, indent=2, ensure_ascii=False)

        # Log success
        print(f"✓ Saved: {filename} ({len(annotation.html)} chars)")
        print(f"  Type: {fragment_type}")
        print(f"  URL: {annotation.url[:80]}...")

        return SaveResponse(success=True, filename=filename, path=str(filepath))

    except Exception as e:
        print(f"✗ Error saving annotation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "HTML Fragment Annotation Server",
        "endpoints": {
            "/urls": "GET - Fetch URL list",
            "/counts": "GET - Get annotation counts by type",
            "/save": "POST - Save annotation",
        },
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
    print("  GET  /urls   - Fetch URL list")
    print("  GET  /counts - Get annotation counts by type")
    print("  POST /save   - Save annotation")
    print()
    print("Instructions:")
    print("1. Keep this server running")
    print("2. Use Chrome extension to annotate HTML fragments")
    print("3. Annotations will be automatically saved here")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    uvicorn.run("annotation_server:app", host="localhost", port=8000, reload=True)


if __name__ == "__main__":
    main()
