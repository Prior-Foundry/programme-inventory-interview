import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { DocumentRecord, Evidence, Program, ProgramField, ProgramSetup } from "./types";

const emptySetup: ProgramSetup = { version: 0, definition: "", inclusion_rules: [], exclusion_rules: [], taxonomy: [], fields: [], evidence_rules: [] };
const splitLines = (value: string) => value.split("\n").map(item => item.trim()).filter(Boolean);

export default function App() {
  const [tab, setTab] = useState<"documents" | "setup" | "inventory">("documents");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [setup, setSetup] = useState<ProgramSetup>(emptySetup);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextDocuments, nextSetup, nextPrograms] = await Promise.all([api.documents(), api.setup(), api.programs()]);
      setDocuments(nextDocuments); setSetup(nextSetup); setPrograms(nextPrograms);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load the application"); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return <main>
    <header><div><p className="eyebrow">INTERVIEW STARTER</p><h1>Programme inventory</h1><p>Turn policy-document evidence into a reviewable inventory. The definition of a programme is deliberately yours to design.</p></div></header>
    <nav>{(["documents", "setup", "inventory"] as const).map(item => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item === "documents" ? "Document library" : item === "setup" ? "Programme setup" : "Programme inventory"}</button>)}</nav>
    {message && <p className="notice">{message}</p>}
    {tab === "documents" && <DocumentLibrary documents={documents} onDocuments={setDocuments} onMessage={setMessage} />}
    {tab === "setup" && <SetupEditor setup={setup} onSaved={setSetup} onMessage={setMessage} />}
    {tab === "inventory" && <Inventory programs={programs} documents={documents} setup={setup} onPrograms={setPrograms} onMessage={setMessage} />}
  </main>;
}

function DocumentLibrary({ documents, onDocuments, onMessage }: { documents: DocumentRecord[]; onDocuments: (items: DocumentRecord[]) => void; onMessage: (value: string) => void }) {
  const [selected, setSelected] = useState<DocumentRecord | null>(null);
  const [preview, setPreview] = useState("");
  const [scanning, setScanning] = useState(false);
  const scan = async () => {
    try {
      setScanning(true); const job = await api.scan();
      for (let attempt = 0; attempt < 80; attempt += 1) {
        const state = await api.job(job.id);
        if (state.status === "completed" || state.status === "failed") break;
        await new Promise(resolve => window.setTimeout(resolve, 250));
      }
      onDocuments(await api.documents());
    } catch (error) { onMessage(error instanceof Error ? error.message : "Scan failed"); }
    finally { setScanning(false); }
  };
  const showPage = async (document: DocumentRecord) => {
    setSelected(document); setPreview("");
    try { setPreview((await api.page(document.id, 1)).text || "No extractable text on this page. OCR may be needed."); }
    catch (error) { setPreview(error instanceof Error ? error.message : "Preview unavailable"); }
  };
  return <section><div className="section-heading"><div><h2>Document library</h2><p>Scan uses the full bundle in <code>corpus/</code> when present, otherwise the tiny local fixture corpus.</p></div><button onClick={() => void scan()} disabled={scanning}>{scanning ? "Scanning…" : "Scan corpus"}</button></div>
    {!documents.length ? <Empty title="No documents scanned" detail="Start by scanning the corpus. The fixture corpus is enough to build and test a vertical slice." /> : <div className="two-column"><div className="card-list">{documents.map(document => <button className="document-card" key={document.id} onClick={() => void showPage(document)}><strong>{document.filename}</strong><span>{document.page_count ?? "?"} pages · {Math.ceil(document.size_bytes / 1024)} KB</span><Status value={document.extraction_status} /></button>)}</div><article className="preview"><h3>{selected?.filename || "Select a document"}</h3><pre>{preview || "Page-one text will appear here."}</pre></article></div>}</section>;
}

