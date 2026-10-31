import { edugdQaSource } from 'virtual:edugd-qa-source'

export type AssistantKnowledgeArticle = {
  id: string
  title: string
  source: string
  keywords: string[]
  answer: string
}

/**
 * Small, curated documentation index for the in-dashboard helper.
 *
 * This intentionally contains no live records and no action handlers. The
 * assistant can explain documented workflows, but it cannot make decisions
 * or change administrative state.
 */
const curatedAssistantKnowledge: AssistantKnowledgeArticle[] = [
  {
    id: 'devices',
    title: 'Device records',
    source: 'Dashboard documentation · Device records',
    keywords: ['device', 'devices', 'phone', 'tablet', 'pixel', 'enrolled', 'compliant'],
    answer: 'Device records show the human-facing reference, Android details, enrollment, assigned policy, synchronization state, compliance, and privacy-safe evidence. Device identity is supplied by the managed Android device rather than typed into the dashboard.',
  },
  {
    id: 'policies',
    title: 'Policy builder',
    source: 'Dashboard documentation · Policy management',
    keywords: ['policy', 'policies', 'blocked', 'approved', 'restriction', 'schedule', 'offline'],
    answer: 'The policy builder defines approved and blocked applications, device restrictions, network controls, schedules, compliance checks, and offline behaviour. Review the plain-language preview before saving a revision.',
  },
  {
    id: 'catalogue',
    title: 'Application catalogue',
    source: 'Dashboard documentation · Applications and domains',
    keywords: ['application', 'applications', 'app', 'domain', 'catalogue', 'catalog', 'enabled', 'disabled'],
    answer: 'Enabled catalogue entries are available for new policy selections. Disabled entries are retained for history and existing signed policies, but are unavailable when creating new policy rules.',
  },
  {
    id: 'provisioning',
    title: 'Provisioning',
    source: 'Dashboard documentation · Device enrollment',
    keywords: ['provision', 'provisioning', 'enrollment', 'enrol', 'qr', 'token', 'onboarding'],
    answer: 'Provisioning is used to issue enrollment credentials and complete Android device onboarding. The device record is created from the Android device-owner flow; administrators do not manually enter device identity details.',
  },
  {
    id: 'synchronization',
    title: 'Synchronization queue',
    source: 'Dashboard documentation · Synchronization',
    keywords: ['sync', 'synchronization', 'synchronisation', 'queue', 'command', 'acknowledge', 'acknowledgement'],
    answer: 'The synchronization queue records command delivery and device acknowledgement. Pending, sent, applied, and failed states remain reviewable so an administrator can understand whether a policy reached the enrolled device.',
  },
  {
    id: 'violations',
    title: 'Violations and incidents',
    source: 'Dashboard documentation · Enforcement evidence',
    keywords: ['violation', 'violations', 'incident', 'incidents', 'enforcement', 'hash', 'evidence'],
    answer: 'Violations and incidents are reviewed by device, class, and period. Event hashes and sequences support traceable review while keeping learner content outside the evidence record.',
  },
  {
    id: 'audit',
    title: 'Audit logs',
    source: 'Dashboard documentation · Audit and forensics',
    keywords: ['audit', 'audits', 'log', 'logs', 'history', 'event type', 'forensics'],
    answer: 'Audit logs provide the accountable administrative record. Use the event-type filter to review authentication, enrollment, assignment, synchronization, asset, incident, and violation activity.',
  },
  {
    id: 'privacy',
    title: 'Privacy boundaries',
    source: 'Dashboard documentation · Privacy and security',
    keywords: ['privacy', 'private', 'messages', 'photos', 'contacts', 'location', 'microphone', 'content'],
    answer: 'The documented evidence boundary is privacy-limited: the system records policy and device-control evidence, not private messages, photos, contacts, location history, microphone recordings, or learner content.',
  },
  {
    id: 'operations',
    title: 'Operations overview',
    source: 'Dashboard documentation · Operations overview',
    keywords: ['operations', 'overview', 'workflow', 'complete', 'where do i start', 'start'],
    answer: 'The operations overview connects the workflow: school profile, devices, applications and domains, policies, assignments, provisioning, enforcement, synchronization, violations, incidents, and audit logs.',
  },
  {
    id: 'architecture',
    title: 'System architecture',
    source: 'Repository documentation - Architecture and security decisions',
    keywords: ['architecture', 'system', 'components', 'microservices', 'backend', 'frontend', 'android', 'dpc', 'services'],
    answer: 'The codebase is organised around the administrator frontend, the Flask API and service layer, the Android device-policy controller, persistent policy and audit data, and the synchronization boundary between the server and enrolled devices. The dashboard is the administrative surface; enforcement remains on the managed Android device.',
  },
  {
    id: 'repository',
    title: 'Repository structure',
    source: 'Repository documentation - Project README',
    keywords: ['repository', 'repo', 'codebase', 'folder', 'folders', 'structure', 'source code'],
    answer: 'The repository separates Android DPC code, backend API and services, frontend administration pages and components, backend documentation, frontend documentation, tests, and local-stack tooling. The frontend uses route-level pages while shared layout, authentication, services, schemas, and types remain reusable.',
  },
  {
    id: 'local-stack',
    title: 'Local stack and isolation',
    source: 'Repository documentation - Disposable local Flask and Vite stack',
    keywords: ['local stack', 'local', 'vite', 'flask', 'docker', 'compose', 'staging', 'production', 'isolated'],
    answer: 'The local stack runs the Flask backend and Vite frontend with isolated local support services. Its documented safety boundary keeps PostgreSQL on loopback, uses a unique local Compose project, and avoids hosted database URLs, provider tokens, Redis credentials, and Sentry credentials.',
  },
  {
    id: 'authentication',
    title: 'Administrator authentication',
    source: 'Repository documentation - Administrator authentication and authorization design',
    keywords: ['authentication', 'login', 'session', 'password', 'jwt', 'credential', 'timeout', 'logout'],
    answer: 'Privileged administration requires a named administrator session. The design supports active, disabled, and locked account states, permission checks on each operation, password verifiers instead of plaintext passwords, session expiry, revocation, rate limiting, and redacted authentication audit events.',
  },
  {
    id: 'permissions',
    title: 'Permissions and authorization',
    source: 'Repository documentation - Administrator authentication and authorization design',
    keywords: ['permission', 'permissions', 'authorization', 'rbac', 'role', 'administrator.manage', 'policy.manage'],
    answer: 'Authorization is database-authoritative and operation-specific. Examples include managing administrators, issuing or revoking enrollment credentials, assigning policies, controlling devices, and managing policy revisions. A valid login alone does not grant every operation.',
  },
  {
    id: 'device-lifecycle',
    title: 'Device identity and lifecycle',
    source: 'Repository documentation - Architecture and security decisions',
    keywords: ['device identity', 'uuid', 'canonical', 'reference', 'active', 'suspended', 'retired', 'android version', 'api level'],
    answer: 'The Android DPC creates and securely persists the canonical device identity. The system tracks active, suspended, and retired lifecycle states, stores Android version and API level, and keeps short human-facing references separate from canonical identifiers used internally.',
  },
  {
    id: 'enrollment',
    title: 'Enrollment and provisioning security',
    source: 'Repository documentation - Device enrollment authentication design',
    keywords: ['enrollment security', 'pairing', 'pairing token', 'device credential', 'single use', 'ten minute', 'enroll device'],
    answer: 'Enrollment uses a short-lived, single-use, school-issued pairing credential. Successful enrollment creates a separate revocable device credential. The detailed design uses a ten-minute pairing lifetime and protects later device requests with signed canonical requests.',
  },
  {
    id: 'policy-lifecycle',
    title: 'Policy lifecycle and revisions',
    source: 'Repository documentation - Immutable policy revision design',
    keywords: ['policy lifecycle', 'draft', 'active', 'inactive', 'revoked', 'revision', 'immutable', 'rollback', 'clear assignment'],
    answer: 'A policy keeps a stable identity while each revision is immutable. Policy lifecycle states are draft, active, inactive, and revoked. Assignments point to an exact revision, and clearing or deliberately applying an older revision is recorded as a distinct operation rather than inferred from a version number alone.',
  },
  {
    id: 'policy-validation',
    title: 'Policy validation and preview',
    source: 'Repository documentation - Policy administration API and frontend contract coverage',
    keywords: ['validate policy', 'invalid policy', 'policy validation', 'preview policy', 'canonical', 'server validates', 'constraints'],
    answer: 'The policy form is a structured authoring surface, not the final authority. It checks required fields and relationships locally, shows a plain-language preview, then sends the structured payload for server-side canonical validation before a revision is created. A request can therefore be rejected even when one visible field looks valid if the complete payload or capability constraints are inconsistent.',
  },
  {
    id: 'dpc-protocol',
    title: 'Android DPC protocol',
    source: 'Repository documentation - DPC policy protocol v2 and v3 foundation',
    keywords: ['dpc protocol', 'protocol', 'api 29', 'api 35', 'android 10', 'android 15', 'capability', 'fail closed'],
    answer: 'The documented compatibility boundary supports Android 10 through 15 and API levels 29 through 35 for live DPC builds. The DPC advertises capabilities during enrollment, and the server must not activate a policy requiring capabilities the device does not report.',
  },
  {
    id: 'sync-contract',
    title: 'Synchronization contract',
    source: 'Repository documentation - Policy synchronization v1 contract',
    keywords: ['apply', 'no change', 'no_change', 'clear', 'rollback', 'blocked', 'sync operation', 'synchronization contract'],
    answer: 'Synchronization explicitly distinguishes apply, no_change, clear, rollback, and blocked outcomes. Apply enforces the exact returned revision; no_change keeps the matching state; clear removes a policy; rollback intentionally applies an older revision; blocked stops normal synchronization without changing local policy state.',
  },
  {
    id: 'audit-forensics',
    title: 'Audit and forensic evidence',
    source: 'Repository documentation - Architecture, audit, and forensics decisions',
    keywords: ['forensic', 'forensics', 'append only', 'immutable audit', 'chain', 'event sequence', 'redaction', 'audit evidence'],
    answer: 'Administrative, enrollment, assignment, synchronization, violation, and device-control events are retained as accountable evidence. Sensitive credentials, passwords, authorization headers, pairing tokens, request bodies, and raw source addresses are excluded or redacted from audit and application logs.',
  },
  {
    id: 'health-readiness',
    title: 'Health and readiness',
    source: 'Repository documentation - Architecture and security decisions',
    keywords: ['health', 'readiness', 'ready', 'liveness', 'dependency', 'api status'],
    answer: 'Health indicates process liveness, while readiness performs bounded checks of essential configuration and database dependencies. The dashboard can show both signals so an administrator can distinguish a running process from a service ready for authenticated administration.',
  },
  {
    id: 'data-protection',
    title: 'Data protection and retention',
    source: 'Repository documentation - Data protection and retention controls',
    keywords: ['data protection', 'retention', 'data minimisation', 'asset number', 'learner', 'surveillance', 'personal data'],
    answer: 'The documented data-minimisation boundary uses school asset numbers, device UUIDs, class or department assignments, device-management evidence, policy versions, synchronization time, and compliance results. It excludes learner photographs, private content, health information, family information, location history, microphone recordings, and browsing history.',
  },
  {
    id: 'frontend-workflows',
    title: 'Frontend workflow map',
    source: 'Repository documentation - EduGD administrator frontend README',
    keywords: ['frontend workflow', 'page', 'pages', 'dashboard route', 'device list', 'policy list', 'audit-event list', 'error'],
    answer: 'The administrator frontend covers login, device list and detail, policy list and immutable revision history, assignments, provisioning tokens, applications and domains, synchronization, violations, incidents, audit filtering, structured API errors, pagination, retry actions, and data-protection settings.',
  },
  {
    id: 'testing-quality',
    title: 'Testing and quality gates',
    source: 'Repository documentation - Quality baseline and frontend README',
    keywords: ['test', 'tests', 'testing', 'quality', 'lint', 'typecheck', 'build', 'coverage', 'verification'],
    answer: 'The repository documents automated quality gates for formatting, linting, type checking, coverage, dependency auditing, security scanning, frontend verification, and end-to-end workflow checks. Changes should be validated at the smallest affected layer and then with the complete relevant suite.',
  },
  {
    id: 'translations',
    title: 'Translations',
    source: 'Repository documentation - Translation integration',
    keywords: ['translation', 'translations', 'language', 'localization', 'localisation'],
    answer: 'Translations are a separate administration workflow in the frontend. Language selection belongs to the presentation layer and should not change policy payloads, device identity, enforcement state, or audit semantics.',
  },
  {
    id: 'dashboard-metrics',
    title: 'Dashboard metrics',
    source: 'Repository implementation - Dashboard page and administrator read services',
    keywords: ['dashboard metrics', 'registered devices', 'enrolled devices', 'compliant devices', 'pending commands', 'device count', 'metric'],
    answer: 'Dashboard device counts are derived from authenticated device records and their reported state. Registered, enrolled, compliant, non-compliant, offline-review, missing, pending-command, and violation totals describe different signals and should not be treated as interchangeable.',
  },
  {
    id: 'manual-refresh',
    title: 'Refresh behaviour',
    source: 'Repository implementation - Dashboard and operations pages',
    keywords: ['refresh', 'auto refresh', 'automatic refresh', 'reload', 'live update', 'display update'],
    answer: 'The dashboard and operations views update their displayed data when the administrator requests a refresh or when a completed action invalidates the affected record. The interface does not continuously replace the visible review state on a timer.',
  },
  {
    id: 'application-status',
    title: 'Application and domain status',
    source: 'Repository implementation - Managed applications and policy catalogue',
    keywords: ['application status', 'domain status', 'enabled status', 'disabled status', 'catalogue status', 'new policy selection'],
    answer: 'Enabled applications and domains can be selected for new policy rules. Disabled catalogue entries remain visible where historical or existing signed-policy context requires them, but they are not offered as new selectable controls.',
  },
  {
    id: 'qr-provisioning',
    title: 'QR provisioning troubleshooting',
    source: 'Repository implementation - Android provisioning QR dialog',
    keywords: ['qr code', 'qr provisioning', 'invalid url', 'invalid URL', 'construct URL', 'provisioning link'],
    answer: 'QR provisioning requires a valid absolute enrollment endpoint and a complete pairing payload. An Invalid URL error normally means the configured base or enrollment endpoint is missing, malformed, or not absolute; the safe fix is to correct the local API origin/configuration and regenerate the QR payload rather than typing a device identity manually.',
  },
  {
    id: 'enforcement-center',
    title: 'Enforcement center',
    source: 'Repository implementation - Enforcement center page',
    keywords: ['enforcement center', 'enforcement page', 'control center', 'operational shortcuts'],
    answer: 'The enforcement center is an operational hub that links to the existing policy, device, catalogue, synchronization, violation, and audit workflows. It does not replace those pages or create a second copy of their records.',
  },
  {
    id: 'violations-review',
    title: 'Violation review',
    source: 'Repository implementation - Violation reports and audit logs',
    keywords: ['review violations', 'violation filter', 'violation page', 'hashes', 'next page', 'previous page', 'pagination'],
    answer: 'Violation review is paginated and can be filtered by the administrator. Event hashes, sequences, device references, dates, and policy context support review; they are evidence identifiers, not learner-content records.',
  },
  {
    id: 'mobile-responsive',
    title: 'Responsive administration',
    source: 'Repository implementation - Admin shell and responsive page styles',
    keywords: ['mobile', 'responsive', 'desktop', 'screen size', 'zoom', 'small screen', 'layout'],
    answer: 'The admin shell uses responsive navigation and fluid content widths. Forms and assistant panels should remain readable at mobile and desktop widths, with controls wrapping or stacking rather than requiring browser zoom.',
  },
  {
    id: 'assistant-limits',
    title: 'Assistant boundaries',
    source: 'Dashboard documentation · Assistant scope',
    keywords: ['assistant', 'help', 'question', 'questions', 'can you', 'capability', 'capabilities'],
    answer: 'This helper answers quick questions from the curated dashboard documentation only. It cannot approve, publish, assign, revoke, delete, create, edit, apply, or otherwise change records, and it is not an authoritative decision-maker.',
  },
]

