let accessToken: string | null = null
let expiresAt = 0

export function setSessionToken(token: string, expiresInSeconds: number) {
  accessToken = token
  expiresAt = Date.now() + expiresInSeconds * 1000
}

export function getSessionToken() {
  if (accessToken && Date.now() >= expiresAt) clearSessionToken()
  return accessToken
}

export function getSessionExpiry() {
  return expiresAt
}

export function clearSessionToken() {
  accessToken = null
  expiresAt = 0
}
