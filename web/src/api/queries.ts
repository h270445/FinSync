import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type CategoryLineInput, type ManualTransaction, type MerchantRuleInput, unwrap } from './client'
import type { components } from './schema'

export function useEvents() {
  return useQuery({
    queryKey: ['events'],
    queryFn: async () => unwrap(await api.GET('/v1/events')).events,
  })
}

/** W2: month totals; without a month, the server's current month (Budapest time). */
export function useOverview(month: string | null) {
  return useQuery({
    queryKey: ['overview', month],
    queryFn: async () => unwrap(await api.GET('/v1/overview', { params: { query: month ? { month } : {} } })),
  })
}

export function useEventDecisions(eventId: number) {
  return useQuery({
    queryKey: ['events', eventId, 'decisions'],
    queryFn: async () =>
      unwrap(await api.GET('/v1/events/{event_id}/decisions', { params: { path: { event_id: eventId } } })).decisions,
  })
}

export function useReviews() {
  return useQuery({
    queryKey: ['reviews'],
    queryFn: async () => unwrap(await api.GET('/v1/matches/review')).reviews,
  })
}

/** Every review action changes both the queue and the events, so both are refetched. */
function useInvalidateAll() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries()
}

export function useConfirmMatch() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async (decisionId: number) =>
      unwrap(await api.POST('/v1/matches/{decision_id}/confirm', { params: { path: { decision_id: decisionId } } })),
    onSuccess,
  })
}

export function useRejectMatch() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async (decisionId: number) =>
      unwrap(await api.POST('/v1/matches/{decision_id}/reject', { params: { path: { decision_id: decisionId } } })),
    onSuccess,
  })
}

export function useSplitEvent() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async ({ eventId, transactionId }: { eventId: number; transactionId: number }) =>
      unwrap(
        await api.POST('/v1/events/{event_id}/split', {
          params: { path: { event_id: eventId } },
          body: { transaction_id: transactionId },
        }),
      ),
    onSuccess,
  })
}

// Category correction (W3 list, W4 detail). A correction changes the event, the overview's category split
// and possibly the merchant rules, so everything is refetched.

export function useCategoryChanges(eventId: number) {
  return useQuery({
    queryKey: ['events', eventId, 'category-changes'],
    queryFn: async () =>
      unwrap(await api.GET('/v1/events/{event_id}/category-changes', { params: { path: { event_id: eventId } } }))
        .changes,
  })
}

/** Confirm or change an event's category; `remember` teaches the group's merchant memory. */
export function useSetCategory() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async ({ eventId, category, remember = false }: { eventId: number; category: string; remember?: boolean }) =>
      unwrap(
        await api.PUT('/v1/events/{event_id}/category', {
          params: { path: { event_id: eventId } },
          body: { category, remember },
        }),
      ),
    onSuccess,
  })
}

export function useSetMixed() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async ({ eventId, mixed }: { eventId: number; mixed: boolean }) =>
      unwrap(await api.PUT('/v1/events/{event_id}/mixed', { params: { path: { event_id: eventId } }, body: { mixed } })),
    onSuccess,
  })
}

/** Replace the event's category lines; an empty list removes the split. */
export function useSetCategoryLines() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async ({ eventId, lines }: { eventId: number; lines: CategoryLineInput[] }) =>
      unwrap(
        await api.PUT('/v1/events/{event_id}/category-lines', { params: { path: { event_id: eventId } }, body: { lines } }),
      ),
    onSuccess,
  })
}

export function useSetTransfer() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async ({ eventId, transfer }: { eventId: number; transfer: boolean }) =>
      unwrap(
        await api.PUT('/v1/events/{event_id}/transfer', { params: { path: { event_id: eventId } }, body: { transfer } }),
      ),
    onSuccess,
  })
}

/** W6 manual entry. A new record may create an event, join one or open a review, so everything is refetched. */
export function useCreateTransaction() {
  const onSuccess = useInvalidateAll()
  return useMutation({
    mutationFn: async (body: ManualTransaction) => unwrap(await api.POST('/v1/transactions', { body })),
    onSuccess,
  })
}

export type ImportRequest = components['schemas']['ImportIn']

/** W7: a preview (`dry_run`) changes nothing; a real import changes events, reviews and totals. */
export function useImportFile() {
  const invalidateAll = useInvalidateAll()
  return useMutation({
    mutationFn: async (body: ImportRequest) => unwrap(await api.POST('/v1/imports', { body })),
    onSuccess: (_, body) => (body.dry_run ? undefined : invalidateAll()),
  })
}

// W8 settings.

export function useMembers() {
  return useQuery({
    queryKey: ['members'],
    queryFn: async () => unwrap(await api.GET('/v1/members')).members,
  })
}

/** An admin changes a member's role; the answer is the new member list. */
export function useSetMemberRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ memberId, role }: { memberId: string; role: string }) =>
      unwrap(
        await api.PUT('/v1/members/{member_id}/role', { params: { path: { member_id: memberId } }, body: { role } }),
      ).members,
    onSuccess: (members) => queryClient.setQueryData(['members'], members),
  })
}

/** The signed-in member's own API tokens (works only with the web session). */
export function useTokens() {
  return useQuery({
    queryKey: ['tokens'],
    queryFn: async () => unwrap(await api.GET('/v1/tokens')).tokens,
  })
}

export function useCreateToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (name: string) => unwrap(await api.POST('/v1/tokens', { body: { name } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tokens'] }),
  })
}

export function useRevokeToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (tokenId: number) =>
      unwrap(await api.POST('/v1/tokens/{token_id}/revoke', { params: { path: { token_id: tokenId } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tokens'] }),
  })
}

/** The group's merchant rules and the categories a rule may name. Rules change only new records. */
export function useMerchantRules() {
  return useQuery({
    queryKey: ['merchant-rules'],
    queryFn: async () => unwrap(await api.GET('/v1/merchant-rules')),
  })
}

export function useCreateMerchantRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: MerchantRuleInput) => unwrap(await api.POST('/v1/merchant-rules', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['merchant-rules'] }),
  })
}

export function useUpdateMerchantRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: MerchantRuleInput & { id: number }) =>
      unwrap(await api.PUT('/v1/merchant-rules/{rule_id}', { params: { path: { rule_id: id } }, body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['merchant-rules'] }),
  })
}

export function useDeleteMerchantRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) =>
      unwrap(await api.DELETE('/v1/merchant-rules/{rule_id}', { params: { path: { rule_id: id } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['merchant-rules'] }),
  })
}

/** The group's own accounts and counterparties: new records naming one are transfers. */
export function useOwnAccounts() {
  return useQuery({
    queryKey: ['own-accounts'],
    queryFn: async () => unwrap(await api.GET('/v1/own-accounts')).own_accounts,
  })
}

export function useCreateOwnAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (label: string) => unwrap(await api.POST('/v1/own-accounts', { body: { label } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['own-accounts'] }),
  })
}

export function useDeleteOwnAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) =>
      unwrap(await api.DELETE('/v1/own-accounts/{account_id}', { params: { path: { account_id: id } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['own-accounts'] }),
  })
}
