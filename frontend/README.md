# Meraki Interiors — Frontend

Production-ready React application foundation.

## Stack

- Vite + React + TypeScript
- React Router
- TanStack Query
- shadcn/ui + Tailwind CSS
- React Hook Form + Zod
- nuqs
- Axios
- ESLint + Prettier
- Vitest + React Testing Library

## Getting started

```bash
cp .env.example .env
npm install
npm run dev
```

## Scripts

| Script                 | Purpose                             |
| ---------------------- | ----------------------------------- |
| `npm run dev`          | Start Vite dev server               |
| `npm run build`        | Typecheck + production build        |
| `npm run preview`      | Preview production build            |
| `npm run lint`         | ESLint                              |
| `npm run lint:fix`     | ESLint with autofix                 |
| `npm run typecheck`    | TypeScript project references check |
| `npm run format`       | Prettier write                      |
| `npm run format:check` | Prettier check                      |
| `npm run test`         | Vitest (single run)                 |
| `npm run test:watch`   | Vitest watch mode                   |

## Architecture

See `CLAUDE.md` for non-negotiable conventions, feature layout, and workflow rules.
