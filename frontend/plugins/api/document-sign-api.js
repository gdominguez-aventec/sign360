// plugins/api/document-sign-api.js
export default defineNuxtPlugin((nuxtApp) => {
  const entity = '/documentmanager/document-sign/'
  const documentEntity = '/documentmanager/sign-document/'
  const provideName = 'DocumentSignApiService'

  const { $apiManager } = useNuxtApp()
  const apiHost = useRuntimeConfig().public.apiHost

  const buildQuery = (params = {}) =>
    new URLSearchParams(
      Object.entries(params).filter(
        ([, value]) => value !== null && value !== undefined && value !== ''
      )
    ).toString()

  const getAll = (params = {}) => {
    const query = buildQuery(params)
    return $apiManager.fetch(`${apiHost}${entity}${query ? `?${query}` : ''}`, 'GET')
  }

  const get = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/`, 'GET')

  // L'alta va com a multipart perquè hi viatgen els PDF: no s'hi posa
  // Content-Type a mà, el navegador hi ha d'afegir el boundary. Els signants
  // van com a JSON dins d'un camp de text, perquè un multipart no admet
  // estructures niuades.
  const create = ({ files, title, description, signers, sendNow }) => {
    const body = new FormData()
    files.forEach((file) => body.append('files', file))
    if (title) body.append('title', title)
    if (description) body.append('description', description)
    body.append('signers', JSON.stringify(signers))
    body.append('send_now', sendNow ? 'true' : 'false')

    return $apiManager.fetch(`${apiHost}${entity}`, 'POST', body)
  }

  // Sense `signer`, el backend envia al següent de la cadena que no ha firmat.
  const sendToSign = (id, payload = {}) =>
    $apiManager.fetch(`${apiHost}${entity}${id}/send-to-sign/`, 'POST', payload, {
      'Content-Type': 'application/json',
    })

  const remove = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/`, 'DELETE')

  // --- Documents concrets dins d'una sol·licitud ---

  const documentBlob = (signDocumentId, { original = false } = {}) =>
    $apiManager.fetchBlob(
      `${apiHost}${documentEntity}${signDocumentId}/${original ? 'view-original' : 'view'}/`
    )

  const downloadDocument = (signDocumentId, filename, { original = false } = {}) =>
    $apiManager.downloadFile(
      `${apiHost}${documentEntity}${signDocumentId}/${original ? 'download-original' : 'download'}/`,
      filename
    )

  // Qualsevol versió intermèdia de la cadena, per id de Document
  const versionBlob = (documentId) =>
    $apiManager.fetchBlob(`${apiHost}/documentmanager/document/${documentId}/view/`)

  const downloadVersion = (documentId, filename) =>
    $apiManager.downloadFile(
      `${apiHost}/documentmanager/document/${documentId}/download/`,
      filename
    )

  nuxtApp.provide(provideName, {
    getAll,
    get,
    create,
    sendToSign,
    remove,
    documentBlob,
    downloadDocument,
    versionBlob,
    downloadVersion,
  })
})
