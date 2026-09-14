// The AI (Insights, Assistant) is prompted for plain text with **bold**
// markers and bullet lines — nothing richer — so this renders exactly that
// subset instead of pulling in a full markdown/sanitization dependency.
// Text content stays as React children throughout (no dangerouslySetInnerHTML),
// so this can't introduce an XSS hole the way naive HTML injection would.
function renderBoldSegments(line: string): React.ReactNode[] {
  return line.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part ? <span key={i}>{part}</span> : null;
  });
}

export function MarkdownLite({ text, className }: { text: string; className?: string }) {
  const lines = text.split("\n");
  return (
    <p className={className}>
      {lines.map((line, i) => (
        <span key={i}>
          {renderBoldSegments(line)}
          {i < lines.length - 1 && <br />}
        </span>
      ))}
    </p>
  );
}
