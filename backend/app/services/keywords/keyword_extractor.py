import re
from collections import Counter
from datetime import datetime, timezone
from typing import List, Dict, Any

GENERIC_NOISE_TERMS = {
    "price", "regular", "sale", "tax", "included", "shipping", "calculated", "checkout",
    "view", "quick", "cart", "item", "items", "home", "filter", "sort", "add", "all",
    "free", "delivery", "policy", "policies", "contact", "about", "subscribe", "newsletter",
    "terms", "conditions", "privacy", "page", "search", "menu", "close", "open", "order",
    "orders", "account", "login", "register", "customer", "reviews", "star", "rating",
    "copyright", "reserved", "rights", "powered", "shopify", "woocommerce", "select",
    "options", "default", "title", "quantity", "unit", "sold", "out", "stock", "color",
    "size", "guide", "small", "medium", "large", "xl", "xxl", "xs", "pack", "piece"
}

ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your",
    "yours", "yourself", "yourselves", "will"
}

class KeywordExtractor:
    """
    Search-Intent & Keyword Research Engine.
    Distinguishes on-page website terms from true multi-token search queries,
    assigns search intent, builds semantic clusters, and guarantees zero fabricated search volume.
    """
    def extract_keywords(
        self,
        pages: List[Dict[str, Any]],
        company_name: str = "",
        industry: str = "",
        sub_industry: str = "",
        categories: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        categories = categories or []
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # 1. Collect prominent title & header phrases
        prominent_phrases = []
        source_url_map = {}

        # First add discovered categories as high-intent keywords
        for cat in categories:
            cat_name = cat.get("category_name", "").strip()
            if cat_name and len(cat_name) > 3:
                prominent_phrases.append(cat_name)
                source_url_map[cat_name.lower()] = cat.get("url")

        for p in pages:
            url = p.get("url", "")
            title = p.get("title", "")
            if title:
                # Clean title separators
                for chunk in re.split(r"[|\-–—:]", title):
                    clean_chunk = chunk.strip()
                    if 4 < len(clean_chunk) < 60:
                        prominent_phrases.append(clean_chunk)
                        source_url_map[clean_chunk.lower()] = url

            for h in p.get("h1", []) + p.get("h2", [])[:3]:
                clean_h = h.strip()
                if 4 < len(clean_h) < 60:
                    prominent_phrases.append(clean_h)
                    source_url_map[clean_h.lower()] = url

        # 2. Extract multi-word n-grams from headings and meta descriptions
        all_text_snippets = []
        for p in pages:
            all_text_snippets.append(p.get("meta_description", ""))
            all_text_snippets.extend(p.get("h1", []))
            all_text_snippets.extend(p.get("h2", [])[:4])

        combined_text = " ".join(all_text_snippets).lower()
        cleaned_words = [w for w in re.findall(r"\b[a-z]{3,}\b", combined_text) if w not in ENGLISH_STOPWORDS]

        # Bigrams & Trigrams
        ngrams = []
        for i in range(len(cleaned_words) - 1):
            w1, w2 = cleaned_words[i], cleaned_words[i+1]
            if w1 not in GENERIC_NOISE_TERMS and w2 not in GENERIC_NOISE_TERMS:
                ngrams.append(f"{w1} {w2}")
        for i in range(len(cleaned_words) - 2):
            w1, w2, w3 = cleaned_words[i], cleaned_words[i+1], cleaned_words[i+2]
            if w1 not in GENERIC_NOISE_TERMS and w2 not in GENERIC_NOISE_TERMS and w3 not in GENERIC_NOISE_TERMS:
                ngrams.append(f"{w1} {w2} {w3}")

        ngram_counts = Counter(ngrams)

        # 3. Construct Search Keywords with Intent & Clustering
        search_keywords = []
        seen_kws = set()

        # A. Brand & Navigational Keywords
        clean_comp = company_name.strip()
        if clean_comp:
            brand_variants = [
                clean_comp.lower(),
                f"{clean_comp.lower()} online",
                f"{clean_comp.lower()} official website",
            ]
            if "fashion" in industry.lower():
                brand_variants.append(f"{clean_comp.lower()} collection")
            else:
                brand_variants.append(f"{clean_comp.lower()} platform")

            for bv in brand_variants:
                if bv not in seen_kws:
                    seen_kws.add(bv)
                    search_keywords.append({
                        "keyword": bv,
                        "cluster": "Brand & Navigational",
                        "intent": "Navigational",
                        "country": "India / Global",
                        "language": "en",
                        "source": "Target Brand Navigation",
                        "search_volume": "Not available from verified source",
                        "cpc": "Not available from verified source",
                        "source_url": pages[0].get("url", "") if pages else "",
                        "date_checked": now_str
                    })

        # B. Transactional & Commercial Keywords from Categories & Prominent Phrases
        for phrase in prominent_phrases:
            phrase_clean = phrase.strip().lower()
            if phrase_clean in seen_kws:
                continue
            
            # Filter noise
            if any(n in phrase_clean for n in ["home", "login", "register", "contact", "filter", "copyright"]):
                continue

            cluster = self._assign_cluster(phrase_clean, industry, sub_industry)
            intent = self._assign_intent(phrase_clean)
            seen_kws.add(phrase_clean)

            src_url = source_url_map.get(phrase_clean) or (pages[0].get("url") if pages else "")

            search_keywords.append({
                "keyword": phrase_clean,
                "cluster": cluster,
                "intent": intent,
                "country": "India / Global",
                "language": "en",
                "source": "Catalog / Page Architecture",
                "search_volume": "Not available from verified source",
                "cpc": "Not available from verified source",
                "source_url": src_url,
                "date_checked": now_str
            })
            if len(search_keywords) >= 15:
                break

        # C. Add top frequent 2-word n-grams as Commercial terms
        for ngram, cnt in ngram_counts.most_common(12):
            ng_clean = ngram.lower()
            if ng_clean not in seen_kws and len(search_keywords) < 22:
                seen_kws.add(ng_clean)
                cluster = self._assign_cluster(ng_clean, industry, sub_industry)
                intent = self._assign_intent(ng_clean)
                search_keywords.append({
                    "keyword": ng_clean,
                    "cluster": cluster,
                    "intent": intent,
                    "country": "India / Global",
                    "language": "en",
                    "source": "Content Co-occurrence Extraction",
                    "search_volume": "Not available from verified source",
                    "cpc": "Not available from verified source",
                    "source_url": pages[0].get("url", "") if pages else "",
                    "date_checked": now_str
                })

        # 4. Generate Semantic Keyword Clusters Summary
        clusters_summary = {}
        for kw in search_keywords:
            c_name = kw["cluster"]
            if c_name not in clusters_summary:
                clusters_summary[c_name] = []
            clusters_summary[c_name].append(kw["keyword"])

        return KeywordBundle(
            search_keywords=search_keywords,
            keyword_clusters=clusters_summary
        )

    def _assign_intent(self, term: str) -> str:
        t_low = term.lower()
        if any(w in t_low for w in ["buy", "order", "price", "shop", "store", "sale", "online", "collection", "sets", "set"]):
            return "Transactional"
        elif any(w in t_low for w in ["best", "top", "designer", "trends", "exclusive", "latest", "luxury"]):
            return "Commercial Investigation"
        elif any(w in t_low for w in ["how", "what", "guide", "style", "history", "ideas"]):
            return "Informational"
        return "Commercial Investigation"

    def _assign_cluster(self, term: str, industry: str, sub_industry: str) -> str:
        t_low = term.lower()
        if any(w in t_low for w in ["suit", "anarkali", "sharara", "salwar", "kurta", "kurti", "ethnic"]):
            return "Ethnic & Traditional Suits"
        elif any(w in t_low for w in ["indo", "western", "co-ord", "fusion", "modern"]):
            return "Indo-Western & Fusion Wear"
        elif any(w in t_low for w in ["wedding", "marriage", "bridal", "festive", "drapes", "lehenga"]):
            return "Wedding & Festive Occasion Wear"
        elif any(w in t_low for w in ["kaftan", "shirt", "top", "ready"]):
            return "Contemporary Daily & Resort Wear"
        return f"{industry} Core Offerings" if industry else "Core Commercial Keywords"

class KeywordBundle(list):
    def __init__(self, search_keywords, keyword_clusters):
        super().__init__(search_keywords)
        self.search_keywords = search_keywords
        self.keyword_clusters = keyword_clusters
        self.total_keywords = len(search_keywords)

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "search_keywords": return self.search_keywords
            if item == "keyword_clusters": return self.keyword_clusters
            if item == "total_keywords": return self.total_keywords
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

keyword_extractor = KeywordExtractor()
