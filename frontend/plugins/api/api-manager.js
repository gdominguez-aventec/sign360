// plugins/api/api-manager.js
// Únic punt de sortida cap al backend: hi afegeix el token, converteix els
// errors en missatges llegibles i, si la sessió ha caducat, torna al login.
import { defineNuxtPlugin } from '#app'
import { useToast } from 'vue-toastification'

export default defineNuxtPlugin((nuxtApp) => {
  const toast = useToast()

  // Evita una pluja de toasts si diverses peticions fallen alhora amb 401
  let last401ToastTime = 0

  const extractMessage = (error) => {
    const data = error?.response?._data ?? error?.data ?? null

    const direct =
      data?.message || data?.error || data?.detail || error?.message || null
    if (direct) return direct

    // Errors de validació per camp: {"file": ["..."], "otp_email": ["..."]}
    if (data && typeof data === 'object') {
      return Object.values(data)
        .map((value) => (Array.isArray(value) ? value.join(', ') : value))
        .join(' | ')
    }

    return 'S\'ha produït un error inesperat.'
  }

  const apiService = {
    getToken() {
      if (!process.client) return ''
      return localStorage.getItem('auth_token') || ''
    },

    buildHeaders(extra = null) {
      const token = this.getToken()
      return {
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...extra,
      }
    },

    async fetch(url, method, body = null, headers = null, suppressToast = false) {
      const options = {
        method,
        headers: this.buildHeaders(headers),
      }
      if (body != null) options.body = body

      try {
        return await $fetch(url, options)
      } catch (error) {
        const message = extractMessage(error)
        const status = error?.response?.status ?? error?.status ?? null

        if (status === 401) {
          const now = Date.now()
          if (now - last401ToastTime > 2000) {
            toast.error(message)
            last401ToastTime = now
          }
          if (process.client) localStorage.removeItem('auth_token')
          nuxtApp.$router.push('/auth/login')
        } else if (!suppressToast) {
          toast.error(message)
        }

        throw error
      }
    },

    // Descàrregues i visualització de PDF: cal el blob, no JSON, i el token ha
    // de viatjar a la capçalera (els <iframe>/<a> no la poden posar).
    async fetchBlob(url) {
      const response = await fetch(url, { headers: this.buildHeaders() })
      if (!response.ok) {
        if (response.status === 401) {
          if (process.client) localStorage.removeItem('auth_token')
          nuxtApp.$router.push('/auth/login')
        }
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.blob()
    },

    async downloadFile(url, filename) {
      const blob = await this.fetchBlob(url)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename || 'document.pdf'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)
    },
  }

  nuxtApp.provide('apiManager', apiService)
})
