# Frontend coding guide

Build Orbiz screens with the stack already in this app. Reach for an existing tool before adding a new one. Architecture and folder rules live in [CLAUDE.md](./CLAUDE.md); this file is how to write the code inside that layout.

## Default choices

| Need                              | Use                                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------ |
| Server data                       | TanStack Query hooks in `features/<name>/api/`                                             |
| HTTP                              | Feature service calling the shared Axios client in `src/lib/api`                           |
| Forms                             | React Hook Form + Zod                                                                      |
| Filters, search, tabs, pagination | `nuqs` in the URL                                                                          |
| UI                                | shadcn components in `src/components/ui`                                                   |
| Styling                           | Tokens in [DESIGN.md](./DESIGN.md), mapped through the shadcn variables in `src/index.css` |
| Routes                            | `ROUTES` helpers in `src/constants/routes.ts`                                              |
| Env                               | `src/lib/env.ts`                                                                           |

Do not add Redux, Zustand, a second form library, or a second data-fetching library.

## Data flow

```text
Component → query/mutation hook → service → shared API client → backend
```

- Services perform HTTP and return typed data. They do not render UI.
- Hooks own query keys, `useQuery`, and `useMutation`.
- Components read hook results and render.
- Query keys live in `*.keys.ts` and include every parameter that changes the result.

```ts
export const useOrders = (params: OrderListParams) =>
  useQuery({
    queryKey: ORDER_QUERY_KEYS.list(params),
    queryFn: () => OrderService.list(params),
  });
```

Invalidate the affected query keys after a mutation. After creating an order, refresh the order list and the dashboard summary that shows that order.

## Types and API shapes

- Type request and response bodies next to the feature. Derive form types with `z.infer`.
- Treat backend fields as the source of truth. Match serializer field names.
- Use `unknown` and narrow it when a payload is not yet trusted. Do not use `any`.
- Surface `ApiError` status and message in the UI. Do not swallow failed requests.

## Forms

- One Zod schema per form. The schema is the validation, and the resolver wires it to React Hook Form.
- Show field errors beside the field. Disable the submit button while `isSubmitting` is true.
- The AI order draft is a form. The seller can edit every extracted field before confirm.
- Confirm actions that change an order, payment, or stock level. Show the result of that action in the same screen.

## Screens

Every primary screen has four states: loading, empty, success, and error. Use `QueryState` when the state is a simple message and a retry. Use a real empty state with the next action when the list is legitimately empty ("Add a product").

- Orders show fulfilment status and payment status as separate badges.
- Sandbox payment UI says it is PayPal Sandbox.
- Tables that need sorting, filtering, and column control use AG Grid for the orders or products grid. Keep simpler lists as normal markup.
- Put page-level data fetching in the page component. Keep presentational components free of query hooks when they only receive props.

## Assistant UI

- Render the model's draft as editable fields, not as a committed order.
- Show which records an answer used when the API returns them.
- Label missing or uncertain fields.
- Offer a visible new-conversation action. Keep history for the current session.
- Show a clear failure message when the model or the request fails. Leave the seller's typed message in place.

## Files and components

- Filenames are kebab-case. Component exports are PascalCase.
- Import from `@/`.
- Add shadcn components with the CLI (`npx shadcn@latest add …`).
- Keep a component in the feature until a second feature needs it.
- Colocate constants, types, and helpers inside the feature. Promote them to `src/lib` or `src/components` only when they are shared.
- Prefer a straightforward component over a generic abstraction used once.

## Accessibility and layout

- Label every input. Tie errors to the field with `aria-invalid` and `role="alert"`.
- Use buttons for actions and links for navigation.
- Support keyboard use on dialogs, menus, and the assistant composer.
- Build layouts that work on a laptop width first, then check a narrow viewport for the demo path: dashboard, assistant, order detail.

## What to avoid

- Hardcoded API URLs or route strings in components.
- Secrets or PayPal credentials in `VITE_*` variables. The client talks to the Orbiz API only.
- Fetching in `useEffect` when TanStack Query can own the request.
- Copying server lists into local state.
- Optimistic payment or stock updates. Wait for the server response, then update the cache.
- New UI kits, CSS frameworks, or state libraries beside the ones in the table above.
