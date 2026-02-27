import { z } from "zod";

export const loginSchema = z.object({
  usernameOrEmail: z.string().min(1, "Username or email is required"),
  password: z.string().min(1, "Password is required"),
});

export const userCreateSchema = z.object({
  username: z.string().min(3),
  email: z.string().email(),
  display_name: z.string().min(1),
  role: z.enum(["user", "contributor", "admin"]),
  password: z.string().min(8),
});

