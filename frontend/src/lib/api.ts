const configuredApiUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const developmentApiUrl = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''
const productionApiUrl = 'https://ai-career-intelligence-7x5r.onrender.com'

export const API_BASE_URL = (
  configuredApiUrl || developmentApiUrl || productionApiUrl
).replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status?: number

  constructor(
    message: string,
    status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  token?: string
  method?: string
  body?: BodyInit
  json?: unknown
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' })
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)

  let body = options.body
  if (options.json !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.json)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
      credentials: 'omit',
    })
  } catch {
    throw new ApiError(
      `Could not connect to the API at ${API_BASE_URL}. Check the backend status, network, and CORS configuration.`,
    )
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiError(
      response.ok
        ? 'The API returned an invalid response. Please try again.'
        : `The API request failed (${response.status}) and returned an invalid error response.`,
      response.status,
    )
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`
    if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
      const detail = payload.detail
      if (typeof detail === 'string') {
        message = detail
      } else if (Array.isArray(detail)) {
        message = detail
          .map((item) => typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : '')
          .filter(Boolean)
          .join(' ')
        if (!message) message = `Request validation failed (${response.status}).`
      }
    }
    throw new ApiError(message, response.status)
  }

  return payload as T
}
