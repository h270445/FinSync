/**
 * Reading an export file for W7 in the browser: CSV becomes text, XLSX becomes base64 for `POST /v1/imports`.
 *
 * Hungarian bank exports are often Windows-1250 rather than UTF-8, so CSV bytes are decoded as UTF-8 first
 * and, when that fails, as Windows-1250. XLSX is not read here; the server reads its first sheet.
 */

export type ReadFile =
  | { kind: 'csv'; name: string; content: string; header: string[]; requestSize: number }
  | { kind: 'xlsx'; name: string; base64: string; requestSize: number }

// The API's body limit for /v1/imports is 1 MiB (docs/guides/api.md); a little is left for the JSON around it.
export const MAX_REQUEST_BYTES = 1024 * 1024 - 4096

export async function readImportFile(file: File): Promise<ReadFile> {
  const bytes = new Uint8Array(await file.arrayBuffer())
  if (isXlsx(file.name, bytes)) {
    const base64 = toBase64(bytes)
    return { kind: 'xlsx', name: file.name, base64, requestSize: base64.length }
  }
  const content = decodeText(bytes)
  return { kind: 'csv', name: file.name, content, header: csvHeader(content), requestSize: new TextEncoder().encode(content).length }
}

/** An XLSX file is a ZIP archive: it starts with "PK", whatever its name says. */
function isXlsx(name: string, bytes: Uint8Array): boolean {
  return name.toLowerCase().endsWith('.xlsx') || (bytes[0] === 0x50 && bytes[1] === 0x4b)
}

export function decodeText(bytes: Uint8Array): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder('windows-1250').decode(bytes)
  }
}

/** The header names of a CSV, for the column suggestions; the server detects the delimiter the same way. */
export function csvHeader(content: string): string[] {
  const first = content.replace(/^﻿/, '').split(/\r?\n/, 1)[0] ?? ''
  const delimiter = [';', '\t', ','].reduce((best, candidate) =>
    first.split(candidate).length > first.split(best).length ? candidate : best,
  )
  return first
    .split(delimiter)
    .map((name) => name.trim().replace(/^"(.*)"$/, '$1'))
    .filter(Boolean)
}

function toBase64(bytes: Uint8Array): string {
  let binary = ''
  const chunk = 0x8000 // String.fromCharCode takes its arguments on the stack; large files go in chunks
  for (let start = 0; start < bytes.length; start += chunk)
    binary += String.fromCharCode(...bytes.subarray(start, start + chunk))
  return btoa(binary)
}

// The API's messages are English (code and API stay English); the UI is Hungarian, so the import messages
// of finsync/ingestion/csv_import.py are translated here. An unknown message is shown as it came.
const MESSAGES: [RegExp, (...groups: string[]) => string][] = [
  [/^invalid amount (.+)$/, (raw) => `érvénytelen összeg: ${raw}`],
  [/^the amount must be a non-zero number$/, () => 'az összeg nem lehet nulla'],
  [/^invalid date ('[^']*')(?:;.*)?$/, (raw) => `érvénytelen dátum: ${raw} (helyesen: 2026-09-05 vagy 2026.09.05.)`],
  [/^the description is empty$/, () => 'üres a leírás'],
  [/^invalid currency (.+)$/, (raw) => `érvénytelen pénznem: ${raw}`],
  [/^Column (.+) not found; the file has: (.*)$/, (name, columns) => `Nincs ${name} nevű oszlop. A fájl oszlopai: ${columns}.`],
  [/^A required column is not mapped$/, () => 'A dátum, az összeg és a leírás oszlopát meg kell adni.'],
  [/^The file is empty$/, () => 'A fájl üres.'],
  [/^The file has a header but no rows$/, () => 'A fájlban csak fejléc van, tétel nincs.'],
  [/^The file is not a readable XLSX workbook$/, () => 'A fájl nem olvasható XLSX munkafüzet.'],
  [/^The file has more than (\d+) rows; split it$/, (max) => `A fájl több mint ${max} soros. Bontsd több részre.`],
]

export function importMessage(message: string): string {
  for (const [pattern, text] of MESSAGES) {
    const match = pattern.exec(message)
    if (match) return text(...match.slice(1))
  }
  return message
}
