
- For endpoints where users need to access their own data but otherwise require admin privileges, `Depends(get_current_user)` followed by explicit checks (`current_user.id != user_id and current_user.role != "admin"`) is the cleanest way.

## Memory Management API
- FastAPI makes it very easy to filter querysets conditionally based on current user roles (`current_user.role != "admin"` vs `current_user.id`).
- When defining response models with `sqlmodel` and `pydantic`, `Optional[int]` for primary keys on creation is automatically satisfied as `int` for read responses. We chose not to expose embeddings to improve API throughput.

## UI Patterns & Shared Components
- Use `web/src/lib/utils.ts` with `clsx` and `tailwind-merge` for safe class merging.
- Shared components are located in `web/src/components/`.
- `Layout.tsx` handles both sidebar and top bar, with conditional rendering to exclude itself from `/login`.
- Components (`MetricCard`, `DataTable`, `LoadingSkeleton`) follow a consistent Tailwind-based dark mode support pattern.

## Dashboard Implementation
- Created dashboard at `/dashboard` with system health, database, and redis status metrics.
- Used `MetricCard` and `DataTable` components for consistent UI.
- Integrated `QuickActions` client component for interactive tasks.
- API endpoints used: `/system/health`, `/system/database`, `/system/redis`, `/audit?limit=5`.
- All fetches use `cache: 'no-store'` to ensure real-time data on the dashboard.

## Users & IAM Page Implementation
- Implemented `web/src/app/users/page.tsx` using Next.js App Router.
- Used Server Actions (`web/src/app/actions/users.ts`) for creating users and revalidating the list.
- Integrated `DataTable` component for listing users.
- Implemented role-based access control (RBAC) check within the page component to ensure only admins can access.
- Fetched `X-API-Key` from the JWT token stored in the `access_token` cookie for backend authentication.
- Used `revalidatePath("/users")` to ensure the user list is up-to-date after creation.

### Audit & Observability Implementation
- **API Authentication**: Used `X-API-Key` header for backend requests in server components, matching the existing pattern in the `Users` page.
- **Admin Access Control**: Implemented role verification via `verifyAuthToken` from `jose` library.
- **Dynamic Configuration**: The `DEBUG_WIRE_LOG` setting is updated via `POST /admin/config`, which modifies `os.environ` in the backend, allowing for runtime debugging without container restart.
- **Pagination**: Implemented simple server-side pagination using Next.js search parameters and the `skip`/`limit` query params supported by the telemetry API.
- **Component Reusability**: Successfully used the shared `DataTable` component for audit logs.

### Cortex Page Implementation (Feb 25, 2026)
- Implemented the Cortex page with a tabbed UI for Memory Storage, Skills Management, and Evolution History.
- Used `searchParams` for tab switching to keep the main page as a Server Component, improving SSR and performance.
- Created server actions in `web/src/app/actions/memskills.ts` for approving and rejecting memory skill changelogs.
- Integrated `DataTable` and `MetricCard` components for a consistent UI.
- Handled admin-only protection by verifying the JWT token and checking the user role.
- Noted that `searchParams` is a Promise in Next.js 15+, which requires awaiting it in the page component.

- **Dynamic User Display**: Implemented dynamic user information display in the RootLayout and Layout components. 
- **Server-Side Auth**: Leveraged Next.js Server Components to read cookies and verify JWT tokens server-side before passing user data to client components.
- **Tailwind Capitalize**: Used Tailwind's 'capitalize' class for role display, with a manual override for 'admin' to 'Administrator' to match original design.
- **Git Ignore Gotcha**: Discovered that root-level `lib/` ignore pattern affects nested `lib` directories in subprojects (e.g., `web/src/lib`), requiring force-add or ignore adjustment.
