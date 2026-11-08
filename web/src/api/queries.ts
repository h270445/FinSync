import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from './client'

export function useEvents() {
  return useQuery({
    queryKey: ['events'],
    queryFn: async () => unwrap(await api.GET('/v1/events')).events,
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
