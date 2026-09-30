from typing import List, Dict, Any

class ServiceExtractor:
    def extract_from_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        services = []
        seen = set()

        for page in pages:
            # 1. JSON-LD Service
            for item in page.get("structured_data", []):
                item_type = str(item.get("@type", "")).lower()
                if "service" in item_type:
                    s_name = item.get("name")
                    if s_name and s_name.lower() not in seen:
                        seen.add(s_name.lower())
                        services.append({
                            "service_name": s_name,
                            "category": "Professional Service",
                            "description": item.get("description", "Identified via Schema.org Service data.")
                        })

            # 2. Heuristics from SERVICE or SOLUTIONS pages
            if page.get("page_type") in ("SERVICE", "OTHER"):
                for heading in page.get("h1", []) + page.get("h2", [])[:4]:
                    cleaned = heading.strip()
                    if 4 < len(cleaned) < 50 and cleaned.lower() not in seen:
                        if any(kw in cleaned.lower() for kw in ["service", "consulting", "managed", "support", "integration", "migration", "solution"]):
                            seen.add(cleaned.lower())
                            services.append({
                                "service_name": cleaned,
                                "category": "Consulting & Support",
                                "description": f"Service offering discovered on {page.get('url')}."
                            })

        return services

service_extractor = ServiceExtractor()
