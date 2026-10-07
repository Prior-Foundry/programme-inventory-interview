from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Path as ApiPath, status
from fastapi.middleware.cors import CORSMiddleware

from .documents import page_text, run_scan, start_scan
from .models import (
    AssistantAnswer, AssistantRequest, EvidenceReference, ProgramCreate,
    ProgramRecord, ProgramSetup, ProgramSetupInput, ProgramUpdate,
)
from .repository import JsonRepository


ROOT = Path(__file__).resolve().parents[2]


def now() -> datetime:
    return datetime.now(timezone.utc)


def create_app(
    *, data_dir: Path | None = None, corpus_dir: Path | None = None, fixture_dir: Path | None = None,
) -> FastAPI:
    data_dir = data_dir or ROOT / "data"
    corpus_dir = corpus_dir or ROOT / "corpus"
    fixture_dir = fixture_dir or ROOT / "fixtures" / "mini-corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    repository = JsonRepository(data_dir)

    application = FastAPI(title="Programme Inventory Interview API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @application.get("/api/health")
    def health():
        return {"status": "ok"}

    @application.get("/api/documents")
    def list_documents():
        return repository.read("documents", [])

    @application.post("/api/documents/scan", status_code=status.HTTP_202_ACCEPTED)
    def scan_documents(background_tasks: BackgroundTasks):
        job = start_scan(repository, corpus_dir, fixture_dir)
        background_tasks.add_task(run_scan, job.id, repository, corpus_dir, fixture_dir)
        return job

    @application.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = next((job for job in repository.read("jobs", []) if job["id"] == job_id), None)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @application.get("/api/documents/{document_id}/pages/{page_number}")
    def get_page(document_id: str, page_number: int = ApiPath(ge=1)):
        record = next((item for item in repository.read("documents", []) if item["id"] == document_id), None)
        if record is None:
            raise HTTPException(status_code=404, detail="Document not found")
        try:
            return {"document_id": document_id, "page_number": page_number, "text": page_text(record, page_number, corpus_dir, fixture_dir)}
        except IndexError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Page text is unavailable: {exc}") from exc

    @application.get("/api/program-setup", response_model=ProgramSetup)
    def get_program_setup():
        return repository.read("program_setup", ProgramSetup(version=0).model_dump(mode="json"))

    @application.put("/api/program-setup", response_model=ProgramSetup)
    def update_program_setup(payload: ProgramSetupInput):
        previous = ProgramSetup.model_validate(repository.read("program_setup", ProgramSetup(version=0).model_dump(mode="json")))
        updated = ProgramSetup(version=previous.version + 1, **payload.model_dump())
        repository.write("program_setup", updated.model_dump(mode="json"))
        return updated

    @application.get("/api/programs", response_model=list[ProgramRecord])
    def list_programs():
        return repository.read("program_inventory", [])

    @application.post("/api/programs", response_model=ProgramRecord, status_code=status.HTTP_201_CREATED)
    def create_program(payload: ProgramCreate):
        if payload.status == "reviewed":
            raise HTTPException(status_code=422, detail="Create a draft, add confirmed evidence, then mark it reviewed")
        setup = ProgramSetup.model_validate(repository.read("program_setup", ProgramSetup(version=0).model_dump(mode="json")))
        _validate_field_values(payload.field_values, setup)
        record = ProgramRecord(
            id=str(uuid4()), setup_version=setup.version, created_at=now(), updated_at=now(), **payload.model_dump(),
        )
        inventory = repository.read("program_inventory", [])
        inventory.append(record.model_dump(mode="json"))
        repository.write("program_inventory", inventory)
        return record

    @application.patch("/api/programs/{program_id}", response_model=ProgramRecord)
    def update_program(program_id: str, payload: ProgramUpdate):
        inventory = repository.read("program_inventory", [])
        index = next((index for index, item in enumerate(inventory) if item["id"] == program_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        existing = ProgramRecord.model_validate(inventory[index])
        changes = payload.model_dump(exclude_unset=True)
        if "field_values" in changes:
            setup = ProgramSetup.model_validate(repository.read("program_setup", ProgramSetup(version=0).model_dump(mode="json")))
            _validate_field_values(changes["field_values"], setup)
        candidate = existing.model_copy(update={**changes, "updated_at": now()})
        if candidate.status == "reviewed" and not any(item.reviewer_confirmed for item in candidate.evidence):
            raise HTTPException(status_code=422, detail="A reviewed programme needs at least one confirmed evidence reference")
        inventory[index] = candidate.model_dump(mode="json")
        repository.write("program_inventory", inventory)
        return candidate

    @application.post("/api/programs/{program_id}/evidence", response_model=ProgramRecord)
    def add_evidence(program_id: str, evidence: EvidenceReference):
        inventory = repository.read("program_inventory", [])
        index = next((index for index, item in enumerate(inventory) if item["id"] == program_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        document = next((item for item in repository.read("documents", []) if item["id"] == evidence.document_id), None)
        if document is None:
            raise HTTPException(status_code=422, detail="Evidence document is not in the corpus")
        try:
            text = page_text(document, evidence.page_number, corpus_dir, fixture_dir)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Evidence page cannot be verified: {exc}") from exc
        if evidence.quote_nl not in text:
            raise HTTPException(status_code=422, detail="Evidence quote was not found on the cited page")
        record = ProgramRecord.model_validate(inventory[index])
        updated = record.model_copy(update={"evidence": [*record.evidence, evidence], "updated_at": now()})
        inventory[index] = updated.model_dump(mode="json")
        repository.write("program_inventory", inventory)
        return updated

    @application.post("/api/assistant/answer", response_model=AssistantAnswer)
    def fake_assistant(payload: AssistantRequest):
        return AssistantAnswer(
            provider="fake",
            answer=("The built-in assistant is deterministic and does not make inventory claims. "
                    "Use it as a provider boundary, then implement a real server-side provider if appropriate. "
                    f"Question received: {payload.question}"),
        )

    return application


def _validate_field_values(values: dict, setup: ProgramSetup) -> None:
    configured = {field.key: field for field in setup.fields}
    unknown = set(values) - set(configured)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown configured field(s): {', '.join(sorted(unknown))}")
    missing = [field.key for field in configured.values() if field.required and not values.get(field.key)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required field(s): {', '.join(missing)}")


app = create_app()
