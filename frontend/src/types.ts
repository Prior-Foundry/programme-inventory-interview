export type DocumentRecord = {
  id: string; filename: string; size_bytes: number; page_count?: number;
  extraction_status: "pending" | "extracted" | "needs_ocr" | "failed";
  extracted_characters: number; error?: string;
};

export type ProgramSetup = {
  version: number; description: string; schema: Record<string, unknown>;
};

export type Evidence = {
  document_id: string; page_number: number; quote_nl: string;
  extracted_location?: string; reviewer_confirmed: boolean;
};

export type Program = {
  id: string; setup_version: number; name_en: string; classification?: string;
  field_values: Record<string, unknown>; status: "draft" | "reviewed";
  confidence: "low" | "medium" | "high"; evidence: Evidence[];
};
