export interface SetupStatus {
  is_setup: boolean;
}

export interface SetupRequest {
  household_name: string;
  owner_email: string;
  owner_display_name: string;
  owner_password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface MeResponse {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  household_id: string;
  household_name: string;
  last_login_at: string | null;
}

export interface InviteAcceptRequest {
  token: string;
  email: string;
  display_name: string;
  password: string;
}

export interface StatusResponse {
  status: string;
}
