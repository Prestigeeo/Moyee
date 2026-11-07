"""Academic discovery client (OpenAlex search + DOI lookup).

Follows PRD §6.4:
- Searches by keyword, title, author, year range, DOI, publication type, and open-access status.
- Distinguishes metadata access from open-access full-text links.
- Never fabricates unavailable metadata fields.
"""

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.modules.discovery.schemas import AuthorItem, DiscoveredWork, DiscoverySearchResponse

OPENALEX_BASE = "https://api.openalex.org"
CROSSREF_BASE = "https://api.crossref.org"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
ARXIV_BASE = "https://export.arxiv.org/api/query"
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
    cleaned = " ".join(full_name.split())[:200]
    parts = cleaned.rsplit(" ", 1)
    if len(parts) == 2:
        return AuthorItem(name=cleaned, given=parts[0][:120], family=parts[1][:120])
    return AuthorItem(name=cleaned, given=None, family=cleaned[:120])


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


def _search_crossref(
    query: str,
    *,
    year_from: int | None,
    year_to: int | None,
    per_page: int,
    page: int,
    client: httpx.Client,
) -> tuple[list[DiscoveredWork], int]:
    params: dict[str, str | int] = {
        "query": query,
        "rows": min(per_page, 50),
        "offset": (page - 1) * per_page,
    }
    filters: list[str] = []
    if year_from is not None:
        filters.append(f"from-pub-date:{year_from}")
    if year_to is not None:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)
    try:
        resp = client.get(f"{CROSSREF_BASE}/works", params=params)
        resp.raise_for_status()
        msg = (resp.json() or {}).get("message") or {}
    except Exception:
        return [], 0

    out: list[DiscoveredWork] = []
    for item in msg.get("items") or []:
        try:
            titles = item.get("title") or []
            title = (titles[0] if titles else "").strip()
            doi = extract_doi(item.get("DOI") or "")
            if not title or not doi:
                continue
            authors: list[AuthorItem] = []
            for a in (item.get("author") or [])[:25]:
                given = (a.get("given") or "").strip()[:120]
                family = (a.get("family") or "").strip()[:120]
                full = (f"{given} {family}".strip() or (a.get("name") or "").strip())[:200]
                if full:
                    authors.append(
                        AuthorItem(name=full, given=given or None, family=family or None)
                    )
            pub_year = None
            for date_key in ("published-print", "published-online", "issued"):
                date_parts = (item.get(date_key) or {}).get("date-parts") or []
                parts = date_parts[0] if date_parts and isinstance(date_parts[0], list) else []
                if parts and isinstance(parts[0], int):
                    pub_year = parts[0]
                    break
            containers = item.get("container-title") or []
            venue = (containers[0] if containers else "").strip() or None
            raw_abs = item.get("abstract") or ""
            clean_abs = re.sub(r"<[^>]+>", " ", str(raw_abs)).strip() if raw_abs else None
            pdf_url = None
            for link in item.get("link") or []:
                if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower():
                    pdf_url = str(link.get("URL") or "").strip() or None
                    break
            ref_cnt = item.get("is-referenced-by-count")
            out.append(
                DiscoveredWork(
                    provider="crossref",
                    external_id=f"cr:{doi}",
                    doi=doi,
                    title=title,
                    authors=authors,
                    abstract=clean_abs,
                    publication_year=pub_year,
                    venue=venue,
                    publisher=str(item.get("publisher") or "").strip() or None,
                    publication_type=str(item.get("type") or "article"),
                    volume=str(item.get("volume") or "").strip() or None,
                    issue=str(item.get("issue") or "").strip() or None,
                    pages=str(item.get("page") or "").strip() or None,
                    source_url=str(item.get("URL") or f"https://doi.org/{doi}"),
                    oa_pdf_url=pdf_url,
                    is_open_access=bool(pdf_url),
                    citation_count=int(ref_cnt) if isinstance(ref_cnt, int) else None,
                    keywords=[],
                )
            )
        except Exception:
            continue
    return out, int(msg.get("total-results") or len(out))


