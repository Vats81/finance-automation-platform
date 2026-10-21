// Spreadsheet apps run a cell that starts with = + - @ (or a tab/CR) as a
// formula, so text from users can execute when an exported CSV is opened.
// Prefixing such cells with an apostrophe makes them inert text. Plain
// numbers (including negatives) are left alone so they stay numbers.
const NUMBER = /^-?\d+(\.\d+)?$/;

export function csvCell(value: string | number): string {
  let text = String(value);
  if (!NUMBER.test(text) && /^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function csvRow(cells: (string | number)[]): string {
  return cells.map(csvCell).join(",");
}
