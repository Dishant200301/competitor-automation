import uuid
from app.extraction.pages import now

UNKNOWN = "Not found"


class EvidenceRegistry:
    def __init__(self):
        self.sources, self.evidence = [], []
        self.by_url = {}

    def source(self, page):
        url = page["url"]
        if url not in self.by_url:
            record = {"id": str(uuid.uuid4()), "url": url, "source_type": "public_website", "page_title": page.get("title", ""),
                      "date_checked": page.get("date_checked", now()), "content_hash": page.get("content_hash"),
                      "verification_status": "verified" if page.get("http_status") == 200 else "unverified"}
            self.by_url[url] = record
            self.sources.append(record)
        return self.by_url[url]

    def claim(self, page, field, value, text, method="structured_data", confidence=.95):
        source = self.source(page)
        eid = str(uuid.uuid4())
        self.evidence.append({"id": eid, "source_id": source["id"], "source_url": source["url"],
            "source_type": source["source_type"], "page_title": source["page_title"], "date_checked": source["date_checked"],
            "extracted_field": field, "value": value, "evidence_text": str(text)[:3000],
            "extraction_method": method, "verification_status": source["verification_status"], "confidence": confidence})
        return eid


def record(values, page, registry, method="structured_data", excerpt=None):
    result = {"id": str(uuid.uuid4()), **values, "source_url": page["url"], "date_checked": page.get("date_checked", now()),
              "verification_status": "verified", "evidence_ids": [], "field_evidence": {}}
    for field, value in values.items():
        if value is None or value == "" or value == UNKNOWN or value == "Not verified" or value == []: continue
        eid = registry.claim(page, field, value, excerpt if excerpt else str(value), method)
        result["evidence_ids"].append(eid)
        result["field_evidence"][field] = eid
    return result
