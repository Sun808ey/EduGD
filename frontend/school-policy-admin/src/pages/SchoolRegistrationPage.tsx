import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { Alert, Box, Button, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { errorMessage } from '@/services/errors'
import { formatDate } from '@/lib/format'
import type { SchoolRegistration } from '@/types/api.types'

const timezones = ['Africa/Kampala', 'Africa/Nairobi', 'UTC']
const emptySchool: SchoolRegistration = { name: '', district: '', school_type: '', contact_person: '', official_telephone: '', official_email: null, physical_location: '', authorised_administrator_name: '', timezone: '' }

export function SchoolRegistrationPage() {
  const location = useLocation()
  const settingsMode = location.pathname === '/settings'
  const [form, setForm] = useState<SchoolRegistration>(emptySchool)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const cache = useQueryClient()
  const school = useQuery({ queryKey: ['school'], queryFn: ({ signal }) => adminService.getSchool(signal) })
  const mutation = useMutation({ mutationFn: () => school.data ? adminService.updateSchool(form) : adminService.registerSchool(form), onSuccess: async () => { setError(''); setEditing(false); await cache.invalidateQueries({ queryKey: ['school'] }) }, onError: (caught) => setError(errorMessage(caught)) })

  function update(field: keyof SchoolRegistration, value: string) { setForm((current) => ({ ...current, [field]: value })) }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(''); mutation.mutate() }

  if (school.isLoading) return <LoadingState label="Loading school profile…" />
  if (school.isError) return <ErrorState message="School profile is temporarily unavailable." retry={() => void school.refetch()} />
  if (school.data && !editing) return <Stack spacing={3}><Box component="header"><Typography component="h1" variant="h4" sx={{ fontWeight: 800 }}>{settingsMode ? 'School settings' : 'School profile'}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Edit the school profile used for policy timetables and device enrollment.</Typography></Box><Paper variant="outlined" sx={{ borderRadius: 3, p: 3 }}><Stack spacing={1}><Typography variant="h6" sx={{ fontWeight: 800 }}>{school.data.name}</Typography><Typography>{school.data.district} · {school.data.school_type}</Typography><Typography variant="body2" color="text.secondary">Timezone: {school.data.timezone} · Registered {formatDate(school.data.created_at)}</Typography></Stack><Button variant="contained" onClick={() => { setForm(school.data!); setEditing(true) }} sx={{ mt: 3 }}>Edit school profile</Button></Paper></Stack>

  const fields: Array<{ key: keyof SchoolRegistration; label: string; type?: string; maxLength?: number }> = [
    { key: 'name', label: 'School name', maxLength: 160 }, { key: 'district', label: 'District', maxLength: 120 },
    { key: 'school_type', label: 'School type', maxLength: 80 }, { key: 'contact_person', label: 'Contact person', maxLength: 120 },
    { key: 'official_telephone', label: 'Official school telephone number', type: 'tel', maxLength: 32 },
    { key: 'official_email', label: 'Official school email (optional)', type: 'email', maxLength: 254 },
    { key: 'physical_location', label: 'Physical location', maxLength: 255 },
    { key: 'authorised_administrator_name', label: 'Authorised administrator', maxLength: 120 },
  ]
  return <Stack spacing={3}><Box component="header"><Typography component="h1" variant="h4" sx={{ fontWeight: 800 }}>{school.data ? 'Edit school profile' : 'Register your school'}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>These details are used by administrators, policy schedules, and secure device enrollment.</Typography></Box><Alert severity="info">Do not enter learner information or private telephone contacts. The timetable timezone is required before time-based policies can be published.</Alert><Paper component="form" onSubmit={submit} variant="outlined" sx={{ borderRadius: 3, p: { xs: 2, sm: 3 } }}><Stack spacing={2}><Typography component="h2" variant="h6" sx={{ fontWeight: 800 }}>School details</Typography>{error && <Alert severity="error">{error}</Alert>}<Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' } }}>{fields.map(({ key, label, type, maxLength }) => <TextField key={key} name={key} required={key !== 'official_email'} label={label} type={type} value={form[key] ?? ''} onChange={(event) => update(key, event.currentTarget.value)} onInput={(event) => update(key, (event.target as HTMLInputElement).value)} slotProps={{ htmlInput: { maxLength } }} />)}<TextField name="timezone" required select label="Timetable timezone" value={form.timezone} onChange={(event) => update('timezone', event.currentTarget.value)} helperText="Policy windows use this timezone.">{timezones.map((timezone) => <MenuItem key={timezone} value={timezone}>{timezone}</MenuItem>)}</TextField></Box><Stack direction="row" spacing={1}><Button type="submit" variant="contained" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : school.data ? 'Save changes' : 'Register school'}</Button>{school.data && <Button type="button" variant="outlined" onClick={() => { setForm(school.data!); setEditing(false); setError('') }}>Cancel</Button>}</Stack></Stack></Paper></Stack>
}
