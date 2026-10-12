import { Alert, List, ListItem, ListItemText, Paper, Stack, Typography } from '@mui/material'

export function DataProtectionPage() {
  return <Stack spacing={3}>
    <header><Typography variant="overline" color="text.secondary">Governance</Typography><Typography component="h1" variant="h4" sx={{ fontWeight: 800 }}>Data protection</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>This notice describes the limited information EDUGD uses to administer school-owned devices.</Typography></header>
    <Alert severity="info"><strong>Before using real learner information:</strong> confirm the school’s Personal Data Protection Office registration and certificate requirements with the responsible data-protection officer. This panel is not legal advice.</Alert>
    <Paper variant="outlined" sx={{ p: 3 }}><Typography variant="h6" sx={{ fontWeight: 800 }}>Privacy notice</Typography><List dense>
      <ListItem><ListItemText primary="What we collect" secondary="School contact details, school-owned device numbers and hardware identifiers, policy records, class or department responsibility, and security-relevant audit events." /></ListItem>
      <ListItem><ListItemText primary="Why we collect it" secondary="To register school assets, prepare and apply approved device policies, show compliance, respond to incidents, and maintain an accountable audit trail." /></ListItem>
      <ListItem><ListItemText primary="What we do not collect" secondary="Do not enter learner names when a school device number is sufficient. Do not upload learner photographs, private device content, health information, family information, or personal telephone contacts." /></ListItem>
      <ListItem><ListItemText primary="Who can view it" secondary="Only authenticated administrators with the relevant role permission can view or change school records. Public pages do not expose administrator, device, policy, assignment, or audit data." /></ListItem>
      <ListItem><ListItemText primary="How long it is kept" secondary="Records are retained only for the school’s documented operational, safety, and audit needs. Retired asset data can be redacted after the configured retention window while non-personal audit integrity anchors remain." /></ListItem>
      <ListItem><ListItemText primary="Corrections" secondary="Use the asset or assignment correction controls on the device detail page. Each correction records the changed field names and reason without duplicating the old personal values." /></ListItem>
    </List></Paper>
    <Paper variant="outlined" sx={{ p: 3 }}><Typography variant="h6" sx={{ fontWeight: 800 }}>Security safeguards</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Use the HTTPS deployment URL, strong administrator passwords, role permissions, append-only audit evidence, encrypted approved backups, and the documented retention process. Never place credentials, learner content, or pairing tokens in notes or translations.</Typography></Paper>
  </Stack>
}
