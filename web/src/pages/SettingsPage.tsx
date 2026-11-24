import { Check, Copy, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ApiError, type CreatedToken, type MerchantRule } from '@/api/client'
import {
  useCreateMerchantRule,
  useCreateOwnAccount,
  useDeleteOwnAccount,
  useOwnAccounts,
  useCreateToken,
  useDeleteMerchantRule,
  useMembers,
  useMerchantRules,
  useRevokeToken,
  useSetMemberRole,
  useTokens,
  useUpdateMerchantRule,
} from '@/api/queries'
import { LlmSettingsCard } from '@/components/LlmSettingsCard'
import { NativeSelect } from '@/components/NativeSelect'
import { EmptyState, ErrorState, LoadingRows } from '@/components/states'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { categoryLabel, formatDateTime } from '@/lib/format'

const refusal = (error: unknown, fallback: string) => (error instanceof ApiError ? error.message : fallback)

/**
 * W8 settings (docs/design/user-interface.md#settings): the group's members, the signed-in member's
 * API tokens for the Android app and the Sheets script, and the group's merchant → category rules,
 * the first layer of the hybrid categorizer, the own accounts and the LLM setting.
 */
export function SettingsPage() {
  const members = useMembers()
  const isAdmin = members.data?.some((member) => member.is_me && member.role === 'admin') ?? false
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Beállítások</h1>
      <MembersCard isAdmin={isAdmin} />
      <TokensCard />
      <MerchantRulesCard isAdmin={isAdmin} />
      <OwnAccountsCard isAdmin={isAdmin} />
      <LlmSettingsCard isAdmin={isAdmin} />
    </section>
  )
}

const ROLE_LABELS: Record<string, string> = { admin: 'Admin', member: 'Tag' }

