from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ResearchCreateRequest(BaseModel):
    company_name: Optional[str] = None
    product_url: Optional[str] = None
    service_url: Optional[str] = None
    social_url: Optional[str] = None
    source_type: Optional[str] = Field(default="website", description="website, social, company, product, or service")
    source_input: Optional[str] = Field(default=None, description="Target URL, company, handle, or product")
    # Flexible field aliases
    sourceInput: Optional[str] = None
    url: Optional[str] = None
    input: Optional[str] = None
    website: Optional[str] = None
    target: Optional[str] = None

    def get_effective_input(self) -> str:
        val = self.source_input or self.sourceInput or self.url or self.input or self.website or self.target or ""
        return val.strip()

    def get_effective_type(self) -> str:
        t = (self.source_type or "website").strip().lower()
        return t if t in ("website", "social", "company", "product", "service") else "website"

class ResearchCreateResponse(BaseModel):
    research_run_id: str
    run_id: Optional[str] = None
    status: str
    message: str

class ResearchRunResponse(BaseModel):
    id: str
    source_type: str
    source_input: str
    status: str
    current_step: Optional[str] = None
    progress_percentage: int = 0
    error_message: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: str
    updated_at: str

class ResearchSummaryResponse(BaseModel):
    run: ResearchRunResponse
    company: Optional[Dict[str, Any]] = None
    competitors: List[Dict[str, Any]] = Field(default_factory=list)
    pages_count: int = 0
    products_count: int = 0
    categories_count: int = 0
    services_count: int = 0
    keywords_count: int = 0
    validation_report: Optional[Dict[str, Any]] = None

# Aliases for flexible requests
class ResearchRequest(ResearchCreateRequest):
    pass
