"""Academic discovery client (OpenAlex search + DOI lookup).

Follows PRD §6.4:
- Searches by keyword, title, author, year range, DOI, publication type, and open-access status.
- Distinguishes metadata access from open-access full-text links.
- Never fabricates unavailable metadata fields.
"""

import re
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.modules.discovery.schemas import AuthorItem, DiscoveredWork, DiscoverySearchResponse

OPENALEX_BASE = "https://api.openalex.org"
DOI_REGEX = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)


def extract_doi(raw: str) -> str | None:
    """Return a normalized lowercase DOI if `raw` contains one."""
    match = DOI_REGEX.search(raw.strip())
    return match.group(1).rstrip(".").lower() if match else None


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct plain text from OpenAlex's `abstract_inverted_index`."""
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        if isinstance(idxs, list):
            for idx in idxs:
                if isinstance(idx, int):
                    positions[idx] = word
    if not positions:
        return None
    max_pos = max(positions)
    if max_pos > 10_000:
        return None
    words = [positions[i] for i in sorted(positions)]
    return " ".join(words).strip() or None


def _split_name(full_name: str) -> AuthorItem:
    cleaned = " ".join(full_name.split())
    parts = cleaned.rsplit(" ", 1)
    if len(parts) == 2:
        return AuthorItem(name=cleaned, given=parts[0], family=parts[1])
    return AuthorItem(name=cleaned, given=None, family=cleaned)


def normalize_pdf_url(url: str | None) -> str | None:
    """Convert known open-access landing URLs (e.g. arXiv abs, PMC) into direct PDF URLs."""
    if not url or not url.strip():
        return None
    u = url.strip()
    arxiv_match = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+(?:v\d+)?)", u, re.IGNORECASE)
    if arxiv_match:
        return f"https://arxiv.org/pdf/{arxiv_match.group(1)}.pdf"
    pmc_match = re.search(r"ncbi\.nlm\.nih\.gov/pmc/articles/(PMC\d+)/?$", u, re.IGNORECASE)
    if pmc_match:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_match.group(1)}/pdf/"
    return u


def _resolve_oa_pdf_url(item: dict) -> str | None:
    best_oa = item.get("best_oa_location") or {}
    primary = item.get("primary_location") or {}
    oa = item.get("open_access") or {}
    locations = item.get("locations") or []

    # 1. Prefer explicit pdf_url from best_oa, primary, or any repository location
    candidates: list[str] = []
    for loc in (best_oa, primary, *locations):
        if isinstance(loc, dict):
            pdf = loc.get("pdf_url")
            if pdf and isinstance(pdf, str) and pdf.strip():
                candidates.append(pdf.strip())

    # 2. Fall back to oa_url or open-access landing_page_url (converting arXiv/PMC where possible)
    if oa.get("oa_url"):
        candidates.append(str(oa["oa_url"]).strip())
    for loc in (best_oa, *locations):
        if isinstance(loc, dict) and loc.get("is_oa") and loc.get("landing_page_url"):
            candidates.append(str(loc["landing_page_url"]).strip())

    for c in candidates:
        norm = normalize_pdf_url(c)
        if norm:
            return norm
    return None


