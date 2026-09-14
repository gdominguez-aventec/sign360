// plugins/api/document-sign-api.js
export default defineNuxtPlugin((nuxtApp) => {
  const entity = '/documentmanager/document-sign/'
  const provideName = 'DocumentSignApiService'

  const { $apiManager } = useNuxtApp()
  const apiHost = useRuntimeConfig().public.apiHost

  const getAll = (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== '')
    ).toString()
    return $apiManager.fetch(`${apiHost}${entity}${query ? `?${query}` : ''}`, 'GET')
  }

  const get = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/`, 'GET')

  // L'alta va com a multipart perquè hi viatja el PDF: no s'hi posa
  // Content-Type a mà, el navegador hi ha d'afegir el boundary.
  const create = ({ file, title, description, otpName, otpEmail, otpPhone, sendNow }) => {
    const body = new FormData()
    body.append('file', file)
    if (title) body.append('title', title)
    if (description) body.append('description', description)
    body.append('otp_name', otpName)
    body.append('otp_email', otpEmail)
    if (otpPhone) body.append('otp_phone', otpPhone)
    body.append('send_now', sendNow ? 'true' : 'false')

    return $apiManager.fetch(`${apiHost}${entity}`, 'POST', body)
  }

  const sendToSign = (id, payload = {}) =>
    $apiManager.fetch(`${apiHost}${entity}${id}/send-to-sign/`, 'POST', payload, {
      'Content-Type': 'application/json',
    })

  const viewUrl = (id) => `${apiHost}${entity}${id}/view/`

  const getBlob = (id) => $apiManager.fetchBlob(viewUrl(id))

  const download = (id, filename) =>
    $apiManager.downloadFile(`${apiHost}${entity}${id}/download/`, filename)

  const downloadOriginal = (id, filename) =>
    $apiManager.downloadFile(`${apiHost}${entity}${id}/download-original/`, filename)

  const remove = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/`, 'DELETE')

  nuxtApp.provide(provideName, {
    getAll,
    get,
    create,
    sendToSign,
    viewUrl,
    getBlob,
    download,
    downloadOriginal,
    remove,
  })
})
