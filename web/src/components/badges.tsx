import { Badge } from '@/components/ui/badge'
import { sourceLabel } from '@/lib/format'

export function SourceBadge({ source }: { source: string }) {
  return (
    <Badge variant="outline" className="font-normal">
      {sourceLabel(source)}
    </Badge>
  )
}

/** Amber is used only for this tag (design rule: the only warm colour). */
export function ReviewTag() {
  return <Badge className="bg-warning text-warning-foreground">Ellenőrzésre vár</Badge>
}
