import { describe, expect, it } from 'vitest'

import { csvHeader, decodeText, importMessage } from './importFile'

describe('importFile', () => {
  it('decodes Windows-1250 when the bytes are not UTF-8', () => {
    // "Összeg" in Windows-1250: Ö is 0xD6.
    expect(decodeText(new Uint8Array([0xd6, 0x73, 0x73, 0x7a, 0x65, 0x67]))).toBe('Összeg')
    expect(decodeText(new TextEncoder().encode('Összeg'))).toBe('Összeg')
  })

  it('finds the header names whatever the delimiter', () => {
    expect(csvHeader('﻿Dátum;Összeg;"Közlemény"\r\n2026.09.05.;-4 500;Bolt\n')).toEqual(['Dátum', 'Összeg', 'Közlemény'])
    expect(csvHeader('date,amount,description\n')).toEqual(['date', 'amount', 'description'])
  })

  it('translates the import messages and keeps an unknown one', () => {
    expect(importMessage("invalid date '2026.13.01.'; use 2026-09-05 or 2026.09.05.")).toBe(
      "érvénytelen dátum: '2026.13.01.' (helyesen: 2026-09-05 vagy 2026.09.05.)",
    )
    expect(importMessage("Column 'Dátum' not found; the file has: date, amount")).toBe(
      "Nincs 'Dátum' nevű oszlop. A fájl oszlopai: date, amount.",
    )
    expect(importMessage('Something new')).toBe('Something new')
  })
})