def normalize_openalex_work(item: dict) -> DiscoveredWork | None:
    """Convert an OpenAlex work JSON object into a `DiscoveredWork`."""
    title = (item.get("display_name") or item.get("title") or "").strip()
    raw_id = item.get("id") or ""
    if not title or not raw_id:
        return None

    external_id = raw_id.rsplit("/", 1)[-1]
    raw_doi = item.get("doi") or ""
    doi = extract_doi(raw_doi) if raw_doi else None

    authors: list[AuthorItem] = []
    for auth in item.get("authorships") or []:
        author_obj = auth.get("author") or {}
        display = (author_obj.get("display_name") or "").strip()
        if display:
            authors.append(_split_name(display))

    primary = item.get("primary_location") or {}
    source_obj = primary.get("source") or {}
    venue = (source_obj.get("display_name") or "").strip() or None
    publisher = (
        source_obj.get("host_organization_name") or primary.get("raw_source_name") or ""
    ).strip() or None

    biblio = item.get("biblio") or {}
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")
    if first_page and last_page and first_page != last_page:
        pages: str | None = f"{first_page}-{last_page}"
    else:
        pages = first_page or last_page or None

    oa = item.get("open_access") or {}
    oa_pdf_url = _resolve_oa_pdf_url(item)
    is_oa = bool(oa.get("is_oa")) or bool(oa_pdf_url)
    source_url = (
        primary.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else None) or raw_id
    )

    keywords: list[str] = []
    for kw in (item.get("keywords") or [])[:10]:
        kw_name = (kw.get("display_name") or "").strip()
        if kw_name and kw_name not in keywords:
            keywords.append(kw_name)

    return DiscoveredWork(
        provider="openalex",
        external_id=external_id,
        doi=doi,
        title=title,
        authors=authors,
        abstract=reconstruct_abstract(item.get("abstract_inverted_index")),
        publication_year=item.get("publication_year"),
        venue=venue,
        publisher=publisher,
        publication_type=item.get("type") or "article",
        volume=biblio.get("volume"),
        issue=biblio.get("issue"),
        pages=pages,
        source_url=source_url,
        oa_pdf_url=oa_pdf_url if is_oa else None,
        is_open_access=is_oa,
        citation_count=item.get("cited_by_count"),
        keywords=keywords,
    )


def _headers() -> dict[str, str]:
    mailto = get_settings().openalex_mailto
    ua = f"Moyee/0.1 (mailto:{mailto})" if mailto else "Moyee/0.1"
    return {"User-Agent": ua, "Accept": "application/json"}


def search_works(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    publication_type: str | None = None,
    page: int = 1,
    per_page: int = 15,
    http_client: httpx.Client | None = None,
) -> DiscoverySearchResponse:
    """Search OpenAlex works or resolve a direct DOI query."""
    cleaned = query.strip()
    maybe_doi = extract_doi(cleaned)
    if maybe_doi and ("doi.org" in cleaned.lower() or cleaned.lower().startswith("10.")):
        work = lookup_by_doi(maybe_doi, http_client=http_client)
        results = [work] if work else []
        return DiscoverySearchResponse(
            query=cleaned, total=len(results), page=1, per_page=per_page, results=results
        )

    filters: list[str] = []
    if year_from is not None and year_to is not None:
        filters.append(f"publication_year:{year_from}-{year_to}")
    elif year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    elif year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if open_access_only:
        filters.append("is_oa:true")
    if publication_type:
        filters.append(f"type:{publication_type}")

    params: dict[str, str | int] = {
        "search": cleaned,
        "page": page,
        "per-page": per_page,
    }
    if filters:
        params["filter"] = ",".join(filters)
    if get_settings().openalex_mailto:
        params["mailto"] = get_settings().openalex_mailto

    close_client = http_client is None
    client = http_client or httpx.Client(timeout=12.0, headers=_headers())
    try:
        resp = client.get(f"{OPENALEX_BASE}/works", params=params)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Academic search provider is temporarily unavailable.",
        ) from exc
    finally:
        if close_client:
            client.close()

    results: list[DiscoveredWork] = []
    for raw in payload.get("results") or []:
        norm = normalize_openalex_work(raw)
        if norm is not None:
            results.append(norm)

    total = (payload.get("meta") or {}).get("count", len(results))
    return DiscoverySearchResponse(
        query=cleaned, total=total, page=page, per_page=per_page, results=results
    )


def lookup_by_doi(doi: str, *, http_client: httpx.Client | None = None) -> DiscoveredWork | None:
    norm_doi = extract_doi(doi)
    if not norm_doi:
        return None
    encoded = quote(f"https://doi.org/{norm_doi}", safe="")
    close_client = http_client is None
    client = http_client or httpx.Client(timeout=10.0, headers=_headers())
    try:
        resp = client.get(f"{OPENALEX_BASE}/works/{encoded}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return normalize_openalex_work(resp.json())
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Academic DOI lookup failed.",
        ) from exc
    finally:
        if close_client:
            client.close()
