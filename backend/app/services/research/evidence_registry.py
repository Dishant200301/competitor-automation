import os
import csv
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class EvidenceRegistry:
    """
    Centralized, evidence-first registry for all research findings.
    Ensures every claim is traceable to a specific source URL, title,
    extraction method, and verification status.
    """
    def __init__(self, run_id: str, target_company: str = ""):
        self.run_id = run_id
        self.target_company = target_company
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.evidence: List[Dict[str, Any]] = []

    def register_source(
        self,
        source_url: str,
        source_type: str = "target_website",
        page_title: str = "",
        company: str = ""
    ) -> str:
        """Register or update a source URL. Returns a unique source_id."""
        if not source_url:
            return ""
        
        # Key by normalized URL
        norm_url = source_url.strip()
        for s_id, s_data in self.sources.items():
            if s_data["source_url"] == norm_url:
                if page_title and not s_data["page_title"]:
                    s_data["page_title"] = page_title
                return s_id

        source_id = f"SRC-{len(self.sources) + 1:04d}"
        self.sources[source_id] = {
            "source_id": source_id,
            "company": company or self.target_company or "Target Entity",
            "source_url": norm_url,
            "source_type": source_type,
            "page_title": page_title or "Web Document",
            "date_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "status": "Verified"
        }
        return source_id

    def add_evidence(
        self,
        claim: str,
        field: str,
        value: Any,
        source_url: str,
        source_title: str = "",
        evidence_text: str = "",
        evidence_location: str = "body",
        extraction_method: str = "deterministic_extraction",
        confidence: str = "HIGH",
        verification_status: str = "Verified",
        company: str = ""
    ) -> Dict[str, Any]:
        """Record a single verifiable claim mapped to a source."""
        source_id = self.register_source(
            source_url=source_url,
            source_type="target_website" if "label-s4u" in source_url or "target" in field.lower() else "competitor_or_search",
            page_title=source_title,
            company=company or self.target_company
        )

        evidence_id = f"EVD-{len(self.evidence) + 1:05d}"
        val_str = str(value) if value is not None else "Not found"
        
        entry = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "claim": claim,
            "field": field,
            "value": val_str,
            "source_url": source_url,
            "source_title": source_title or (self.sources.get(source_id, {}).get("page_title", "")),
            "evidence_text": (evidence_text or val_str)[:400].strip(),
            "evidence_location": evidence_location,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "verification_status": verification_status,
            "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        }
        self.evidence.append(entry)
        return entry

    def get_sources_list(self) -> List[Dict[str, Any]]:
        return list(self.sources.values())

    def get_evidence_list(self) -> List[Dict[str, Any]]:
        return self.evidence

    def export_csv(self, output_dir: str):
        """Export sources.csv and evidence.csv into the specified directory."""
        os.makedirs(output_dir, exist_ok=True)
        
        sources_path = os.path.join(output_dir, "sources.csv")
        with open(sources_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["source_id", "company", "source_url", "source_type", "page_title", "date_checked", "status"]
            )
            writer.writeheader()
            for s in self.sources.values():
                writer.writerow(s)

        evidence_path = os.path.join(output_dir, "evidence.csv")
        with open(evidence_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "evidence_id", "source_id", "claim", "field", "value",
                    "source_url", "source_title", "evidence_text", "evidence_location",
                    "extraction_method", "confidence", "verification_status", "extracted_at"
                ]
            )
            writer.writeheader()
            for ev in self.evidence:
                writer.writerow(ev)
