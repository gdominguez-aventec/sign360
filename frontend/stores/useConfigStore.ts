import { defineStore } from 'pinia'

/**
 * Configuració que publica el backend a `/documentmanager/config/`.
 *
 * Es llegeix del servidor i no d'una variable d'entorn del frontal perquè hi
 * hagi una sola font de veritat: qui valida què es pot fer és el backend.
 */
export const useConfigStore = defineStore('config', () => {
  const multiSignerEnabled = ref(false)
  const maxUploadSize = ref(20 * 1024 * 1024)
  const signingProviderConfigured = ref(false)
  const loaded = ref(false)

  const load = async (force = false) => {
    if (loaded.value && !force) return
    const { $apiManager } = useNuxtApp()
    const apiHost = useRuntimeConfig().public.apiHost
    try {
      const response = await $apiManager.fetch(`${apiHost}/documentmanager/config/`, 'GET')
      multiSignerEnabled.value = Boolean(response.multi_signer_enabled)
      maxUploadSize.value = response.max_upload_size ?? maxUploadSize.value
      signingProviderConfigured.value = Boolean(response.signing_provider_configured)
      loaded.value = true
    } catch {
      // Si no es pot llegir, es queda amb els valors per defecte (els més
      // restrictius): el backend torna a validar-ho igualment.
    }
  }

  return { multiSignerEnabled, maxUploadSize, signingProviderConfigured, loaded, load }
})