const ignoredQuestionWords = new Set([
  'a', 'an', 'and', 'are', 'can', 'does', 'how', 'is', 'it', 'of', 'on',
  'or', 'the', 'to', 'what', 'when', 'where', 'who', 'why', 'with',
])

function normalise(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9\s]/g, ' ')
}

function parseAttachedQuestionAnswers(markdown: string): AssistantKnowledgeArticle[] {
  const lines = markdown.split(/\r?\n/)
  const articles: AssistantKnowledgeArticle[] = []
  let section = 'EduGD reference'
  let current: { number: string; question: string; answer: string[]; section: string } | null = null

  function commit() {
    if (!current) return
    const answer = current.answer.join(' ').replace(/\s+/g, ' ').trim()
    if (!answer) return
    const questionWords = normalise(current.question)
      .split(/\s+/)
      .filter((word) => word.length > 2 && !ignoredQuestionWords.has(word))
    articles.push({
      id: `edugd-qa-${current.number}`,
      title: current.question,
      source: `EduGD reference · ${current.section} · Question ${current.number}`,
      keywords: [...new Set([current.question, ...questionWords])],
      answer,
    })
  }

  for (const line of lines) {
    const sectionMatch = /^##\s+(.+?)\s*$/.exec(line)
    if (sectionMatch) {
      section = sectionMatch[1]
      continue
    }
    if (/^###\s+/.test(line)) continue
    const questionMatch = /^(\d+)\.\s+\*\*(.+?)\*\*\s*$/.exec(line)
    if (questionMatch) {
      commit()
      current = { number: questionMatch[1], question: questionMatch[2], answer: [], section }
      continue
    }
    if (current) current.answer.push(line)
  }
  commit()
  return articles
}

/**
 * Only numbered Q&A pairs are imported from the attached reference. Markdown
 * headings, prose, and imperative text outside those pairs are not executed
 * or treated as assistant instructions.
 */
const attachedQuestionAnswers = parseAttachedQuestionAnswers(edugdQaSource)
export const assistantKnowledge: AssistantKnowledgeArticle[] = [
  ...curatedAssistantKnowledge,
  ...attachedQuestionAnswers,
]

export function answerDocumentationQuestion(question: string) {
  const normalizedQuestion = normalise(question)
  if (!normalizedQuestion) return null

  const words = new Set(normalizedQuestion.split(/\s+/).filter(Boolean))
  const ranked = assistantKnowledge
    .map((article) => ({
      article,
      score: article.keywords.reduce((score, keyword) => {
        const normalizedKeyword = normalise(keyword)
        return score + (normalizedQuestion.includes(normalizedKeyword) || words.has(normalizedKeyword) ? 1 : 0)
      }, 0),
    }))
    .sort((left, right) => right.score - left.score)

  const best = ranked[0]
  if (!best || best.score === 0) return null
  return best.article
}
