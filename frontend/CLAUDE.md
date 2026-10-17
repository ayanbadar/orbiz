# Meraki Interiors Frontend

This repository is a production-ready React application foundation.
Future agents **must** follow the architecture and conventions below.

If architecture changes, update this file in the same change. Do not let agent context go stale.

---

## Project Architecture

### Feature-based layout

```text
src/
├── components/          # Shared app components + shadcn ui/
├── constants/           # Global constants (e.g. routes)
├── context/             # App-wide providers only
├── features/            # Feature modules
├── hooks/               # Shared hooks only
├── lib/                 # Shared infrastructure (api, env, query-client)
├── utils/               # Shared utilities
├── app.tsx
└── main.tsx
```

Feature shape (create layers only when needed — no empty folders):

```text
features/<feature-name>/
├── api/
│   ├── <feature>.api.ts        # TanStack Query hooks
│   ├── <feature>.service.ts    # HTTP / data access
│   └── <feature>.keys.ts       # Query keys
├── components/
├── constants/
├── context/
├── hooks/
├── types/
└── utils/
```

### Shared vs feature-specific

- **Shared** (`components/`, `hooks/`, `utils/`, `constants/`, `context/`, `lib/`): truly cross-feature only.
- **Feature-specific**: stays inside `features/<name>/`. Never dump feature logic into shared folders.

### State management hierarchy

```text
URL state            → nuqs
Server state         → TanStack Query
Form state           → React Hook Form (+ Zod)
Feature-shared state → React Context (feature-local when possible)
Component-local      → useState / useReducer
```

Do **not** introduce Redux, Zustand, Jotai, or other global stores without a demonstrated need.
Do **not** use Context as a replacement for TanStack Query.
Do **not** put everything into URL parameters.

### API architecture

```text
Component → Feature Query/Mutation Hook → Feature Service → Shared API Client → Backend
```

- Shared Axios client: `src/lib/api/index.ts`
- Services own HTTP. Hooks own TanStack Query wiring. Components own UI.
- Centralize query keys in `*.keys.ts`.

### Routing

- React Router only (do not add TanStack Router).
- Centralized route helpers in `src/constants/routes.ts` using `joinPath()` from `@/utils`.
- Never hardcode route strings in components.

### shadcn / Tailwind

- UI foundation is shadcn/ui under `src/components/ui/`.
- **Always** add shadcn components via the official CLI (`npx shadcn@latest add …`).
- Do **not** manually recreate shadcn components.
- Prefer semantic tokens: `bg-background`, `text-foreground`, `bg-muted`, `text-muted-foreground`, `border-border`.
- Avoid arbitrary colors / one-off Tailwind values unless required.

### Environment

- All `VITE_*` access goes through `src/lib/env.ts` (validated with Zod).
- Never scatter `import.meta.env.VITE_*` through the app.
- Client env vars are public — never put secrets in `VITE_*`.

---

## Non-Negotiable Rules

1. Application source is **TypeScript only** — no `.js` / `.jsx` under `src/`.
2. Explicit `any` is prohibited (`@typescript-eslint/no-explicit-any` is an error). Prefer `unknown` + narrowing.
3. Filenames are **kebab-case** (`demo-page.tsx`, `use-media-query.ts`).
4. Imports use the `@/` alias — avoid deep relative paths.
5. Use the shadcn CLI for shadcn components; do not hand-roll them.
6. Server state → TanStack Query. URL state → nuqs. Form state → React Hook Form + Zod (`z.infer`).
7. Do not introduce overlapping libraries when the existing stack already solves the problem.
8. Feature-specific code stays in features. Shared folders stay shared.
9. Do not create unused architecture folders or unnecessary abstractions.
10. Do not weaken ESLint / TypeScript rules to make errors go away.
11. Do not bypass TypeScript or ESLint with `any`, broad `eslint-disable`, or `@ts-ignore` unless explicitly justified in the change.

---

## Development Workflow

1. Inspect existing architecture before changing it.
2. Reuse existing utilities, components, and hooks.
3. Follow existing feature patterns (`service` → `keys` → `api` hooks → components).
4. Avoid duplicate implementations.
5. After meaningful changes, run: `npm run lint`, `npm run typecheck`, `npm run test` (and `npm run build` when relevant).
6. Keep changes scoped to the requested work — no unrelated refactors.
7. Update this file when conventions change.

---

## Adding a New Feature

1. Decide global vs feature-specific.
2. Create/extend `features/<name>/`.
3. Add types.
4. Add service methods (`*.service.ts`).
5. Add query keys (`*.keys.ts`).
6. Add query/mutation hooks (`*.api.ts`).
7. Add feature components.
8. Add feature hooks/context **only when required**.
9. Add URL state with nuqs where appropriate (tabs, filters, sort, pagination, search).
10. Reuse shared UI/utilities where appropriate.
11. Add tests where valuable.
12. Register routes via `ROUTES` helpers — never hardcode paths.

---

## Dependency Rules

Before adding a dependency, check whether the existing stack already covers the need:

- React, React Router, TanStack Query, nuqs, React Hook Form, Zod, shadcn, Tailwind, Axios

Prefer these over overlapping alternatives.

---

## Tooling Expectations

Required scripts (must work independently for CI):

- `lint` / `lint:fix`
- `typecheck`
- `test` / `test:watch`
- `build`
- `format` / `format:check`
- `dev` / `preview`

### Notable version decisions

- **Vite 6 + Vitest 3** are pinned together. Vite 8 (create-vite default) and Vitest 5 were incompatible in practice (Vitest runner/`describe` failures and duplicate Vite type conflicts). Prefer upgrading them only as a matched pair once upstream support is stable.
