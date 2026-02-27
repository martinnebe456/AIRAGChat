// Placeholder for OpenAPI-generated types.
// Regenerate from backend OpenAPI and replace this file in a real CI pipeline.
export type ApiUser = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: "user" | "contributor" | "admin";
  is_active: boolean;
};

export type ApiDocument = {
  id: string;
  filename_original: string;
  status: string;
  file_size_bytes: number;
  created_at: string;
  owner_user_id: string;
};

