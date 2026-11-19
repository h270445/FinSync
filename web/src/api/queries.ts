import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type ManualTransaction, type MerchantRuleInput, unwrap } from './client'
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
