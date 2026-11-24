// Hungarian texts of the category correction, shared by the W3 list and the W4 detail.

import { ApiError, type CategoryCorrection, type FinSyncEvent } from '@/api/client'
import { categoryLabel, categorySourceLabel } from '@/lib/format'

export const refusal = (error: unknown, fallback: string) => (error instanceof ApiError ? error.message : fallback)

/** "Forrás: beépített szótár · bizonytalan" under the category, so a guess never looks like a decision. */
export function categoryCertainty(event: FinSyncEvent): string {
  const source = categorySourceLabel(event.category_source)
  if (event.category_source === 'user') return `Forrás: ${source}`
  return `Forrás: ${source} · ${event.uncertain ? 'bizonytalan, csak javaslat' : 'biztos'}`
}

/** What happened to the merchant rule after "always use this", in Hungarian. */
export function ruleMessage(result: CategoryCorrection): string | null {
  const merchant = result.merchant_rule?.merchant ?? ''
  const category = categoryLabel(result.merchant_rule?.category ?? '')
  switch (result.merchant_rule_outcome) {
    case 'created':
      return `Új szabály: ${merchant} → ${category}. A következő vásárlásoknál ezt használjuk.`
    case 'confirmed':
      return `A(z) ${merchant} szabály megerősítve.`
    case 'updated':
      return `A(z) ${merchant} szabály módosítva: ${category}.`
    case 'kept':
      return `A csoportnak már van szabálya erre a kereskedőre (${category}); azt csak admin módosíthatja a Beállításokban.`
    default:
      return null
  }
}