function SetupEditor({ setup, onSaved, onMessage }: { setup: ProgramSetup; onSaved: (setup: ProgramSetup) => void; onMessage: (value: string) => void }) {
  const [draft, setDraft] = useState(setup);
  useEffect(() => setDraft(setup), [setup]);
  const save = async (event: FormEvent) => { event.preventDefault(); try { const { version: _version, ...payload } = draft; onSaved(await api.saveSetup(payload)); onMessage("Programme setup saved."); } catch (error) { onMessage(error instanceof Error ? error.message : "Could not save setup"); } };
  const addField = () => setDraft(current => ({ ...current, fields: [...current.fields, { key: "", label: "", description: "", required: false, value_type: "text", options: [] }] }));
  const changeField = (index: number, patch: Partial<ProgramField>) => setDraft(current => ({ ...current, fields: current.fields.map((field, currentIndex) => currentIndex === index ? { ...field, ...patch } : field) }));
  return <section><div className="section-heading"><div><h2>Programme setup</h2><p>Define a defensible classification before adding inventory records. No taxonomy is supplied.</p></div><span>Version {setup.version}</span></div><form onSubmit={save} className="stack"><label>What counts as a programme?<textarea value={draft.definition} onChange={event => setDraft({ ...draft, definition: event.target.value })} placeholder="State the unit of inventory and the evidence threshold." /></label><RuleBox label="Inclusion rules" value={draft.inclusion_rules} onChange={value => setDraft({ ...draft, inclusion_rules: splitLines(value) })} /><RuleBox label="Exclusion rules" value={draft.exclusion_rules} onChange={value => setDraft({ ...draft, exclusion_rules: splitLines(value) })} /><RuleBox label="Candidate-defined classification / taxonomy" value={draft.taxonomy} onChange={value => setDraft({ ...draft, taxonomy: splitLines(value) })} /><RuleBox label="Evidence rules" value={draft.evidence_rules} onChange={value => setDraft({ ...draft, evidence_rules: splitLines(value) })} /><div><h3>Inventory fields</h3>{draft.fields.map((field, index) => <div className="field-row" key={index}><input aria-label="Field key" placeholder="field_key" value={field.key} onChange={event => changeField(index, { key: event.target.value })} /><input aria-label="Field label" placeholder="English field label" value={field.label} onChange={event => changeField(index, { label: event.target.value })} /><select value={field.value_type} onChange={event => changeField(index, { value_type: event.target.value as ProgramField["value_type"] })}><option value="text">Text</option><option value="date">Date</option><option value="number">Number</option><option value="list">List</option><option value="select">Select</option></select><label className="checkbox"><input type="checkbox" checked={field.required} onChange={event => changeField(index, { required: event.target.checked })} /> Required</label><button type="button" className="quiet" onClick={() => setDraft(current => ({ ...current, fields: current.fields.filter((_, currentIndex) => currentIndex !== index) }))}>Remove</button></div>)}<button type="button" className="secondary" onClick={addField}>Add field</button></div><button type="submit">Save programme setup</button></form></section>;
}