function MembersCard({ isAdmin }: { isAdmin: boolean }) {
  const members = useMembers()
  const setRole = useSetMemberRole()
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tagok</CardTitle>
        <CardDescription>
          A csoport tagjai. Az admin módosíthatja a csoport beállításait (szabályok, szerepkörök); a csoportnak mindig
          marad legalább egy adminja. Tagot meghívni és eltávolítani egyelőre parancssorból lehet.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {members.isPending ? (
          <LoadingRows rows={2} />
        ) : members.isError ? (
          <ErrorState error={members.error} />
        ) : (
          <ul className="divide-y">
            {members.data.map((member) => (
              <li key={member.user_id} className="flex flex-wrap items-center gap-2 py-2">
                <span className="font-medium">{member.user_id}</span>
                {member.is_me && <Badge variant="secondary">Te</Badge>}
                <span className="text-sm text-muted-foreground">{member.email ?? 'nincs webes belépése'}</span>
                <span className="ml-auto">
                  {isAdmin ? (
                    <NativeSelect
                      aria-label={`${member.user_id} szerepköre`}
                      value={member.role}
                      disabled={setRole.isPending}
                      onChange={(event) => setRole.mutate({ memberId: member.user_id, role: event.target.value })}
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Tag</option>
                    </NativeSelect>
                  ) : (
                    <Badge variant="outline">{ROLE_LABELS[member.role] ?? member.role}</Badge>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
        {setRole.isError && <p className="mt-2 text-sm text-destructive">{roleRefusalText(setRole.error)}</p>}
      </CardContent>
    </Card>
  )
}

function TokensCard() {
  const tokens = useTokens()
  const create = useCreateToken()
  const revoke = useRevokeToken()
  const [name, setName] = useState('')
  const [created, setCreated] = useState<CreatedToken | null>(null)
  const [confirming, setConfirming] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    create.mutate(name.trim(), {
      onSuccess: (result) => {
        setCreated(result)
        setCopied(false)
        setName('')
      },
    })
  }

  async function copy(token: string) {
    try {
      await navigator.clipboard.writeText(token)
      setCopied(true)
    } catch {
      toast.error('A másolás nem sikerült; jelöld ki és másold ki kézzel.')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API-tokenek</CardTitle>
        <CardDescription>
          Az Android-alkalmazás és a táblázat-szkript ezzel küld tételeket a nevedben. A tokent csak létrehozáskor
          látod; ha elveszett, vond vissza, és hozz létre újat.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label htmlFor="t-name">Mire használod?</Label>
            <Input
              id="t-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="pl. Anna telefonja"
              maxLength={80}
              className="w-64"
            />
          </div>
          <Button type="submit" disabled={!name.trim() || create.isPending}>
            Új token
          </Button>
        </form>
        {create.isError && (
          <p className="text-sm text-destructive">{refusal(create.error, 'A token létrehozása nem sikerült.')}</p>
        )}

        {created && (
          <Alert>
            <AlertTitle>Új token: {created.record.name}</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>Másold be most az alkalmazásba. Később már nem jeleníthető meg újra.</p>
              <div className="flex flex-wrap items-center gap-2">
                <code className="rounded bg-muted px-2 py-1 text-xs break-all" data-testid="new-token">
                  {created.token}
                </code>
                <Button type="button" size="sm" variant="outline" onClick={() => void copy(created.token)}>
                  {copied ? <Check /> : <Copy />}
                  {copied ? 'Kimásolva' : 'Másolás'}
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {tokens.isPending ? (
          <LoadingRows rows={2} />
        ) : tokens.isError ? (
          <ErrorState error={tokens.error} />
        ) : tokens.data.length === 0 ? (
          <EmptyState>Még nincs API-tokened.</EmptyState>
        ) : (
          <ul className="divide-y">
            {tokens.data.map((token) => (
              <li key={token.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="font-medium">
                    {token.name} <code className="text-xs text-muted-foreground">{token.prefix}…</code>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Létrehozva: {formatDateTime(token.created_at)} · Utoljára használva:{' '}
                    {token.last_used_at ? formatDateTime(token.last_used_at) : 'még soha'}
                  </p>
                </div>
                {token.revoked_at ? (
                  <Badge variant="outline">Visszavonva: {formatDateTime(token.revoked_at)}</Badge>
                ) : confirming === token.id ? (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={revoke.isPending}
                      onClick={() =>
                        revoke.mutate(token.id, {
                          onSuccess: () => {
                            setConfirming(null)
                            toast.success(`Visszavonva: ${token.name}`)
                          },
                          onError: (error) => toast.error(refusal(error, 'A visszavonás nem sikerült.')),
                        })
                      }
                    >
                      Igen, visszavonom
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>
                      Mégse
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => setConfirming(token.id)}>
                    Visszavonás
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function roleRefusalText(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) return 'A csoportnak legalább egy adminja kell, hogy maradjon.'
  return refusal(error, 'A szerepkör módosítása nem sikerült.')
}

function MerchantRulesCard({ isAdmin }: { isAdmin: boolean }) {
  const rules = useMerchantRules()
  const create = useCreateMerchantRule()
  const [merchant, setMerchant] = useState('')
  const [category, setCategory] = useState('')
  const categories = rules.data?.categories ?? []

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!merchant.trim() || !category) return
    create.mutate(
      { merchant: merchant.trim(), category },
      {
        onSuccess: () => {
          setMerchant('')
          setCategory('')
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Kereskedő → kategória szabályok</CardTitle>
        <CardDescription>
          A csoport saját szabályai erősebbek az automatikus kulcsszavas kategorizálásnál. Egy szabály a kereskedőnév
          minden szavára illeszkedik, így a „SPAR” a „SPAR 0123 BUDAPEST”-re is. A szabály csak az ezután érkező
          tételekre hat. {isAdmin ? 'Adminként te módosíthatod.' : 'Csak a csoport adminja módosíthatja.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isAdmin && (
          <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <Label htmlFor="r-merchant">Kereskedő</Label>
              <Input
                id="r-merchant"
                value={merchant}
                onChange={(event) => setMerchant(event.target.value)}
                placeholder="pl. SPAR"
                maxLength={80}
                className="w-56"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="r-category">Kategória</Label>
              <NativeSelect id="r-category" value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">Válassz…</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {categoryLabel(item)}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <Button type="submit" disabled={!merchant.trim() || !category || create.isPending}>
              Szabály hozzáadása
            </Button>
          </form>
        )}
        {create.isError && <p className="text-sm text-destructive">{ruleRefusal(create.error)}</p>}

        {rules.isPending ? (
          <LoadingRows rows={2} />
        ) : rules.isError ? (
          <ErrorState error={rules.error} />
        ) : rules.data.rules.length === 0 ? (
          <EmptyState>Még nincs szabály.</EmptyState>
        ) : (
          <ul className="divide-y">
            {rules.data.rules.map((rule) => (
              <RuleRow key={rule.id} rule={rule} categories={categories} editable={isAdmin} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function ruleRefusal(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) return 'Erre a kereskedőre már van szabály a csoportban.'
  return refusal(error, 'A szabály mentése nem sikerült.')
}

function RuleRow({ rule, categories, editable }: { rule: MerchantRule; categories: string[]; editable: boolean }) {
  const update = useUpdateMerchantRule()
  const remove = useDeleteMerchantRule()
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div className="min-w-0">
        <p className="font-medium">{rule.merchant}</p>
        <p className="text-xs text-muted-foreground">
          Illeszkedik: „{rule.merchant_key}” · felvette: {rule.created_by}
        </p>
      </div>
      {!editable ? (
        <Badge variant="outline">{categoryLabel(rule.category)}</Badge>
      ) : (
        <div className="flex items-center gap-2">
          <NativeSelect
            aria-label={`${rule.merchant} kategóriája`}
            value={rule.category}
            disabled={update.isPending}
            onChange={(event) =>
              update.mutate(
                {
                  id: rule.id,
                  merchant: rule.merchant,
                  category: event.target.value,
                },
                { onError: (error) => toast.error(ruleRefusal(error)) },
              )
            }
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {categoryLabel(item)}
              </option>
            ))}
          </NativeSelect>
          <Button
            size="icon"
            variant="ghost"
            aria-label={`${rule.merchant} szabály törlése`}
            disabled={remove.isPending}
            onClick={() =>
              remove.mutate(rule.id, {
                onSuccess: () => toast.success(`Törölve: ${rule.merchant}`),
                onError: (error) => toast.error(refusal(error, 'A törlés nem sikerült.')),
              })
            }
          >
            <Trash2 />
          </Button>
        </div>
      )}
    </li>
  )
}

function OwnAccountsCard({ isAdmin }: { isAdmin: boolean }) {
  const accounts = useOwnAccounts()
  const create = useCreateOwnAccount()
  const remove = useDeleteOwnAccount()
  const [label, setLabel] = useState('')

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!label.trim()) return
    create.mutate(label.trim(), { onSuccess: () => setLabel('') })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Saját számlák és partnerek</CardTitle>
        <CardDescription>
          A csoporton belüli átutalás nem kiadás és nem bevétel. Ha egy új tétel ezek közül valamelyiket nevezi meg
          (számlaszám vagy a név, ahogy a bank írja), átvezetésként kerül be, és kimarad az Áttekintés összegeiből. A
          lista csak az ezután érkező tételekre hat.{' '}
          {isAdmin ? 'Adminként te módosíthatod.' : 'Csak a csoport adminja módosíthatja.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isAdmin && (
          <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <Label htmlFor="a-label">Számlaszám vagy név</Label>
              <Input
                id="a-label"
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder="pl. 12345678-87654321 vagy MINTA ANNA"
                maxLength={80}
                className="w-72"
              />
            </div>
            <Button type="submit" disabled={!label.trim() || create.isPending}>
              Hozzáadás
            </Button>
          </form>
        )}
        {create.isError && (
          <p className="text-sm text-destructive">
            {create.error instanceof ApiError && create.error.status === 409
              ? 'Ez a számla vagy név már szerepel a listán.'
              : refusal(create.error, 'A mentés nem sikerült.')}
          </p>
        )}

        {accounts.isPending ? (
          <LoadingRows rows={2} />
        ) : accounts.isError ? (
          <ErrorState error={accounts.error} />
        ) : accounts.data.length === 0 ? (
          <EmptyState>Még nincs megadva saját számla vagy partner.</EmptyState>
        ) : (
          <ul className="divide-y">
            {accounts.data.map((account) => (
              <li key={account.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <span className="font-medium break-all">{account.label}</span>
                  <Badge variant="outline">{account.kind === 'account' ? 'Számlaszám' : 'Név'}</Badge>
                </div>
                {isAdmin && (
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label={`${account.label} törlése`}
                    disabled={remove.isPending}
                    onClick={() =>
                      remove.mutate(account.id, {
                        onSuccess: () => toast.success(`Törölve: ${account.label}`),
                        onError: (error) => toast.error(refusal(error, 'A törlés nem sikerült.')),
                      })
                    }
                  >
                    <Trash2 />
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
