export const dateTime = new Intl.DateTimeFormat('en-UG', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Africa/Kampala',
})

export function formatDate(value?: string | null) {
  if (!value) return 'Unknown'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? 'Unknown' : dateTime.format(parsed)
}
