"""
Fluid AI — Main Application
FastAPI server with the /agent endpoint that orchestrates the full
autonomous pipeline: planning → execution → reflection → document generation.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import OUTPUT_DIR
from models.schemas import (
    AgentRequest,
    AgentResponse,
    ErrorResponse,
    StepStatus,
)
from agent.llm_client import LLMClient
from agent.planner import Planner
from agent.executor import Executor
from agent.reflection import Reflector
from agent.document import DocumentGenerator
from agent.pdf_converter import convert_docx_to_pdf

# ─── Logging Setup ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-22s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fluid_ai.main")

# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Fluid AI — Autonomous Document Agent",
    description=(
        "An autonomous AI agent that accepts natural language requests, "
        "plans and executes tasks step-by-step, and produces polished "
        "Microsoft Word (.docx) documents."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Serve the Web UI frontend, or return status if requested as JSON."""
    index_file = Path(__file__).resolve().parent / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return {
        "service": "Fluid AI",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ─── Agent Endpoint ─────────────────────────────────────────────────────────

@app.post(
    "/agent",
    response_model=AgentResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Agent"],
    summary="Execute an autonomous agent task",
    description=(
        "Accepts a natural language request, autonomously plans the work, "
        "executes each step, performs quality review, and generates a "
        "professional Word document."
    ),
)
async def run_agent(request: AgentRequest):
    """
    Main agent endpoint — the full autonomous pipeline.

    Pipeline stages:
    1. **Planning**: LLM decomposes the request into ordered steps
    2. **Execution**: Each step is executed with retry logic
    3. **Reflection**: Quality self-check with optional refinement
    4. **Document Generation**: Polished .docx output
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info(f"NEW REQUEST: {request.request[:100]}...")
    logger.info("=" * 60)

    try:
        # Initialize components with shared LLM client
        llm = LLMClient()
        planner = Planner(llm_client=llm)
        executor = Executor(llm_client=llm)
        reflector = Reflector(llm_client=llm)

        # ── Stage 1: Planning ────────────────────────────────────────
        logger.info("📋 STAGE 1: Planning...")
        plan = planner.create_plan(request.request)
        logger.info(
            f"Plan: '{plan.document_title}' ({plan.document_type}) "
            f"with {len(plan.steps)} steps"
        )

        # ── Stage 2: Execution ───────────────────────────────────────
        logger.info("⚡ STAGE 2: Executing steps...")
        step_results = executor.execute_plan(plan, request.request)

        completed_steps = sum(
            1 for r in step_results if r.status == StepStatus.COMPLETED
        )
        total_retries = sum(r.retries_used for r in step_results)
        logger.info(
            f"Execution: {completed_steps}/{len(step_results)} steps completed, "
            f"{total_retries} total retries"
        )

        # ── Stage 3: Reflection ──────────────────────────────────────
        logger.info("🔍 STAGE 3: Quality review...")
        reflection = reflector.review(plan, step_results, request.request)
        logger.info(f"Quality score: {reflection.quality_score}/10")

        # ── Stage 4: Document Generation ─────────────────────────────
        logger.info("📄 STAGE 4: Generating document...")
        doc_gen = DocumentGenerator()
        doc_path = doc_gen.generate(plan, step_results, reflection, request.request)
        logger.info(f"Document saved: {doc_path}")

        # Convert to PDF
        pdf_path = None
        pdf_url = None
        try:
            pdf_path = convert_docx_to_pdf(doc_path)
            pdf_url = f"/documents/{pdf_path.name}"
            logger.info(f"PDF saved: {pdf_path}")
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

        # ── Build Response ───────────────────────────────────────────
        elapsed = time.time() - start_time
        has_failures = any(
            r.status == StepStatus.FAILED for r in step_results
        )
        status = "partial_failure" if has_failures else "success"

        response = AgentResponse(
            status=status,
            request_summary=request.request[:200],
            execution_plan=plan,
            step_results=step_results,
            reflection=reflection,
            document_path=str(doc_path),
            document_download_url=f"/documents/{doc_path.name}",
            pdf_download_url=pdf_url,
            summary=(
                f"Successfully generated '{plan.document_title}' "
                f"({plan.document_type.replace('_', ' ')}) in {elapsed:.1f}s. "
                f"{completed_steps}/{len(step_results)} steps completed"
                f"{f', {total_retries} retries used' if total_retries > 0 else ''}. "
                f"Quality score: {reflection.quality_score}/10. "
                f"Document saved to: {doc_path.name}"
            ),
        )

        logger.info(f"✅ Request completed in {elapsed:.1f}s")
        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {e}",
        )

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {type(e).__name__}: {e}",
        )


# ─── API Key Configuration Endpoint ────────────────────────────────────────

from pydantic import BaseModel as PydanticBase

class ApiKeyUpdate(PydanticBase):
    api_key: str

@app.get("/api/key-status", tags=["Config"])
async def get_key_status():
    from config import GROQ_API_KEY
    import os
    current_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
    is_set = bool(current_key and current_key.strip())
    masked = f"{current_key[:8]}...{current_key[-4:]}" if is_set and len(current_key) > 12 else "Not configured"
    return {"configured": is_set, "masked_key": masked}

@app.post("/api/update-key", tags=["Config"])
async def update_api_key(payload: ApiKeyUpdate):
    new_key = payload.api_key.strip()
    if not new_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Invalid Groq key format. Groq API keys start with 'gsk_'")
    
    import os
    os.environ["GROQ_API_KEY"] = new_key
    
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        import re
        if re.search(r"^GROQ_API_KEY=.*$", content, flags=re.MULTILINE):
            content = re.sub(r"^GROQ_API_KEY=.*$", f"GROQ_API_KEY={new_key}", content, flags=re.MULTILINE)
        else:
            content += f"\nGROQ_API_KEY={new_key}\n"
        env_path.write_text(content, encoding="utf-8")
    
    return {"status": "success", "message": "API key successfully updated and saved to .env"}

@app.get(
    "/documents/{filename}",
    tags=["Documents"],
    summary="Download a generated document (.docx or .pdf)",
)
async def download_document(filename: str):
    """Download a generated document, converting to PDF on-the-fly if needed."""
    filepath = OUTPUT_DIR / filename
    ext = filepath.suffix.lower()

    if ext not in [".docx", ".pdf"]:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files can be downloaded")

    # If PDF is requested but doesn't exist, try to generate it from corresponding .docx
    if ext == ".pdf" and not filepath.exists():
        docx_source = filepath.with_suffix(".docx")
        if docx_source.exists():
            try:
                filepath = convert_docx_to_pdf(docx_source)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
        else:
            raise HTTPException(status_code=404, detail=f"Document not found: {filename}")

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {filename}")

    media_type = (
        "application/pdf"
        if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filename,
    )


# ─── List Documents Endpoint ────────────────────────────────────────────────

@app.get(
    "/documents",
    tags=["Documents"],
    summary="List all generated documents",
)
async def list_documents():
    """List all generated documents with Word and PDF download availability."""
    docx_files = sorted(OUTPUT_DIR.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for doc in docx_files:
        pdf_name = doc.with_suffix(".pdf").name
        pdf_file = OUTPUT_DIR / pdf_name
        pdf_exists = pdf_file.exists()
        
        items.append({
            "filename": doc.name,
            "title": doc.stem.replace("_", " "),
            "download_url": f"/documents/{doc.name}",
            "pdf_url": f"/documents/{pdf_name}",
            "pdf_available": pdf_exists,
            "size_bytes": doc.stat().st_size,
            "created": doc.stat().st_mtime,
        })
    return {"documents": items}
