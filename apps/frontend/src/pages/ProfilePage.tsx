import { PageCard } from "../components/Ui";
import { useAuthStore } from "../store/authStore";

export function ProfilePage() {
  const me = useAuthStore((s) => s.me);

  return (
    <PageCard title="Profile" subtitle="Current authenticated user and session security posture.">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-ink/10 bg-white p-4">
          <div className="text-xs uppercase tracking-[0.12em] text-ink/60">Identity</div>
          <div className="mt-2 text-sm text-ink">
            <div>
              <span className="font-semibold">Username:</span> {me?.username}
            </div>
            <div>
              <span className="font-semibold">Email:</span> {me?.email}
            </div>
            <div>
              <span className="font-semibold">Display name:</span> {me?.display_name}
            </div>
            <div>
              <span className="font-semibold">Role:</span> {me?.role}
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-ink/10 bg-white p-4">
          <div className="text-xs uppercase tracking-[0.12em] text-ink/60">Session Handling</div>
          <ul className="mt-2 list-disc pl-4 text-sm text-ink/75">
            <li>Access token stored in memory only (Zustand store).</li>
            <li>Refresh token stored in HttpOnly cookie.</li>
            <li>All API calls go through backend.</li>
          </ul>
        </div>
      </div>
    </PageCard>
  );
}

