export function firstString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) {
    return value;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const found = firstString(item);
      if (found) {
        return found;
      }
    }
  }

  return undefined;
}

/** Axios default when the response body had no usable message. */
export function isGenericHttpErrorMessage(message: string): boolean {
  return /^Request failed with status code \d+$/i.test(message.trim());
}

export function readApiErrorMessage(data: unknown): string | undefined {
  if (Array.isArray(data)) {
    return firstString(data);
  }

  if (!data || typeof data !== "object") {
    return undefined;
  }

  const record = data as Record<string, unknown>;
  const topLevel =
    firstString(record.detail) ??
    firstString(record.message) ??
    firstString(record.non_field_errors);
  if (topLevel) {
    return topLevel;
  }

  // DRF field errors e.g. { quantity: ["Insufficient stock…"] } — use the first.
  const fields = readFieldErrors(data);
  return Object.values(fields)[0];
}

export function readFieldErrors(data: unknown): Record<string, string> {
  if (!data || typeof data !== "object") {
    return {};
  }

  const fields: Record<string, string> = {};
  for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
    if (key === "detail" || key === "message" || key === "non_field_errors") {
      continue;
    }
    const message = firstString(value);
    if (message) {
      fields[key] = message;
    }
  }
  return fields;
}
