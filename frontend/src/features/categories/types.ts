export interface Category {
  id: string;
  name: string;
  parent_id: string | null;
  icon: string;
  color: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryCreateRequest {
  name: string;
  parent_id?: string | null;
  icon: string;
  color: string;
}

export interface CategoryUpdateRequest {
  name?: string;
  parent_id?: string | null;
  icon?: string;
  color?: string;
}
