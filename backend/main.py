from dotenv import load_dotenv
load_dotenv()  # Reads backend/.env and loads GEMINI_API_KEY into the environment

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.rag_service import get_rag_response, format_citation_footer
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from labs_service import find_labs
from services.search_service import search_chunks
from services.standards_recommender import recommend_standards
from services.compliance_service import check_compliance
from fastapi import HTTPException

app = FastAPI(title="BIS Sahayak AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class Citation(BaseModel):
    standard_number: str | None
    clause: str | None
    page: int | None
    source_url: str | None


class ChatResponse(BaseModel):
    reply: str
    citations: list[Citation] = []


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = 5


class SearchResult(BaseModel):
    relevance_score: float
    standard_number: str | None
    document_title: str
    page_number: int | None
    section: str | None
    chunk_text: str
    source_url: str | None


class SearchResponse(BaseModel):
    results: list[SearchResult]

class RecommendRequest(BaseModel):
    product_description: str


class RecommendationEvidence(BaseModel):
    section: str | None
    page: int | None
    excerpt: str


class RecommendationCitation(BaseModel):
    standard_number: str | None
    clause: str | None
    page: int | None
    source_url: str | None


class Recommendation(BaseModel):
    standard_number: str | None
    title: str
    relevance: str
    reason: str
    requirement_status: str
    evidence: list[RecommendationEvidence]
    citations: list[RecommendationCitation]


class RecommendResponse(BaseModel):
    product_description: str
    recommendations: list[Recommendation] = []
    message: str | None = None
class ComplianceRequest(BaseModel):
    product_description: str


class ComplianceEvidence(BaseModel):
    section: str | None
    page: int | None
    excerpt: str


class ComplianceCitation(BaseModel):
    standard_number: str | None
    clause: str | None
    page: int | None
    source_url: str | None


class ComplianceRequirement(BaseModel):
    requirement: str
    status: str
    reason: str
    testing_requirement: str | None
    next_step: str | None


class ComplianceStandard(BaseModel):
    standard_number: str | None
    title: str
    requirements: list[ComplianceRequirement]
    evidence: list[ComplianceEvidence]
    citations: list[ComplianceCitation]


class ComplianceResponse(BaseModel):
    product_description: str
    standards: list[ComplianceStandard] = []
    limitations: str
    message: str | None = None




@app.get("/")
def read_root():
    return {"status": "BIS Sahayak AI backend is running"}

@app.get("/api/health/db")
def db_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "unreachable", "detail": str(e)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not request.message.strip():
        return ChatResponse(reply="Please enter a question for Sahayak.", citations=[])

    try:
        result = get_rag_response(db, request.message.strip())
        footer = format_citation_footer(result["citations"])
        return ChatResponse(reply=result["answer"] + footer, citations=result["citations"])
    except Exception as e:
        print(f"RAG error: {e}")
        return ChatResponse(
            reply="Sorry, Sahayak's AI service is having trouble right now. Please try again in a moment.",
            citations=[],
        )

@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest, db: Session = Depends(get_db)):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    top_k = request.top_k or 5
    if top_k < 1 or top_k > 20:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 20.")

    try:
        results = search_chunks(db, request.query.strip(), top_k)
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")

    return SearchResponse(results=results)

@app.post("/api/standards/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest, db: Session = Depends(get_db)):
    if not request.product_description or not request.product_description.strip():
        raise HTTPException(status_code=400, detail="product_description cannot be empty.")

    try:
        result = recommend_standards(db, request.product_description.strip())
    except Exception as e:
        print(f"Standards recommend error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Standards recommendation failed. Please try again.",
        )

    return RecommendResponse(**result)



@app.post("/api/compliance/check", response_model=ComplianceResponse)
def compliance_check(request: ComplianceRequest, db: Session = Depends(get_db)):
    if not request.product_description or not request.product_description.strip():
        raise HTTPException(status_code=400, detail="product_description cannot be empty.")

    try:
        result = check_compliance(db, request.product_description.strip())
    except Exception as e:
        print(f"Compliance check error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Compliance check failed. Please try again.",
        )

    return ComplianceResponse(**result)

class LabCitation(BaseModel):
    source_reference: str | None
    source_url: str | None


class LabResult(BaseModel):
    name: str
    location: str | None
    testing_capabilities: list[str]
    standard_numbers: list[str]
    recognition_or_accreditation: str | None
    reason: str
    citations: list[LabCitation]


class LabFindRequest(BaseModel):
    product_description: str
    standard_number: str | None = None


class LabFindResponse(BaseModel):
    product_description: str
    laboratories: list[LabResult] = []
    message: str | None = None
    limitations: list[str] = []


LABS_INSUFFICIENT_EVIDENCE_MSG = (
    "I could not verify suitable BIS laboratory information from the available sources."
)

LABS_DATA_LIMITATION = (
    "Laboratory results are limited to what has been explicitly entered into the "
    "laboratories table — the knowledge base currently has no automated laboratory "
    "ingestion pipeline, so this list is not exhaustive."
)


def _split_field(value: str | None) -> list[str]:
    """Splits a comma-separated DB text field into a clean list. Returns []
    for empty/null fields rather than [''] or [None]."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@app.post("/api/labs/find", response_model=LabFindResponse)
def labs_find(request: LabFindRequest, db: Session = Depends(get_db)):
    if not request.product_description or not request.product_description.strip():
        raise HTTPException(status_code=400, detail="product_description cannot be empty.")

    try:
        labs = find_labs(db, request.product_description.strip(), request.standard_number)
    except Exception as e:
        print(f"Labs find error: {e}")
        raise HTTPException(status_code=500, detail="Laboratory search failed. Please try again.")

    if not labs:
        return LabFindResponse(
            product_description=request.product_description,
            laboratories=[],
            message=LABS_INSUFFICIENT_EVIDENCE_MSG,
            limitations=[LABS_DATA_LIMITATION],
        )

    laboratories = [
        LabResult(
            name=lab.name,
            location=lab.location,
            testing_capabilities=_split_field(lab.capabilities),
            standard_numbers=_split_field(lab.standard_numbers),
            recognition_or_accreditation=lab.accreditation_info,
            reason=(
                f"Matched on '{request.product_description.strip()}' against this "
                "laboratory's stored name, location, or capabilities."
            ),
            citations=[
                LabCitation(
                    source_reference=lab.source_reference,
                    source_url=lab.source_url,
                )
            ],
        )
        for lab in labs
    ]

    return LabFindResponse(
        product_description=request.product_description,
        laboratories=laboratories,
        message=None,
        limitations=[LABS_DATA_LIMITATION],
    )