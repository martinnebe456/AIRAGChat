import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { apiClient } from "../api/client";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { FormDialog } from "../components/FormDialog";
import { PageCard } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";
import { userCreateSchema } from "../lib/validation";
import { useUiStore } from "../store/uiStore";

type UserRow = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: "user" | "contributor" | "admin";
  is_active: boolean;
  created_at: string;
};

type CreateUserForm = {
  username: string;
  email: string;
  display_name: string;
  role: "user" | "contributor" | "admin";
  password: string;
};

export function AdminUsersPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const [filter, setFilter] = useState("");
  const [isCreateUserOpen, setIsCreateUserOpen] = useState(false);
  const [resetPasswordTarget, setResetPasswordTarget] = useState<UserRow | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [toggleStatusTarget, setToggleStatusTarget] = useState<UserRow | null>(null);

  const { register, handleSubmit, reset } = useForm<CreateUserForm>({ defaultValues: { role: "user" } });

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => apiClient.get<{ items: UserRow[] }>("/users"),
  });

  const createMutation = useMutation({
    mutationFn: async (payload: CreateUserForm) => apiClient.post("/users", payload),
    onSuccess: async () => {
      addToast({ title: "User created", kind: "success" });
      reset({ role: "user", password: "" });
      setIsCreateUserOpen(false);
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => addToast({ title: "Create failed", message: (e as Error).message, kind: "error" }),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ userId, body }: { userId: string; body: Record<string, unknown> }) =>
      apiClient.patch(`/users/${userId}`, body),
    onSuccess: async () => {
      addToast({ title: "User updated", kind: "success" });
      setToggleStatusTarget(null);
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => addToast({ title: "Update failed", message: (e as Error).message, kind: "error" }),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async ({ userId, newPassword }: { userId: string; newPassword: string }) =>
      apiClient.post(`/users/${userId}/reset-password`, { new_password: newPassword }),
    onSuccess: async () => {
      addToast({ title: "Password reset", kind: "success" });
      setResetPasswordTarget(null);
      setResetPasswordValue("");
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => addToast({ title: "Password reset failed", message: (e as Error).message, kind: "error" }),
  });

  const filteredUsers = (usersQuery.data?.items ?? []).filter((u) =>
    [u.username, u.email, u.display_name, u.role].join(" ").toLowerCase().includes(filter.toLowerCase()),
  );

  const submitCreateUser = handleSubmit((values) => {
    const parsed = userCreateSchema.safeParse(values);
    if (!parsed.success) {
      addToast({ title: "Invalid form", message: parsed.error.errors[0]?.message, kind: "error" });
      return;
    }
    createMutation.mutate(values);
  });

  return (
    <div className="grid gap-4">
      <PageCard
        title="User Management"
        subtitle="Create, activate/deactivate, manage roles, and reset passwords for local users."
        actions={
          <button
            type="button"
            onClick={() => setIsCreateUserOpen(true)}
            className="rounded-lg bg-ink px-3 py-2 text-sm font-medium text-paper"
          >
            Create User
          </button>
        }
      >
        <div className="mb-4 flex items-center gap-2">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter users..."
            className="w-full max-w-sm rounded-lg border border-ink/12 bg-white/80 px-3 py-2 text-sm"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink/10 text-xs uppercase tracking-[0.12em] text-ink/60">
                <th className="px-2 py-2">User</th>
                <th className="px-2 py-2">Role</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Created</th>
                <th className="px-2 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id} className="border-b border-ink/5 align-top hover:bg-white/35">
                  <td className="px-2 py-2">
                    <div className="font-medium text-ink">{user.display_name}</div>
                    <div className="text-xs text-ink/55">{user.username}</div>
                    <div className="text-xs text-ink/55">{user.email}</div>
                  </td>
                  <td className="px-2 py-2">
                    <select
                      className="rounded-md border border-ink/12 bg-white/85 px-2 py-1 text-xs"
                      value={user.role}
                      onChange={(e) => updateMutation.mutate({ userId: user.id, body: { role: e.target.value } })}
                    >
                      <option value="user">user</option>
                      <option value="contributor">contributor</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <span
                      className={`rounded-full border px-2 py-1 text-xs ${
                        user.is_active
                          ? "border-[#3674B5]/35 bg-[#578FCA]/12 text-[#3674B5]"
                          : "border-[#FADA7A]/80 bg-[#F5F0CD]/95 text-[#3674B5]"
                      }`}
                    >
                      {user.is_active ? "active" : "inactive"}
                    </span>
                  </td>
                  <td className="px-2 py-2 text-xs text-ink/60">{formatDateTime(user.created_at)}</td>
                  <td className="px-2 py-2">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-md border border-ink/12 bg-white/85 px-2 py-1 text-xs"
                        onClick={() => setToggleStatusTarget(user)}
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-ink/12 bg-white/85 px-2 py-1 text-xs"
                        onClick={() => {
                          setResetPasswordTarget(user);
                          setResetPasswordValue("");
                        }}
                      >
                        Reset Password
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredUsers.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-2 py-6 text-center text-sm text-ink/60">
                    No users match the current filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </PageCard>

      <FormDialog
        open={isCreateUserOpen}
        onOpenChange={(open) => {
          setIsCreateUserOpen(open);
          if (!open && !createMutation.isPending) reset({ role: "user", password: "" });
        }}
        title="Create user"
        description="Provision a local account and assign initial RBAC role."
        submitLabel="Create user"
        isSubmitting={createMutation.isPending}
        onSubmit={(e) => void submitCreateUser(e)}
      >
        <input
          {...register("username")}
          placeholder="username"
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        />
        <input
          {...register("email")}
          placeholder="email"
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        />
        <input
          {...register("display_name")}
          placeholder="display name"
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        />
        <select
          {...register("role")}
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        >
          <option value="user">user</option>
          <option value="contributor">contributor</option>
          <option value="admin">admin</option>
        </select>
        <input
          type="password"
          {...register("password")}
          placeholder="temporary password"
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        />
      </FormDialog>

      <FormDialog
        open={!!resetPasswordTarget}
        onOpenChange={(open) => {
          if (!open) {
            setResetPasswordTarget(null);
            setResetPasswordValue("");
          }
        }}
        title="Reset password"
        description={
          resetPasswordTarget
            ? `Set a new password for ${resetPasswordTarget.display_name} (${resetPasswordTarget.username}).`
            : undefined
        }
        submitLabel="Reset password"
        isSubmitting={resetPasswordMutation.isPending}
        onSubmit={() => {
          if (!resetPasswordTarget) return;
          if (!resetPasswordValue || resetPasswordValue.trim().length < 8) {
            addToast({ title: "Password too short", message: "Use at least 8 characters.", kind: "warning" });
            return;
          }
          resetPasswordMutation.mutate({ userId: resetPasswordTarget.id, newPassword: resetPasswordValue });
        }}
      >
        <input
          type="password"
          value={resetPasswordValue}
          onChange={(e) => setResetPasswordValue(e.target.value)}
          placeholder="New password (min 8 chars)"
          className="w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm"
        />
      </FormDialog>

      <ConfirmDialog
        open={!!toggleStatusTarget}
        onOpenChange={(open) => {
          if (!open) setToggleStatusTarget(null);
        }}
        title={toggleStatusTarget?.is_active ? "Deactivate user" : "Activate user"}
        description={
          toggleStatusTarget
            ? `${toggleStatusTarget.is_active ? "Deactivate" : "Activate"} ${toggleStatusTarget.display_name}?`
            : undefined
        }
        confirmLabel={toggleStatusTarget?.is_active ? "Deactivate" : "Activate"}
        tone="warning"
        isPending={updateMutation.isPending}
        onConfirm={() => {
          if (!toggleStatusTarget) return;
          updateMutation.mutate({
            userId: toggleStatusTarget.id,
            body: { is_active: !toggleStatusTarget.is_active },
          });
        }}
      />
    </div>
  );
}
