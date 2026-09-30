import re
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from app.utils.logger import logger

INDUSTRY_TAXONOMY = {
    "Fashion & Apparel": {
        "keywords": [
            "dress", "dresses", "kurta", "kurtas", "kurti", "kurtis", "suit", "suits",
            "anarkali", "anarkalis", "sharara", "shararas", "lehenga", "lehengas",
            "saree", "sarees", "ethnic", "indo-western", "co-ord", "co-ords", "gown",
            "gowns", "kaftan", "kaftans", "clothing", "wear", "outfit", "outfits",
            "apparel", "attire", "fashion", "boutique", "fabric", "bridal", "wedding wear",
            "festive wear", "salwar", "dupattas", "tops", "shirts", "garments"
        ],
        "default_sub": "Women's Ethnic & Modern Apparel",
        "default_model": "D2C E-commerce",
        "default_audience": "Women seeking ethnic, wedding, festive, and contemporary fashion"
    },
    "Technology & Software": {
        "keywords": [
            "software", "saas", "api", "apis", "cloud platform", "sdk", "developer tools",
            "devops", "database", "crm", "erp", "cybersecurity", "ai engine", "machine learning",
            "analytics platform", "open source code", "infrastructure", "workflow automation",
            "enterprise software", "b2b software", "microservices"
        ],
        "default_sub": "Enterprise & Cloud Software",
        "default_model": "B2B SaaS / Subscription",
        "default_audience": "Enterprises, developers, and digital operations teams"
    },
    "Healthcare & Medical": {
        "keywords": [
            "clinic", "hospital", "doctor", "physician", "patient", "treatment", "therapy",
            "surgery", "pharmaceutical", "diagnostic", "healthcare", "medicine", "clinical"
        ],
        "default_sub": "Medical & Clinical Healthcare",
        "default_model": "Healthcare Provider",
        "default_audience": "Patients and healthcare seekers"
    },
    "Food, Beverage & Hospitality": {
        "keywords": [
            "restaurant", "dining", "menu", "cuisine", "chef", "cafe", "coffee", "bakery",
            "food delivery", "gourmet", "dishes", "hotel", "resort", "lodging"
        ],
        "default_sub": "Dining & Hospitality",
        "default_model": "Hospitality / F&B",
        "default_audience": "Diners, travelers, and food consumers"
    },
    "Education & E-Learning": {
        "keywords": [
            "course", "courses", "academy", "training", "curriculum", "tuition", "students",
            "certification", "learning", "instructor", "bootcamp", "university"
        ],
        "default_sub": "Education & Online Training",
        "default_model": "Educational Platform",
        "default_audience": "Students, professionals, and lifelong learners"
    },
    "Professional Services & Agency": {
        "keywords": [
            "consulting", "agency", "marketing agency", "seo services", "branding agency",
            "design studio", "accounting firm", "legal services", "law firm", "advisory"
        ],
        "default_sub": "Consulting & Professional Services",
        "default_model": "Agency / Client Services",
        "default_audience": "Businesses and organizations seeking expert advisory"
    },
    "Manufacturing & Industrial": {
        "keywords": [
            "manufacturing", "industrial", "factory", "machinery", "fabrication", "supplier",
            "raw materials", "oem", "wholesale distribution", "bulk supply"
        ],
        "default_sub": "Industrial Manufacturing & Supply",
        "default_model": "B2B Wholesale / Manufacturing",
        "default_audience": "Industrial buyers, contractors, and distributors"
    }
}