def _search_semantic_scholar(
    query: str,
    *,
    year_from: int | None,
    year_to: int | None,
    open_access_only: bool,
    per_page: int,
    page: int,
    client: httpx.Client,
) -> tuple[list[DiscoveredWork], int]:
    params: dict[str, str | int] = {
        "query": query,
        "limit": min(per_page, 50),
        "offset": (page - 1) * per_page,
        "fields": (
            "title,authors,year,abstract,venue,externalIds,"
            "isOpenAccess,openAccessPdf,citationCount,url"
        ),
    }
    if year_from and year_to:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from:
        params["year"] = f"{year_from}-"
    elif year_to:
        params["year"] = f"-{year_to}"
    if open_access_only:
        params["openAccessPdf"] = ""

    try:
        resp = client.get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params=params)
        resp.raise_for_status()
        body = resp.json() or {}
    except Exception:
        return [], 0

    out: list[DiscoveredWork] = []
    for item in body.get("data") or []:
        try:
            title = (item.get("title") or "").strip()
            pid = item.get("paperId") or ""
            if not title or not pid:
                continue
            ext_ids = item.get("externalIds") or {}
            doi = extract_doi(str(ext_ids.get("DOI") or "")) if ext_ids.get("DOI") else None
            arxiv_id = ext_ids.get("ArXiv")
            oa_pdf = str((item.get("openAccessPdf") or {}).get("url") or "").strip() or None
            if not oa_pdf and arxiv_id:
                oa_pdf = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            is_oa = bool(item.get("isOpenAccess")) or bool(oa_pdf)
            authors = [
                _split_name(str(a.get("name") or ""))
                for a in (item.get("authors") or [])[:25]
                if str(a.get("name") or "").strip()
            ]
            yr = item.get("year")
            cit = item.get("citationCount")
            out.append(
                DiscoveredWork(
                    provider="semantic_scholar",
                    external_id=f"s2:{pid}",
                    doi=doi,
                    title=title,
                    authors=authors,
                    abstract=str(item.get("abstract") or "").strip() or None,
                    publication_year=int(yr) if isinstance(yr, int) else None,
                    venue=str(item.get("venue") or "").strip() or None,
                    publisher=None,
                    publication_type="article",
                    volume=None,
                    issue=None,
                    pages=None,
                    source_url=str(
                        item.get("url") or (f"https://doi.org/{doi}" if doi else "")
                    ).strip()
                    or None,
                    oa_pdf_url=oa_pdf,
                    is_open_access=is_oa,
                    citation_count=int(cit) if isinstance(cit, int) else None,
                    keywords=[],
                )
            )
        except Exception:
            continue
    return out, int(body.get("total") or len(out))


