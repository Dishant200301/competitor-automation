from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.validation.engine import validate, validated_projection
from app.core.config import settings
from app.reports.docx_builder import generate_docx_report

ROOT = Path(__file__).resolve().parents[2]


def safe_url(url: str) -> str:
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    return f"https://{url}"


def load_report(db, run_id):
    dataset = db.get_dataset(run_id)
    if not dataset or not dataset.get("validation", {}).get("passed"):
        raise ValueError("Report requires a persisted, validated dataset")
    audit = validate(dataset)
    if not audit["passed"]: raise ValueError("Stored dataset failed revalidation: " + "; ".join(audit["failures"]))
    return validated_projection(dataset)


def generate_report(db, run_id, output):
    data = load_report(db, run_id)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["display"] = lambda value: "Not found" if value is None or value == "" else (", ".join(map(str,value)) if isinstance(value,list) else value)
    source_numbers = {s["url"]:i+1 for i,s in enumerate(data["sources"])}
    evidence_sources = {e['id']: e['source_url'] for e in data.get('evidence', [])}
    def cite(item):
        if not item or not isinstance(item, dict): return ""
        nums = []
        for eid in item.get("evidence_ids", []):
            url = evidence_sources.get(eid)
            if url and url in source_numbers:
                nums.append(str(source_numbers[url]))
        return f"[{', '.join(nums)}]" if nums else ""

    css_text = (ROOT / "static" / "report.css").read_text(encoding="utf-8") if (ROOT / "static" / "report.css").is_file() else ""
    html = env.get_template("report.html").render(
        d=data,
        sources=source_numbers,
        run_id=run_id,
        css=css_text,
        cite=cite,
        safe_url=safe_url,
        evidence_sources=evidence_sources
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".html").write_text(html, encoding="utf-8")

    # Also generate the .docx document file
    try:
        generate_docx_report(db, run_id, output.with_suffix(".docx"))
    except Exception as docx_err:
        pass

    if os.name == "nt" and not os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        portable = ROOT / ".runtime" / "weasyprint" / "onedir" / "weasyprint" / "_internal"
        dlls = settings.WEASYPRINT_DLL_DIRECTORIES or (str(portable) if portable.is_dir() else "")
        if dlls: os.environ["WEASYPRINT_DLL_DIRECTORIES"] = dlls
    from weasyprint import HTML, CSS
    def deny_fetch(url, *args, **kwargs):
        raise ValueError("Report rendering cannot fetch external resources")
    HTML(string=html, url_fetcher=deny_fetch).write_pdf(str(output), stylesheets=[CSS(filename=str(ROOT / "static" / "report.css"))])

    # Post-process PDF to add /NewWindow true to all URI link annotations so links open in new tab/window
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import BooleanObject, NameObject
        reader = PdfReader(str(output))
        writer = PdfWriter()
        writer.append(reader)
        for page in writer.pages:
            if '/Annots' in page:
                for annot in page['/Annots']:
                    obj = annot.get_object()
                    if '/A' in obj:
                        action = obj['/A'].get_object()
                        if action.get('/S') == '/URI':
                            action[NameObject('/NewWindow')] = BooleanObject(True)
        with open(str(output), "wb") as f:
            writer.write(f)
    except Exception:
        pass

    return str(output)
