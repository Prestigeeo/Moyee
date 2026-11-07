"""Deterministic citation formatting (APA 7, Harvard, IEEE) & BibTeX export."""

import re

from app.modules.library.models import ProjectSource
from app.modules.users.models import CitationStyle


def _family_and_initials(author: dict) -> tuple[str, str]:
    name = (author.get("name") or "").strip()
    family = (author.get("family") or "").strip()
    given = (author.get("given") or "").strip()
    if not family and name:
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            given, family = parts[0], parts[1]
        else:
            family = name
    initials = " ".join(f"{p[0]}." for p in given.split() if p)
    return family or "Unknown", initials


def missing_fields(source: ProjectSource) -> list[str]:
    """Identify incomplete reference metadata (PRD §6.12)."""
    missing: list[str] = []
    if not source.authors:
        missing.append("authors")
    if not source.publication_year:
        missing.append("publication_year")
    if not source.venue and not source.publisher:
        missing.append("venue_or_publisher")
    if not source.doi and not source.source_url:
        missing.append("doi_or_url")
    return missing


def format_inline_citation(source: ProjectSource, style: CitationStyle, index: int = 1) -> str:
    if style == CitationStyle.ieee:
        return f"[{index}]"

    year = str(source.publication_year) if source.publication_year else "n.d."
    authors = source.authors or []
    if not authors:
        short_title = (source.title or "Untitled")[:30].rstrip()
        return f"({short_title}, {year})"

    first_family, _ = _family_and_initials(authors[0])
    if len(authors) == 1:
        return f"({first_family}, {year})"
    if len(authors) == 2:
        second_family, _ = _family_and_initials(authors[1])
        sep = " & " if style == CitationStyle.apa7 else " and "
        return f"({first_family}{sep}{second_family}, {year})"
    return f"({first_family} et al., {year})"


def format_bibliography_entry(source: ProjectSource, style: CitationStyle, index: int = 1) -> str:
    year = str(source.publication_year) if source.publication_year else "n.d."
    title = (source.title or "Untitled").rstrip(".")
    venue = (source.venue or source.publisher or "").strip()
    vol_issue = ""
    if source.volume and source.issue:
        vol_issue = f"{source.volume}({source.issue})"
    elif source.volume:
        vol_issue = source.volume
    pages = source.pages or ""
    doi_part = f"https://doi.org/{source.doi}" if source.doi else (source.source_url or "")

    authors = source.authors or []
    if style == CitationStyle.ieee:
        if authors:
            formatted_authors = []
            for a in authors[:6]:
                fam, ini = _family_and_initials(a)
                formatted_authors.append(f"{ini} {fam}".strip())
            if len(authors) > 6:
                formatted_authors.append("et al.")
            author_str = ", ".join(formatted_authors)
        else:
            author_str = "Unknown Author"

        parts = [f"[{index}] {author_str},", f'"{title},"']
        if venue:
            parts.append(venue + ",")
        if source.volume:
            parts.append(f"vol. {source.volume},")
        if source.issue:
            parts.append(f"no. {source.issue},")
        if pages:
            parts.append(f"pp. {pages},")
        parts.append(f"{year}.")
        if source.doi:
            parts.append(f"doi: {source.doi}.")
        return " ".join(parts)

    # APA 7 and Harvard
    if authors:
        formatted_authors = []
        for a in authors[:20]:
            fam, ini = _family_and_initials(a)
            formatted_authors.append(f"{fam}, {ini}".rstrip(", "))
        if len(formatted_authors) == 1:
            author_str = formatted_authors[0]
        elif style == CitationStyle.apa7:
            author_str = ", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1]
        else:
            author_str = ", ".join(formatted_authors[:-1]) + " and " + formatted_authors[-1]
    else:
        author_str = "Unknown Author"

    if not author_str.endswith("."):
        author_str += "."

    venue_segment = ""
    if venue:
        details = [venue]
        if vol_issue:
            details.append(vol_issue)
        if pages:
            details.append(f"pp. {pages}" if style == CitationStyle.harvard else pages)
        venue_segment = ", ".join(details) + "."

    segments = [f"{author_str} ({year}).", f"{title}."]
    if venue_segment:
        segments.append(venue_segment)
    if doi_part:
        segments.append(doi_part)
    return " ".join(segments)


def make_citation_key(authors: list[dict], year: int | None, title: str) -> str:
    family = "source"
    if authors:
        fam, _ = _family_and_initials(authors[0])
        family = re.sub(r"[^a-z0-9]", "", fam.lower()) or "source"
    yr = str(year) if year else "nd"
    first_word = re.sub(r"[^a-z0-9]", "", (title.split() or ["work"])[0].lower()) or "work"
    return f"{family}{yr}{first_word}"[:60]


def to_bibtex(sources: list[ProjectSource]) -> str:
    entries: list[str] = []
    used_keys: set[str] = set()
    for src in sources:
        base_key = src.citation_key or make_citation_key(
            src.authors, src.publication_year, src.title
        )
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}_{suffix}"
            suffix += 1
        used_keys.add(key)

        entry_type = "book" if src.publication_type == "book" else "article"
        author_field = " and ".join(
            f"{_family_and_initials(a)[0]}, {(a.get('given') or '').strip()}".rstrip(", ")
            for a in (src.authors or [])
        )
        fields: list[tuple[str, str | int | None]] = [
            ("title", src.title),
            ("author", author_field or None),
            ("year", src.publication_year),
            ("journal" if entry_type == "article" else "booktitle", src.venue),
            ("publisher", src.publisher),
            ("volume", src.volume),
            ("number", src.issue),
            ("pages", src.pages),
            ("doi", src.doi),
            ("url", src.source_url),
        ]
        body = ",\n".join(
            f"  {k} = {{{str(v).replace('{', '').replace('}', '')}}}"
            for k, v in fields
            if v is not None and str(v).strip() != ""
        )
        entries.append(f"@{entry_type}{{{key},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def to_ris(sources: list[ProjectSource]) -> str:
    """Export project sources in RIS format for Zotero, Mendeley, and EndNote."""
    records: list[str] = []
    for src in sources:
        ty = "BOOK" if src.publication_type == "book" else "JOUR"
        lines = [f"TY  - {ty}", f"TI  - {src.title}"]
        for a in src.authors or []:
            fam, ini = _family_and_initials(a)
            given = (a.get("given") or ini).strip()
            lines.append(f"AU  - {fam}, {given}".rstrip(", "))
        if src.publication_year:
            lines.append(f"PY  - {src.publication_year}")
        if src.venue:
            lines.append(f"JO  - {src.venue}")
        if src.publisher:
            lines.append(f"PB  - {src.publisher}")
        if src.volume:
            lines.append(f"VL  - {src.volume}")
        if src.issue:
            lines.append(f"IS  - {src.issue}")
        if src.pages:
            lines.append(f"SP  - {src.pages}")
        if src.doi:
            lines.append(f"DO  - {src.doi}")
        if src.source_url:
            lines.append(f"UR  - {src.source_url}")
        if src.abstract:
            lines.append(f"AB  - {src.abstract[:1000]}")
        lines.append("ER  - ")
        records.append("\n".join(lines))
    return "\n\n".join(records) + ("\n" if records else "")
