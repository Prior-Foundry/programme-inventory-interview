from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from .models import DocumentRecord, ScanJob
from .repository import JsonRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def select_corpus(corpus_dir: Path, fixture_dir: Path) -> Path:
    return corpus_dir if any(corpus_dir.glob("*.pdf")) else fixture_dir


def start_scan(repository: JsonRepository, corpus_dir: Path, fixture_dir: Path) -> ScanJob:
    job = ScanJob(id=str(uuid4()), status="queued", created_at=utc_now())
    jobs = repository.read("jobs", [])
    jobs.append(job.model_dump(mode="json"))
    repository.write("jobs", jobs)
    return job


def run_scan(job_id: str, repository: JsonRepository, corpus_dir: Path, fixture_dir: Path) -> None:
    jobs = repository.read("jobs", [])
    job = next((item for item in jobs if item["id"] == job_id), None)
    if job is None:
        return
    selected = select_corpus(corpus_dir, fixture_dir)
    pdfs = sorted(selected.glob("*.pdf"))
    job.update(status="running", total_files=len(pdfs), processed_files=0)
    repository.write("jobs", jobs)
    current = {item["sha256"]: item for item in repository.read("documents", [])}
    records: list[dict] = []
    try:
        for source in pdfs:
            digest = _hash(source)
            old = current.get(digest)
            record = _inspect(source, digest, old)
            records.append(record.model_dump(mode="json"))
            job["processed_files"] += 1
            processed_hashes = {item["sha256"] for item in records}
            repository.write(
                "documents",
                records + [value for key, value in current.items() if key not in processed_hashes],
            )
            repository.write("jobs", jobs)
        job.update(status="completed", completed_at=utc_now().isoformat())
        repository.write("documents", records)
        repository.write("jobs", jobs)
    except Exception as exc:
        job.update(status="failed", error=str(exc), completed_at=utc_now().isoformat())
        repository.write("jobs", jobs)


def page_text(record: dict, page_number: int, corpus_dir: Path, fixture_dir: Path) -> str:
    selected = select_corpus(corpus_dir, fixture_dir)
    source = selected / record["filename"]
    if not source.is_file() or source.resolve().parent != selected.resolve():
        raise FileNotFoundError("Source document is unavailable")
    reader = PdfReader(source)
    if page_number > len(reader.pages):
        raise IndexError("Page does not exist")
    return reader.pages[page_number - 1].extract_text() or ""


def _inspect(source: Path, digest: str, old: dict | None) -> DocumentRecord:
    if old and old.get("size_bytes") == source.stat().st_size:
        return DocumentRecord.model_validate(old)
    try:
        reader = PdfReader(source)
        sample = "".join((page.extract_text() or "") for page in reader.pages[: min(3, len(reader.pages))])
        status = "extracted" if len(sample.strip()) >= 100 else "needs_ocr"
        return DocumentRecord(
            id=f"doc-{digest[:16]}", filename=source.name, sha256=digest,
            size_bytes=source.stat().st_size, page_count=len(reader.pages),
            extraction_status=status, extracted_characters=len(sample.strip()), scanned_at=utc_now(),
        )
    except Exception as exc:
        return DocumentRecord(
            id=f"doc-{digest[:16]}", filename=source.name, sha256=digest,
            size_bytes=source.stat().st_size, extraction_status="failed", error=str(exc), scanned_at=utc_now(),
        )


def _hash(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
