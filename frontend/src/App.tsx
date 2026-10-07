import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { DocumentRecord, ProgramSetup } from "./types";

const emptySetup: ProgramSetup = { version: 0, description: "", schema: {} };

export default function App() {
  const [tab, setTab] = useState<"documents" | "setup">("documents");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [setup, setSetup] = useState<ProgramSetup>(emptySetup);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextDocuments, nextSetup] = await Promise.all([api.documents(), api.setup()]);
      setDocuments(nextDocuments); setSetup(nextSetup);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load the application"); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return <main>
    <header><div><p className="eyebrow">INTERVIEW STARTER</p><h1>Programme inventory</h1><p>Turn policy-document evidence into a reviewable inventory. The definition of a programme is deliberately yours to design.</p></div></header>
    <nav>{(["documents", "setup"] as const).map(item => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item === "documents" ? "Document library" : "Programme setup"}</button>)}</nav>
    {message && <p className="notice">{message}</p>}
    {tab === "documents" && <DocumentLibrary documents={documents} onDocuments={setDocuments} onMessage={setMessage} />}
    {tab === "setup" && <SetupEditor setup={setup} onSaved={setSetup} onMessage={setMessage} />}
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
  const [schemaText, setSchemaText] = useState(() => JSON.stringify(setup.schema, null, 2));
  useEffect(() => { setDraft(setup); setSchemaText(JSON.stringify(setup.schema, null, 2)); }, [setup]);
  const save = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const schema: unknown = JSON.parse(schemaText);
      if (schema === null || Array.isArray(schema) || typeof schema !== "object") throw new Error("Schema must be a JSON object");
      onSaved(await api.saveSetup({ description: draft.description, schema: schema as Record<string, unknown> }));
      onMessage("Programme setup saved.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "Could not save setup"); }
  };
  return <section><div className="section-heading"><div><h2>Programme setup</h2><p>Describe the approach, then define the schema that will support it.</p></div><span>Version {setup.version}</span></div><form onSubmit={save} className="stack"><label>Approach description<textarea value={draft.description} onChange={event => setDraft({ ...draft, description: event.target.value })} placeholder="Describe how you will identify and assess programmes from the source material." /></label><label>Schema<textarea className="schema-editor" value={schemaText} onChange={event => setSchemaText(event.target.value)} placeholder={'{\n  "fields": []\n}'} /></label><button type="submit">Save programme setup</button></form></section>;
}

function Status({ value }: { value: string }) { return <span className={`status ${value}`}>{value.replaceAll("_", " ")}</span>; }
function Empty({ title, detail }: { title: string; detail: string }) { return <div className="empty"><h3>{title}</h3><p>{detail}</p></div>; }
