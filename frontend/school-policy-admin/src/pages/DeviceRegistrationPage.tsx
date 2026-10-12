import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { adminService } from '@/services/admin.service'
import { errorMessage } from '@/services/errors'

const states = ['REGISTERED', 'READY_FOR_PROVISIONING', 'PROVISIONING', 'ENROLLED', 'COMPLIANT', 'ASSIGNED', 'RETURNED', 'RETIRED', 'PROVISIONING_FAILED', 'NON_COMPLIANT', 'MISSING', 'DAMAGED']
const initial = { asset_number: '', manufacturer: '', model: '', serial_number: '', android_version: '13', api_level: '33', date_received: '', condition: '', department: '', asset_lifecycle_status: 'REGISTERED', asset_notes: '' }

export function DeviceRegistrationPage() {
  const [form, setForm] = useState(initial); const [error, setError] = useState(''); const navigate = useNavigate(); const cache = useQueryClient()
  const mutation = useMutation({ mutationFn: () => adminService.registerSchoolDevice({ ...form, api_level: Number(form.api_level), asset_notes: form.asset_notes || null }), onSuccess: async () => { await cache.invalidateQueries({ queryKey: ['devices'] }); navigate('/devices') }, onError: (caught) => setError(errorMessage(caught)) })
  const update = (field: keyof typeof initial, value: string) => setForm((current) => ({ ...current, [field]: value }))
  return <Stack component="form" spacing={2} sx={{ maxWidth: 760 }} onSubmit={(event: FormEvent) => { event.preventDefault(); setError(''); mutation.mutate() }}><Typography component="h1" variant="h4" sx={{ fontWeight: 800 }}>Register school-owned device</Typography><Typography color="text.secondary">Record a school asset before provisioning. This does not enroll or send commands to a device.</Typography>{error && <Alert severity="error">{error}</Alert>}<Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{[['asset_number','Asset number'],['manufacturer','Manufacturer'],['model','Model'],['serial_number','Serial number'],['date_received','Date received'],['condition','Condition'],['department','Department'],['android_version','Android version'],['api_level','Android API level']].map(([field,label]) => <TextField key={field} required label={label} type={field === 'date_received' ? 'date' : field === 'api_level' ? 'number' : 'text'} value={form[field as keyof typeof initial]} onChange={(event) => update(field as keyof typeof initial, event.target.value)} slotProps={field === 'date_received' ? { inputLabel: { shrink: true } } : undefined} fullWidth />)}</Stack><TextField select required label="Asset lifecycle status" value={form.asset_lifecycle_status} onChange={(event) => update('asset_lifecycle_status', event.target.value)}>{states.map((state) => <MenuItem key={state} value={state}>{state.replaceAll('_', ' ')}</MenuItem>)}</TextField><TextField label="Notes" multiline minRows={2} value={form.asset_notes} onChange={(event) => update('asset_notes', event.target.value)} slotProps={{ htmlInput: { maxLength: 512 } }} /><Button type="submit" variant="contained" disabled={mutation.isPending} sx={{ alignSelf: 'start' }}>{mutation.isPending ? 'Registering…' : 'Register device'}</Button></Stack>
}
