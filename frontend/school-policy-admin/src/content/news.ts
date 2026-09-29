export type NewsSource = {
  id: string
  headline: string
  sourceUrl: string
  sourceName: string
  imageUrl: string | null
  imageAlt: string
}

// Source-hosted image URLs are intentionally null until individually verified.
// The page uses the approved local fallback instead of inventing or copying an image.
export const newsSources: NewsSource[] = [
  { id: 'education-digital-agenda', headline: 'Uganda Education Digital Agenda 2021-2025', sourceUrl: 'https://www.scribd.com/presentation/841065961/4-Ben-Mugisha-MoES-Digital-Agenda-Strategy', sourceName: 'Scribd', imageUrl: null, imageAlt: 'Uganda Education Digital Agenda 2021-2025 source preview' },
  { id: 'mobile-devices-guidelines', headline: "Don't Rush to Accept Mobile Devices Before Guidelines Are Out - Ministry of Education", sourceUrl: 'https://ugandaradionetwork.net/story/dont-rush-to-accept-mobile-devices-before-guidelines-are-out-ministry-of-education-1', sourceName: 'Uganda Radio Network', imageUrl: null, imageAlt: 'Uganda Radio Network source preview' },
  { id: 'upstu-digital-agenda', headline: 'On MoES Digital Agenda Strategy and Students Bringing Mobile Devices to School', sourceUrl: 'https://upstu.org/on-moes-digital-agenda-strategy-and-students-bringing-mobile-devices-to-school/', sourceName: 'UPSTU', imageUrl: null, imageAlt: 'UPSTU source preview' },
  { id: 'moes-digital-agenda', headline: 'Digital Agenda', sourceUrl: 'https://www.education.go.ug/digital-agenda/', sourceName: 'Ministry of Education and Sports', imageUrl: null, imageAlt: 'Ministry of Education and Sports source preview' },
  { id: 'ubc-mobile-devices', headline: 'Clarification on Mobile Digital Devices in Schools', sourceUrl: 'https://ubc.go.ug/2024/09/09/clarification-on-mobile-digital-devices-in-schools/', sourceName: 'UBC', imageUrl: null, imageAlt: 'UBC source preview' },
  { id: 'independent-mobile-devices', headline: 'Education Minister Janet Museveni Okays Mobile Devices in Schools', sourceUrl: 'https://www.independent.co.ug/education-minister-janet-museveni-okays-mobile-devices-in-schools/?utm_source=gemini', sourceName: 'The Independent', imageUrl: null, imageAlt: 'The Independent source preview' },
  { id: 'ugbulletin-mobile-phones', headline: 'Education Ministry Permits Mobile Phones in Schools, Emphasizes Student Safety and Monitoring', sourceUrl: 'https://www.ugbulletin.co.ug/education-ministry-permits-mobile-phones-in-schools-emphasizes-student-safety-and-monitoring/?utm_source=gemini', sourceName: 'Uganda Bulletin', imageUrl: null, imageAlt: 'Uganda Bulletin source preview' },
  { id: 'newvision-mobile-phones', headline: 'Ministry of Education Bans Mobile Phones in Schools', sourceUrl: 'https://www.newvision.co.ug/news/1331237/ministry-education-bans-mobile-phones-schools?utm_source=gemini', sourceName: 'New Vision', imageUrl: null, imageAlt: 'New Vision source preview' },
  { id: 'digital-transformation-roadmap', headline: 'Digital Transformation Roadmap', sourceUrl: 'https://ict.go.ug/site/documents/Digital%20Transformation%20Roadmap.pdf', sourceName: 'Ministry of ICT and National Guidance', imageUrl: null, imageAlt: 'Digital Transformation Roadmap source preview' },
]
