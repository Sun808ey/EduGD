import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Bot, CheckCircle2, Compass, ExternalLink, MessageCircle, Send, Sparkles, X } from 'lucide-react'
import { Alert, Box, Button, Chip, Divider, Drawer, IconButton, LinearProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { answerDocumentationQuestion } from '@/content/assistantKnowledge'

type TourStep = {
  title: string
  route: string
  summary: string
  detail: string
  keywords: string[]
}

type AssistantMode = 'tour' | 'qa'
type ChatMessage = { role: 'assistant' | 'admin'; text: string; source?: string }

const tourSteps: TourStep[] = [
  { title: 'School profile', route: '/settings', summary: 'Start with the school record and timetable settings.', detail: 'Confirm the school name, district, administrator contact, and Africa/Kampala timetable timezone before creating time-based policies.', keywords: ['school', 'profile', 'timezone', 'settings'] },
  { title: 'Device records', route: '/devices', summary: 'Review the registered Android devices and their current state.', detail: 'Open each record to review its human-facing reference, Android version, enrollment, policy assignment, synchronization, compliance, and privacy-safe evidence.', keywords: ['device', 'devices', 'phone', 'tablet', 'pixel'] },
  { title: 'Applications and domains', route: '/policies/catalogue', summary: 'Maintain the approved application and domain catalogues.', detail: 'Enabled entries can be selected for new policies. Disabled entries remain available for history and existing signed policies but cannot be selected for new policy rules.', keywords: ['application', 'applications', 'app', 'domain', 'catalogue'] },
  { title: 'Policy builder', route: '/policies', summary: 'Create, preview, publish, and revise school-facing controls.', detail: 'Use the policy form to define approved and blocked applications, device restrictions, network controls, schedules, compliance checks, and offline behaviour.', keywords: ['policy', 'policies', 'blocked', 'approved', 'restriction'] },
  { title: 'Assignments', route: '/assignments', summary: 'Connect policy revisions to the responsible class or department.', detail: 'Assignments show which school responsibility owns a device or policy scope and provide the operational reason for changes.', keywords: ['assignment', 'assign', 'class', 'department'] },
  { title: 'Provisioning', route: '/provisioning', summary: 'Issue enrollment credentials and complete device onboarding.', detail: 'Create or review enrollment tokens and QR provisioning details. Device identity comes from the Android DPC; it is not typed manually into the device record.', keywords: ['provision', 'provisioning', 'enrollment', 'enrol', 'qr', 'token'] },
  { title: 'Enforcement center', route: '/enforcement', summary: 'Use the operational shortcuts for active controls and evidence.', detail: 'This is the guided operations hub for policies, devices, catalogue controls, enforcement evidence, synchronization, and review workflows.', keywords: ['enforcement', 'control', 'controls', 'evidence'] },
  { title: 'Synchronization queue', route: '/sync', summary: 'Track command delivery and device acknowledgements.', detail: 'A command is only applied after the enrolled device confirms it. Pending, sent, applied, and failed states remain available for operational review.', keywords: ['sync', 'synchronization', 'synchronisation', 'queue', 'command'] },
  { title: 'Violations and incidents', route: '/reports', summary: 'Review policy, application, domain, and device-control events.', detail: 'Filter the recorded evidence by device, class, and period. Violation hashes and event sequences support traceable review without exposing learner content.', keywords: ['violation', 'violations', 'incident', 'blocked', 'report'] },
  { title: 'Audit logs', route: '/logs', summary: 'Finish with the accountable administrative record.', detail: 'Use the event-type filter to review authentication, enrollment, assignment, synchronization, asset, incident, and violation activity.', keywords: ['audit', 'log', 'logs', 'history', 'review'] },
  { title: 'Operations overview', route: '/operations', summary: 'See the complete workflow in one operational view.', detail: 'The operations overview brings school profile, devices, policies, provisioning, enforcement, synchronization, violations, incidents, and audit coverage together.', keywords: ['operations', 'overview', 'workflow', 'complete', 'tour'] },
]

const initialMessages: ChatMessage[] = [{ role: 'assistant', text: 'Ask a quick question about the documented dashboard workflow. Answers come from the curated documentation shown in this assistant.', source: 'Dashboard documentation · Assistant scope' }]

function isAdministrativeActionRequest(question: string) {
  return /\b(delete|remove|revoke|approve|publish|assign|block|unblock|clear|create|edit|apply|change|send|retry|sync now)\b/i.test(question)
}

export function AdminTourAssistant() {
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<AssistantMode>('tour')
  const [activeIndex, setActiveIndex] = useState(0)
  const [question, setQuestion] = useState('')
  const [reply, setReply] = useState('I can guide you through the complete school-device workflow. Choose a step or ask where to start.')
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const step = tourSteps[activeIndex]
  const progress = ((activeIndex + 1) / tourSteps.length) * 100

  function openStep(index: number) {
    const nextStep = tourSteps[index]
    setActiveIndex(index)
    setReply(`Opening ${nextStep.title}. ${nextStep.summary}`)
    navigate(nextStep.route)
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submittedQuestion = question.trim()
    if (!submittedQuestion) return

    if (mode === 'qa') {
      const answer = isAdministrativeActionRequest(submittedQuestion)
        ? { answer: 'I can explain the documented workflow, but I cannot approve, publish, assign, revoke, delete, create, edit, apply, or otherwise perform administrative changes.', source: 'Dashboard documentation · Assistant scope' }
        : answerDocumentationQuestion(submittedQuestion)
      setMessages((current) => [
        ...current,
        { role: 'admin', text: submittedQuestion },
        answer
          ? { role: 'assistant', text: answer.answer, source: answer.source }
          : { role: 'assistant', text: 'I could not find that in the dashboard documentation. Ask about devices, policies, catalogue status, provisioning, synchronization, violations, audit, privacy, operations, or the assistant scope.', source: 'Dashboard documentation · Assistant scope' },
      ])
      setQuestion('')
      return
    }

    const normalized = submittedQuestion.toLowerCase()
    const matchedIndex = tourSteps.findIndex((candidate) => candidate.keywords.some((keyword) => normalized.includes(keyword)))
    if (matchedIndex >= 0) openStep(matchedIndex)
    else setReply('I can take you to the school profile, devices, applications, policies, assignments, provisioning, enforcement, synchronization, violations, audit logs, or the operations overview.')
    setQuestion('')
  }

  function selectMode(nextMode: AssistantMode) {
    setMode(nextMode)
    setQuestion('')
    if (nextMode === 'tour') setReply('I can guide you through the complete school-device workflow. Choose a step or ask where to start.')
  }

  return <>
    <Button variant="contained" startIcon={<Sparkles size={17} aria-hidden="true" />} onClick={() => setOpen(true)} aria-label="Open AI workflow assistant" sx={{ position: 'fixed', right: { xs: 16, sm: 24 }, bottom: { xs: 16, sm: 24 }, zIndex: (theme) => theme.zIndex.speedDial, borderRadius: 999, px: 2.25, py: 1.25, boxShadow: 4, textTransform: 'none', fontWeight: 800 }}>Workflow assistant</Button>
    <Drawer anchor="right" open={open} onClose={() => setOpen(false)} ModalProps={{ keepMounted: true }} slotProps={{ paper: { sx: { width: { xs: '100%', sm: 430 }, maxWidth: '100vw', p: 0, fontSize: { xs: '.875rem', sm: '.9rem' } } } }}>
      <Stack sx={{ height: '100%' }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', justifyContent: 'space-between', p: 2.25, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
          <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
            <Box sx={{ display: 'grid', placeItems: 'center', width: 38, height: 38, borderRadius: 2, bgcolor: 'rgba(255,255,255,.16)' }}><Bot size={21} aria-hidden="true" /></Box>
            <Box><Typography variant="subtitle1" sx={{ fontWeight: 800 }}>AI workflow assistant</Typography><Typography variant="caption" sx={{ color: 'inherit', opacity: .85 }}>Tour and documentation Q&amp;A</Typography></Box>
          </Stack>
          <IconButton aria-label="Close workflow assistant" onClick={() => setOpen(false)} sx={{ color: 'inherit' }}><X size={20} /></IconButton>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ px: 2.25, pt: 2 }}>
          <Button size="small" variant={mode === 'tour' ? 'contained' : 'outlined'} onClick={() => selectMode('tour')} aria-pressed={mode === 'tour'} sx={{ textTransform: 'none', fontWeight: 800 }}>Tour</Button>
          <Button size="small" variant={mode === 'qa' ? 'contained' : 'outlined'} onClick={() => selectMode('qa')} aria-pressed={mode === 'qa'} sx={{ textTransform: 'none', fontWeight: 800 }}>Quick Q&amp;A</Button>
        </Stack>
        {mode === 'tour' ? (
          <>
            <Box sx={{ px: 2.25, pt: 1.75 }}><Alert icon={<Compass size={19} />} severity="info" sx={{ alignItems: 'flex-start' }}>Follow the numbered steps to understand the complete workflow. This assistant only navigates the dashboard and does not change records.</Alert></Box>
            <Box sx={{ px: 2.25, pt: 2 }}>
              <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800 }}>Step {activeIndex + 1} of {tourSteps.length}</Typography><Chip size="small" label={location.pathname === step.route ? 'You are here' : 'Guided step'} color={location.pathname === step.route ? 'success' : 'default'} /></Stack>
              <LinearProgress variant="determinate" value={progress} sx={{ mt: 1, height: 7, borderRadius: 99 }} />
            </Box>
            <Box sx={{ flex: 1, overflowY: 'auto', p: 2.25 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, bgcolor: 'action.hover' }}><Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}><MessageCircle size={19} aria-hidden="true" /><Box><Typography variant="h6" sx={{ fontWeight: 800 }}>{step.title}</Typography><Typography variant="body2" sx={{ mt: .75, fontWeight: 700 }}>{step.summary}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.65 }}>{step.detail}</Typography></Box></Stack><Button fullWidth variant="contained" endIcon={<ExternalLink size={16} />} onClick={() => navigate(step.route)} sx={{ mt: 2, textTransform: 'none', fontWeight: 800 }}>Open {step.title}</Button></Paper>
              <Typography variant="subtitle2" sx={{ mt: 2.5, mb: 1, fontWeight: 800 }}>Tour map</Typography>
              <Stack spacing={.75}>{tourSteps.map((tourStep, index) => <Button key={tourStep.route} variant={index === activeIndex ? 'contained' : 'text'} color={index === activeIndex ? 'primary' : 'inherit'} onClick={() => openStep(index)} sx={{ justifyContent: 'flex-start', textAlign: 'left', borderRadius: 2, minHeight: 40, py: .75, textTransform: 'none', fontSize: '.875rem' }} startIcon={index < activeIndex ? <CheckCircle2 size={16} /> : <Box component="span" sx={{ display: 'inline-grid', placeItems: 'center', width: 24, height: 24, borderRadius: '50%', bgcolor: index === activeIndex ? 'rgba(255,255,255,.18)' : 'action.selected', color: index === activeIndex ? 'inherit' : 'primary.main', fontSize: '.68rem', fontWeight: 800, letterSpacing: '.02em' }}>{String(index + 1).padStart(2, '0')}</Box>}>{tourStep.title}</Button>)}</Stack>
            </Box>
            <Divider />
            <Box component="form" onSubmit={submitQuestion} sx={{ p: 2.25 }}><Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>{reply}</Typography><TextField fullWidth size="small" label="Hello, how can I help?" value={question} onChange={(event) => setQuestion(event.target.value)} slotProps={{ input: { endAdornment: <IconButton type="submit" aria-label="Ask workflow assistant" edge="end" size="small"><Send size={17} /></IconButton> } }} /><Stack direction="row" spacing={1} sx={{ mt: 1.5, justifyContent: 'space-between' }}><Button size="small" startIcon={<ArrowLeft size={16} />} disabled={activeIndex === 0} onClick={() => openStep(activeIndex - 1)} sx={{ textTransform: 'none' }}>Previous</Button><Button size="small" endIcon={<ArrowRight size={16} />} disabled={activeIndex === tourSteps.length - 1} onClick={() => openStep(activeIndex + 1)} sx={{ textTransform: 'none' }}>Next step</Button></Stack></Box>
          </>
        ) : (
          <>
            <Box sx={{ px: 2.25, pt: 1.75 }}><Alert severity="info" sx={{ alignItems: 'flex-start' }}>Documentation-only answers. This assistant cannot approve, publish, assign, revoke, delete, create, edit, apply, or change records.</Alert></Box>
            <Box sx={{ flex: 1, overflowY: 'auto', p: 2.25 }}><Stack spacing={1.5}>{messages.map((message, index) => <Stack key={`${message.role}-${index}`} sx={{ alignItems: message.role === 'admin' ? 'flex-end' : 'flex-start' }}><Paper variant="outlined" sx={{ maxWidth: '92%', p: 1.5, borderRadius: 3, bgcolor: message.role === 'admin' ? 'primary.main' : 'action.hover', color: message.role === 'admin' ? 'primary.contrastText' : 'text.primary' }}><Typography variant="body2" sx={{ lineHeight: 1.6 }}>{message.text}</Typography>{message.source && <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: .78 }}>Source: {message.source}</Typography>}</Paper></Stack>)}</Stack></Box>
            <Divider />
            <Box component="form" onSubmit={submitQuestion} sx={{ p: 2.25 }}><TextField fullWidth size="small" label="Hello, how can I help?" value={question} onChange={(event) => setQuestion(event.target.value)} slotProps={{ input: { endAdornment: <IconButton type="submit" aria-label="Ask documentation assistant" edge="end" size="small"><Send size={17} /></IconButton> } }} /><Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>Ask about devices, policies, provisioning, synchronization, violations, audit, privacy, or operations.</Typography></Box>
          </>
        )}
      </Stack>
    </Drawer>
  </>
}
