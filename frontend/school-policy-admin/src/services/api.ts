import axios from 'axios'
import { resolveApiBaseUrl } from '../lib/environment'

const api = axios.create({
  baseURL: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD),
})

export default api

