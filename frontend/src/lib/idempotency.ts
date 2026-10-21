import { useRef } from "react";

export interface IdempotencyOptions {
  idempotencyKey?: string;
}

/** Headers for a create request: the server uses the key to recognise a retry
 * or double-submit of the same form and create the record only once. */
export function idempotencyHeaders(options?: IdempotencyOptions): HeadersInit | undefined {
  return options?.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : undefined;
}

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * One key per form submission. Keep using the same key while retrying the same
 * submission (a timeout, a dropped connection, a second click) so it cannot
 * create the record twice; call renew() once the submission is finished or the
 * user has changed what they are sending.
 */
export function useSubmissionKey(): { key: () => string; renew: () => void } {
  const ref = useRef<string>(newKey());
  return { key: () => ref.current, renew: () => (ref.current = newKey()) };
}