function Inventory({ programs, documents, setup, onPrograms, onMessage }: { programs: Program[]; documents: DocumentRecord[]; setup: ProgramSetup; onPrograms: (items: Program[]) => void; onMessage: (value: string) => void }) {
  const [name, setName] = useState(""); const [classification, setClassification] = useState(""); const [confidence, setConfidence] = useState<Program["confidence"]>("medium"); const [values, setValues] = useState<Record<string, unknown>>({});
  const [evidenceProgram, setEvidenceProgram] = useState(""); const [documentId, setDocumentId] = useState(""); const [page, setPage] = useState(1); const [quote, setQuote] = useState("");
  const create = async (event: FormEvent) => { event.preventDefault(); try { const created = await api.createProgram({ name_en: name, classification: classification || undefined, confidence, field_values: values, status: "draft" }); onPrograms([...programs, created]); setName(""); setClassification(""); setValues({}); onMessage("Draft programme added. Attach and confirm evidence before review."); } catch (error) { onMessage(error instanceof Error ? error.message : "Could not create programme"); } };
  const attachEvidence = async (event: FormEvent) => { event.preventDefault(); try { const evidence: Evidence = { document_id: documentId, page_number: page, quote_nl: quote, reviewer_confirmed: true }; const updated = await api.addEvidence(evidenceProgram, evidence); onPrograms(programs.map(item => item.id === updated.id ? updated : item)); setQuote(""); onMessage("Evidence attached and verified against the PDF page."); } catch (error) { onMessage(error instanceof Error ? error.message : "Could not attach evidence"); } };
  const review = async (record: Program) => { try { const updated = await api.updateProgram(record.id, { status: "reviewed" }); onPrograms(programs.map(item => item.id === updated.id ? updated : item)); } catch (error) { onMessage(error instanceof Error ? error.message : "Review failed"); } };
  const configuredFields = useMemo(() => setup.fields, [setup.fields]);
  return <section><div className="section-heading"><div><h2>Programme inventory</h2><p>Records are English-normalized; every material claim must retain Dutch page-level evidence.</p></div><span>{programs.length} records</span></div><div className="two-column inventory-layout"><form onSubmit={create} className="stack panel"><h3>Create draft</h3><label>Programme name in English<input required value={name} onChange={event => setName(event.target.value)} /></label><label>Classification<input value={classification} onChange={event => setClassification(event.target.value)} placeholder="Use your configured taxonomy" /></label><label>Confidence<select value={confidence} onChange={event => setConfidence(event.target.value as Program["confidence"])}><option>low</option><option>medium</option><option>high</option></select></label>{configuredFields.map(field => <label key={field.key}>{field.label}{field.required ? " *" : ""}<input required={field.required} onChange={event => setValues({ ...values, [field.key]: event.target.value })} /></label>)}<button type="submit">Add draft</button></form><form onSubmit={attachEvidence} className="stack panel"><h3>Attach Dutch evidence</h3><label>Draft programme<select required value={evidenceProgram} onChange={event => setEvidenceProgram(event.target.value)}><option value="">Select a draft</option>{programs.filter(item => item.status === "draft").map(item => <option key={item.id} value={item.id}>{item.name_en}</option>)}</select></label><label>Document<select required value={documentId} onChange={event => setDocumentId(event.target.value)}><option value="">Select a scanned document</option>{documents.map(item => <option key={item.id} value={item.id}>{item.filename}</option>)}</select></label><label>Page number<input required type="number" min="1" value={page} onChange={event => setPage(Number(event.target.value))} /></label><label>Exact Dutch quote<textarea required value={quote} onChange={event => setQuote(event.target.value)} placeholder="Must exactly appear on the cited page." /></label><button type="submit">Verify and attach</button></form></div>{!programs.length ? <Empty title="No programme records" detail="First define the programme model, then build drafts from document evidence." /> : <div className="records">{programs.map(record => <article className="record" key={record.id}><div><Status value={record.status} /><h3>{record.name_en}</h3><p>{record.classification || "Unclassified"} · {record.confidence} confidence · setup v{record.setup_version}</p></div><p>{record.evidence.length} evidence reference{record.evidence.length === 1 ? "" : "s"}</p>{record.status === "draft" && <button disabled={!record.evidence.some(item => item.reviewer_confirmed)} onClick={() => void review(record)}>Mark reviewed</button>}</article>)}</div>}</section>;
}

function RuleBox({ label, value, onChange }: { label: string; value: string[]; onChange: (value: string) => void }) { return <label>{label}<textarea value={value.join("\n")} onChange={event => onChange(event.target.value)} placeholder="One item per line" /></label>; }
function Status({ value }: { value: string }) { return <span className={`status ${value}`}>{value.replaceAll("_", " ")}</span>; }
function Empty({ title, detail }: { title: string; detail: string }) { return <div className="empty"><h3>{title}</h3><p>{detail}</p></div>; }
