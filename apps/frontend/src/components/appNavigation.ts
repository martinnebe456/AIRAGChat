export type AppNavItem = {
  label: string;
  path: string;
  section: "main" | "admin";
  requiresAdmin?: boolean;
};

export const BASE_NAV_ITEMS: AppNavItem[] = [
  { label: "Chat", path: "/chat", section: "main" },
  { label: "Document Library", path: "/documents", section: "main" },
  { label: "Profile", path: "/profile", section: "main" },
];

export const ADMIN_NAV_ITEMS: AppNavItem[] = [
  { label: "User Management", path: "/admin/users", section: "admin", requiresAdmin: true },
  { label: "Projects & Access", path: "/admin/projects", section: "admin", requiresAdmin: true },
  { label: "System Settings", path: "/admin/settings", section: "admin", requiresAdmin: true },
  { label: "Embedding Reindex", path: "/admin/embeddings/reindex", section: "admin", requiresAdmin: true },
  { label: "Eval Datasets", path: "/admin/evals/datasets", section: "admin", requiresAdmin: true },
  { label: "Run Evaluation", path: "/admin/evals/run", section: "admin", requiresAdmin: true },
  { label: "Eval Results", path: "/admin/evals/results", section: "admin", requiresAdmin: true },
];

export function getAppNavigationSections(isAdmin: boolean) {
  return {
    main: BASE_NAV_ITEMS,
    admin: isAdmin ? ADMIN_NAV_ITEMS : [],
  };
}

