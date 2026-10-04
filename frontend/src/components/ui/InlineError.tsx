import { Button } from "@/components/ui/Button";

export function errorMessage(err: unknown, fallback = "Something went wrong."): string {
  return err instanceof Error ? err.message : fallback;
}

// A section's own fetch failed. Shown in place of "Loading..." so a slow or
// failed request ends in a visible error with a way to retry, instead of a
// spinner that never resolves (the apiFetch timeout makes the request fail
// in bounded time; this is what the user then sees).
export function InlineError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="secondary" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}
