/**
 * Join path segments into a normalized absolute path string.
 * Filters empty segments and collapses duplicate slashes.
 */
export function joinPath(...segments: Array<string | number>): string {
  const joined = segments
    .map((segment) => String(segment).replace(/^\/+|\/+$/g, ""))
    .filter(Boolean)
    .join("/");

  return `/${joined}`;
}
