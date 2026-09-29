export type Capability = { slug: string; title: string; summary: string; status: 'Implemented surface' | 'External verification required' }

export const capabilities: Capability[] = [
  { slug: 'offline-enforcement', title: 'Offline-first enforcement', summary: 'Keep policy decisions close to the managed Android device when connectivity cannot be assumed.', status: 'External verification required' },
  { slug: 'policy-management', title: 'Policy management', summary: 'Create, assign, acknowledge, and review phone-use policies from one administrator surface.', status: 'Implemented surface' },
  { slug: 'device-management', title: 'Device management', summary: 'Maintain visibility into school-owned Android devices, check-ins, and operational status.', status: 'Implemented surface' },
  { slug: 'audit-and-forensics', title: 'Audit and forensics', summary: 'Review security-relevant events and the evidence boundaries of the proof-of-concept.', status: 'Implemented surface' },
  { slug: 'security', title: 'Security by design', summary: 'Use protected routes, authorization, secure identity, and privacy-limited evidence as foundations.', status: 'Implemented surface' },
]

export const navGroups = [
  { label: 'Product', links: [['Product overview', '/product'], ['How it works', '/how-it-works'], ['Architecture', '/architecture']] },
  { label: 'Capabilities', links: capabilities.map(({ title, slug }) => [title, `/features/${slug}`]) },
  { label: 'Context', links: [['For schools', '/schools'], ['Security', '/security'], ['About the PoC', '/about']] },
  { label: 'Resources', links: [['Resources', '/resources'], ['News', '/news'], ['Contact', '/contact']] },
] as const
