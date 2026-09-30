import re
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse

class ProductExtractor:
    """
    Dynamic Product, Category, and Collection Extraction Engine.
    Discovers e-commerce catalog structure, collections, products, pricing,
    and currency across modern platforms (Shopify, WooCommerce, custom).
    """
    def extract_from_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        discovered_categories = []
        discovered_products = []
        seen_category_slugs = set()
        seen_product_names = set()
        observed_prices = []
        currencies_found = set()

        # 1. Discover Collections & Categories from internal links & collection pages
        for page in pages:
            url = page.get("url", "")
            final_url = page.get("final_url", url)
            page_type = page.get("page_type", "")
            
            # Check for collection URLs in crawled page and in its links
            candidate_urls = [url, final_url] + page.get("internal_links", [])
            for c_url in candidate_urls:
                parsed = urlparse(c_url)
                path = parsed.path.strip("/")
                if "/collections/" in f"/{path}" or "/category/" in f"/{path}":
                    parts = path.split("/")
                    slug = parts[-1] if parts else ""
                    # Filter pagination, sort queries, or root
                    slug = re.sub(r"-\d+$", "", slug)  # remove trailing -1, -2
                    if slug and slug not in ("all", "frontpage", "collections", "category") and slug not in seen_category_slugs:
                        seen_category_slugs.add(slug)
                        cat_name = slug.replace("-", " ").replace("_", " ").title()
                        discovered_categories.append({
                            "category_name": cat_name,
                            "slug": slug,
                            "url": c_url,
                            "source_page": url
                        })

            # If current page is a COLLECTION page, get its primary heading
            if page_type == "COLLECTION":
                h1 = page.get("h1", [])
                if h1:
                    clean_h1 = h1[0].strip()
                    if 2 < len(clean_h1) < 45 and not any(skip in clean_h1.lower() for skip in ["filter", "sort", "home", "search", "menu"]):
                        slug_norm = clean_h1.lower().replace(" ", "-")
                        if slug_norm not in seen_category_slugs:
                            seen_category_slugs.add(slug_norm)
                            discovered_categories.append({
                                "category_name": clean_h1,
                                "slug": slug_norm,
                                "url": url,
                                "source_page": url
                            })

        # 2. Extract Products from JSON-LD Schema.org
        for page in pages:
            page_url = page.get("url", "")
            for item in page.get("structured_data", []):
                item_type = str(item.get("@type", "")).lower()
                if "product" in item_type:
                    p_name = item.get("name")
                    if p_name and p_name.strip().lower() not in seen_product_names:
                        p_clean = p_name.strip()
                        seen_product_names.add(p_clean.lower())
                        
                        offers = item.get("offers", {})
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        price_val = None
                        currency_val = "INR"
                        avail_val = "InStock"
                        if isinstance(offers, dict):
                            price_val = offers.get("price")
                            currency_val = offers.get("priceCurrency") or "INR"
                            avail_val = str(offers.get("availability", "InStock")).split("/")[-1]

                        if price_val:
                            try:
                                num_p = float(str(price_val).replace(",", ""))
                                observed_prices.append(num_p)
                                currencies_found.add(currency_val)
                            except Exception:
                                pass

                        discovered_products.append({
                            "product_name": p_clean,
                            "category": item.get("category") or self._guess_category(p_clean, discovered_categories),
                            "price": f"{currency_val} {price_val}" if price_val else "Not publicly disclosed",
                            "availability": avail_val,
                            "product_url": item.get("url") or page_url,
                            "description": item.get("description", f"Verified product item on {page_url}."),
                            "source_url": page_url
                        })

        # 3. Extract Products & Prices from HTML cards on Product / Collection pages
        price_regex = re.compile(r"(?:₹|Rs\.?|INR|\$)\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
        for page in pages:
            page_url = page.get("url", "")
            page_type = page.get("page_type", "")
            main_text = page.get("main_text", "")

            # Look for price patterns in text
            for p_match in price_regex.finditer(main_text):
                clean_num = p_match.group(1).replace(",", "")
                try:
                    num_val = float(clean_num)
                    if 100 <= num_val <= 200000:  # reasonable e-commerce price range
                        observed_prices.append(num_val)
                        if "₹" in p_match.group(0) or "rs" in p_match.group(0).lower() or "inr" in p_match.group(0).lower():
                            currencies_found.add("INR")
                        elif "$" in p_match.group(0):
                            currencies_found.add("USD")
                except Exception:
                    pass

            # Headings on product pages or collection grids
            if page_type in ("PRODUCT", "COLLECTION") or "/products/" in page_url or "/collections/" in page_url:
                headings = page.get("h1", []) + page.get("h2", [])
                for h in headings:
                    clean_h = h.strip()
                    if 5 < len(clean_h) < 60 and clean_h.lower() not in seen_product_names:
                        if not any(skip in clean_h.lower() for skip in [
                            "filter", "sort by", "customer reviews", "you may also like", "recently viewed",
                            "subscribe", "newsletter", "follow us", "quick links", "information", "cart",
                            "shopping bag", "checkout", "shipping policy", "refund policy", "terms of service",
                            "catalog", "collections", "our story", "contact us", "faqs", "privacy policy"
                        ]):
                            # Check if it looks like a product title or collection feature
                            seen_product_names.add(clean_h.lower())
                            discovered_products.append({
                                "product_name": clean_h,
                                "category": self._guess_category(clean_h, discovered_categories),
                                "price": "Observed on catalog",
                                "availability": "Active",
                                "product_url": page_url,
                                "description": f"Featured product / catalog item on {page_url}.",
                                "source_url": page_url
                            })
                            if len(discovered_products) >= 20:
                                break

        # 4. Fallback: If no individual products were scraped, treat discovered collections as core catalog offerings
        if not discovered_products and discovered_categories:
            for cat in discovered_categories[:12]:
                discovered_products.append({
                    "product_name": f"{cat['category_name']} Collection",
                    "category": cat["category_name"],
                    "price": "Catalog Available",
                    "availability": "In Stock",
                    "product_url": cat["url"],
                    "description": f"Official product collection line for {cat['category_name']}.",
                    "source_url": cat["source_page"]
                })

        # Calculate price positioning
        currency_code = list(currencies_found)[0] if currencies_found else "INR"
        price_summary = "Pricing available on catalog"
        if observed_prices:
            min_p = min(observed_prices)
            max_p = max(observed_prices)
            if min_p != max_p:
                price_summary = f"Observed prices on sampled pages ranged from {currency_code} {min_p:,.0f} to {currency_code} {max_p:,.0f}."
            else:
                price_summary = f"Observed sample catalog price: {currency_code} {min_p:,.0f}."

        return ProductBundle(
            products=discovered_products,
            categories=discovered_categories,
            price_summary=price_summary,
            currency=currency_code,
            min_p=min(observed_prices) if observed_prices else None,
            max_p=max(observed_prices) if observed_prices else None
        )

    def _guess_category(self, name: str, categories: List[Dict[str, Any]]) -> str:
        name_lower = name.lower()
        for cat in categories:
            if cat["category_name"].lower() in name_lower:
                return cat["category_name"]
        for common in ["Suit Sets", "Anarkali", "Sharara", "Co-ord", "Indo-Western", "Lehenga", "Kurta", "Dress", "Kaftan", "Saree", "Shirt"]:
            if common.lower() in name_lower:
                return common
        return "Core Collection"

class ProductBundle(list):
    def __init__(self, products, categories, price_summary, currency, min_p, max_p):
        super().__init__(products)
        self.products = products
        self.categories = categories
        self.price_range_summary = price_summary
        self.currency = currency
        self.min_observed_price = min_p
        self.max_observed_price = max_p

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "products": return self.products
            if item == "categories": return self.categories
            if item == "price_range_summary": return self.price_range_summary
            if item == "currency": return self.currency
            if item == "product_count": return len(self.products)
            if item == "category_count": return len(self.categories)
            if item == "min_observed_price": return self.min_observed_price
            if item == "max_observed_price": return self.max_observed_price
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

product_extractor = ProductExtractor()