def _search_arxiv(
    query: str,
    *,
    per_page: int,
    page: int,
    client: httpx.Client,
) -> tuple[list[DiscoveredWork], int]:
    params: dict[str, str | int] = {
        "search_query": f"all:{query}",
        "start": (page - 1) * per_page,
        "max_results": min(per_page, 50),
    }
    try:
        resp = client.get(ARXIV_BASE, params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception:
        return [], 0

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out: list[DiscoveredWork] = []
    for entry in root.findall("atom:entry", ns):
        raw_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        title = re.sub(
            r"\s+", " ", (entry.findtext("atom:title", default="", namespaces=ns) or "")
        ).strip()
        summary = re.sub(
            r"\s+", " ", (entry.findtext("atom:summary", default="", namespaces=ns) or "")
        ).strip()
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:4]
        if not raw_id or not title:
            continue
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        authors = [
            _split_name(a.findtext("atom:name", default="", namespaces=ns))
            for a in entry.findall("atom:author", ns)
            if (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
        ]
        out.append(
            DiscoveredWork(
                provider="arxiv",
                external_id=f"arxiv:{arxiv_id}",
                doi=None,
                title=title,
                authors=authors,
                abstract=summary or None,
                publication_year=int(published) if published.isdigit() else None,
                venue="arXiv Preprint",
                publisher="arXiv",
                publication_type="preprint",
                volume=None,
                issue=None,
                pages=None,
                source_url=raw_id,
                oa_pdf_url=pdf_url,
                is_open_access=True,
                citation_count=None,
                keywords=[],
            )
        )
    return out, len(out)


def search_works(
    query: str,
    *,
    provider: str = "openalex",
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    publication_type: str | None = None,
    page: int = 1,
    per_page: int = 15,
    http_client: httpx.Client | None = None,
) -> DiscoverySearchResponse:
    """Search OpenAlex, Semantic Scholar, Crossref, arXiv, or federated 'all'."""
    cleaned = query.strip()
    maybe_doi = extract_doi(cleaned)
    if maybe_doi and ("doi.org" in cleaned.lower() or cleaned.lower().startswith("10.")):
        work = lookup_by_doi(maybe_doi, http_client=http_client)
        results = [work] if work else []
        return DiscoverySearchResponse(
            query=cleaned, total=len(results), page=1, per_page=per_page, results=results
        )

    close_client = http_client is None
    client = http_client or httpx.Client(timeout=12.0, headers=_headers())
    try:
        if provider == "crossref":
            res, total = _search_crossref(
                cleaned,
                year_from=year_from,
                year_to=year_to,
                per_page=per_page,
                page=page,
                client=client,
            )
            if open_access_only:
                res = [w for w in res if w.is_open_access]
            return DiscoverySearchResponse(
                query=cleaned, total=total, page=page, per_page=per_page, results=res
            )

        if provider == "semantic_scholar":
            res, total = _search_semantic_scholar(
                cleaned,
                year_from=year_from,
                year_to=year_to,
                open_access_only=open_access_only,
                per_page=per_page,
                page=page,
                client=client,
            )
            return DiscoverySearchResponse(
                query=cleaned, total=total, page=page, per_page=per_page, results=res
            )

        if provider == "arxiv":
            res, total = _search_arxiv(cleaned, per_page=per_page, page=page, client=client)
            return DiscoverySearchResponse(
                query=cleaned, total=total, page=page, per_page=per_page, results=res
            )

        # OpenAlex (primary for 'openalex' and 'all')
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

        resp = client.get(f"{OPENALEX_BASE}/works", params=params)
        resp.raise_for_status()
        payload = resp.json()

        results: list[DiscoveredWork] = []
        seen_keys: set[str] = set()
        for raw in payload.get("results") or []:
            try:
                norm = normalize_openalex_work(raw)
            except Exception:
                norm = None
            if norm is not None:
                key = (norm.doi or norm.title).lower()
                seen_keys.add(key)
                results.append(norm)

        total = int((payload.get("meta") or {}).get("count", len(results)))

        if provider == "all" and http_client is None:
            with httpx.Client(timeout=3.5, headers=_headers()) as fast_client:
                s2_res, s2_total = _search_semantic_scholar(
                    cleaned,
                    year_from=year_from,
                    year_to=year_to,
                    open_access_only=open_access_only,
                    per_page=max(10, per_page // 2),
                    page=page,
                    client=fast_client,
                )
                for w in s2_res:
                    key = (w.doi or w.title).lower()
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(w)
                cr_res, cr_total = _search_crossref(
                    cleaned,
                    year_from=year_from,
                    year_to=year_to,
                    per_page=max(8, per_page // 3),
                    page=page,
                    client=fast_client,
                )
                for w in cr_res:
                    if open_access_only and not w.is_open_access:
                        continue
                    key = (w.doi or w.title).lower()
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(w)
                total = total + s2_total + cr_total

        return DiscoverySearchResponse(
            query=cleaned, total=total, page=page, per_page=per_page, results=results
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Academic search provider is temporarily unavailable.",
        ) from exc
    finally:
        if close_client:
            client.close()


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
