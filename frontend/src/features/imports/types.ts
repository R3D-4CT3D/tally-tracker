export interface ColumnMapping {
  date: string;
  description: string;
  amount: string;
}

export type DateFormat = "MDY" | "DMY" | "YMD";

export interface ImportUploadResponse {
  import_session_id: string;
  filename: string | null;
  source: "csv" | "paste";
  header: string[];
  sample_rows: string[][];
  row_count: number;
  suggested_mapping: ColumnMapping | null;
  date_format_suggestion: DateFormat;
  date_format_ambiguous: boolean;
}

export interface ImportPreviewRow {
  row_index: number;
  date: string | null;
  description: string | null;
  amount_cents: number | null;
  category_id: string | null;
  matched_rule_id: string | null;
  duplicate: "exact" | "fuzzy" | null;
  error: string | null;
  will_import: boolean;
}

export interface ImportPreviewResponse {
  rows: ImportPreviewRow[];
  valid_count: number;
  error_count: number;
  exact_duplicate_count: number;
  fuzzy_duplicate_count: number;
}

export interface ImportBatch {
  id: string;
  filename: string | null;
  row_count: number;
  imported_count: number;
  skipped_dupes: number;
  created_at: string;
  undoable: boolean;
}
