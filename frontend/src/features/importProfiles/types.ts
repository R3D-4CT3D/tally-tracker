import type { ColumnMapping, DateFormat } from "../imports/types";

export interface ImportProfile {
  id: string;
  name: string;
  column_mapping: ColumnMapping;
  date_format: DateFormat;
  source_hint: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportProfileCreateRequest {
  name: string;
  column_mapping: ColumnMapping;
  date_format: DateFormat;
  source_hint?: string | null;
}
