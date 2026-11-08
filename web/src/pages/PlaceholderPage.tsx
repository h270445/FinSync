import { EmptyState } from '@/components/states'

/** Screens of the plan (docs/design/user-interface.md#web-app) that are not built yet. */
export function PlaceholderPage({ title, screen }: { title: string; screen: string }) {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <EmptyState>Ez a képernyő ({screen}) még nem készült el.</EmptyState>
    </section>
  )
}
