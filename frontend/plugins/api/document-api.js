// plugins/api/document-api.js
export default defineNuxtPlugin((nuxtApp) => {
  const entity = '/documentmanager/document/'
  const provideName = 'DocumentApiService'

  const { $apiManager } = useNuxtApp()
  const apiHost = useRuntimeConfig().public.apiHost

  const getAll = (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== '')
    ).toString()
    return $apiManager.fetch(`${apiHost}${entity}${query ? `?${query}` : ''}`, 'GET')
  }

  const get = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/`, 'GET')

  const viewUrl = (id) => `${apiHost}${entity}${id}/view/`

  const getBlob = (id) => $apiManager.fetchBlob(viewUrl(id))

  const download = (id, filename) =>
    $apiManager.downloadFile(`${apiHost}${entity}${id}/download/`, filename)

  const remove = (id) => $apiManager.fetch(`${apiHost}${entity}${id}/delete/`, 'POST')

  nuxtApp.provide(provideName, { getAll, get, viewUrl, getBlob, download, remove })
})
