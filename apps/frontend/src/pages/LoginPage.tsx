import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";

import { loginSchema } from "../lib/validation";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";

type FormValues = {
  usernameOrEmail: string;
  password: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const login = useAuthStore((s) => s.login);
  const addToast = useUiStore((s) => s.addToast);
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: { usernameOrEmail: "admin", password: "ChangeMe123!" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const parsed = loginSchema.safeParse(values);
    if (!parsed.success) {
      addToast({ title: "Invalid form", message: parsed.error.errors[0]?.message, kind: "error" });
      return;
    }
    setSubmitting(true);
    try {
      await login(values.usernameOrEmail, values.password);
      addToast({ title: "Logged in", kind: "success" });
      navigate(location.state?.from || "/chat", { replace: true });
    } catch (error) {
      addToast({ title: "Login failed", message: (error as Error).message, kind: "error" });
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="grid min-h-screen place-items-center p-4 md:p-6">
      <div className="surface-glass w-full max-w-md rounded-[1.35rem] border border-white/60 p-6 backdrop-blur-xl md:p-7">
        <div className="mb-6">
          <div className="text-[11px] uppercase tracking-[0.16em] text-ink/60">AIRAGChat</div>
          <h1 className="mt-1 text-2xl font-semibold text-ink">OpenAI RAG Login</h1>
          <p className="mt-2 text-sm text-ink/65">
            Sign in with a local user account. Refresh tokens are stored in an HttpOnly cookie.
          </p>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-ink">Username or email</label>
            <input
              className="w-full rounded-xl border border-ink/10 bg-white/88 px-3 py-2.5 outline-none ring-0 focus:border-ink/25"
              {...register("usernameOrEmail", { required: "Required" })}
            />
            {errors.usernameOrEmail && (
              <div className="mt-1 text-xs text-[#578FCA]">{errors.usernameOrEmail.message}</div>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-ink">Password</label>
            <input
              type="password"
              className="w-full rounded-xl border border-ink/10 bg-white/88 px-3 py-2.5 outline-none ring-0 focus:border-ink/25"
              {...register("password", { required: "Required" })}
            />
            {errors.password && <div className="mt-1 text-xs text-[#578FCA]">{errors.password.message}</div>}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-paper shadow-soft transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
