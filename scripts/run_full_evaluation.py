#!/usr/bin/env python3
"""
Script completo de ingesta y evaluación para PetroQuery.
1. Login como evaluator
2. Ingesta todos los PDFs en data/pdfs_og/
3. Espera procesamiento
4. Corre evaluación con dataset
"""

import asyncio
import httpx
import json
import os
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
PDF_DIR = Path("/home/sayer/Proyectos/petroquery/data/pdfs_og")

evaluator_token = None
uploaded_docs = []

async def login():
    global evaluator_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "evaluator", "password": "evaluator123"}
        )
        data = resp.json()
        evaluator_token = data["access_token"]
        print(f"✅ Logged in as evaluator")

async def prewarm_model(token: str) -> None:
    """Pre-warm the E5 embedding model before evaluation."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/admin/prewarm",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 200:
            print(f"✅ Modelo pre-cargado (E5)")
        else:
            print(f"⚠️ Pre-warm no disponible ({resp.status_code}), continuando...")

async def upload_pdf(filepath: Path, project_id: int = 1):
    """Upload a PDF and return document_id."""
    async with httpx.AsyncClient() as client:
        with open(filepath, "rb") as f:
            resp = await client.post(
                f"{BASE_URL}/api/v1/ingest/pdf",
                headers={"Authorization": f"Bearer {evaluator_token}"},
                files={"file": (filepath.name, f, "application/pdf")},
                data={
                    "project_id": str(project_id),
                    "title": filepath.stem,
                    "og_metadata": json.dumps({
                        "cuenca": "Vaca Muerta",
                        "tipo_documento": "manual" if "MANUAL" in filepath.name else "normativa" if "NORMATIVA" in filepath.name else "reporte",
                        "normativa_aplicable": "API RP 53" if "BOP" in filepath.name or "EQUIPOS" in filepath.name else "IAPG-IRAM 301"
                    })
                }
            )
        if resp.status_code == 202:
            data = resp.json()
            print(f"  📤 Uploaded: {filepath.name} -> doc_id={data['document_id']}")
            return data["document_id"]
        else:
            print(f"  ❌ Failed: {filepath.name} -> {resp.status_code}: {resp.text[:100]}")
            return None

async def wait_for_processing(doc_id: int, timeout: int = 120):
    """Wait for document to finish processing."""
    async with httpx.AsyncClient() as client:
        start = time.time()
        while time.time() - start < timeout:
            resp = await client.get(
                f"{BASE_URL}/api/v1/ingest/status/{doc_id}",
                headers={"Authorization": f"Bearer {evaluator_token}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data["status"] == "completed":
                    print(f"  ✅ Completed: doc_id={doc_id}")
                    return True
                elif data["status"] == "failed":
                    print(f"  ❌ Failed: doc_id={doc_id}")
                    return False
            await asyncio.sleep(2)
        print(f"  ⏱️ Timeout: doc_id={doc_id}")
        return False

async def ingest_all_pdfs():
    """Ingest all PDFs in the directory."""
    pdf_files = sorted([f for f in PDF_DIR.iterdir() if f.suffix.lower() == ".pdf"])
    print(f"\n📁 Found {len(pdf_files)} PDFs to ingest")
    
    for pdf_file in pdf_files:
        doc_id = await upload_pdf(pdf_file)
        if doc_id:
            uploaded_docs.append(doc_id)
    
    print(f"\n⏳ Waiting for {len(uploaded_docs)} documents to process...")
    for doc_id in uploaded_docs:
        await wait_for_processing(doc_id)
    
    print(f"\n✅ All documents processed!")

async def run_evaluation():
    """Run the evaluation script."""
    print("\n🧪 Running evaluation...")
    import subprocess
    result = subprocess.run(
        ["python", "scripts/evaluate_petroquery.py"],
        capture_output=True,
        text=True,
        cwd="/home/sayer/Proyectos/petroquery"
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])
    return result.returncode == 0

async def main():
    print("=" * 60)
    print("PETROQUERY - INGESTA Y EVALUACION COMPLETA")
    print("=" * 60)

    await login()
    await ingest_all_pdfs()

    print("\n🔥 Pre-cargando modelo E5 (30-60s)...")
    await prewarm_model(evaluator_token)

    print("\n⏳ Waiting 5s for index stabilization...")
    await asyncio.sleep(5)

    success = await run_evaluation()
    
    if success:
        print("\n🎉 Evaluation completed successfully!")
    else:
        print("\n⚠️ Evaluation had issues. Check output above.")

if __name__ == "__main__":
    asyncio.run(main())
