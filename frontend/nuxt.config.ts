export default defineNuxtConfig({
  devtools: { enabled: true },

  ssr: false,

  runtimeConfig: {
    public: {
      // URL del backend Django (sign360/backend)
      apiHost: process.env.NUXT_PUBLIC_API_HOST || 'http://localhost:8000',
      defaultLocale: process.env.LANGUAGE || 'ca',
      env: process.env.ENV || 'local',
    },
  },

  modules: ['@nuxtjs/i18n', '@nuxtjs/tailwindcss', '@pinia/nuxt', '@nuxt/icon'],

  icon: {
    serverBundle: {
      collections: ['fa6-solid', 'fa6-regular', 'mdi'],
    },
    clientBundle: {
      sizeLimitKb: 640,
    },
  },

  css: ['~/assets/css/main.css'],

  plugins: [
    '~/plugins/npm/toast.js',
    '~/plugins/api/api-manager.js',
    '~/plugins/api/document-api.js',
    '~/plugins/api/document-sign-api.js',
  ],

  i18n: {
    // Els fitxers d'i18n viuen a l'arrel (com a avsis-customers-frontend) i no
    // dins de `i18n/`, que és on els busca el mòdul per defecte.
    restructureDir: '.',
    vueI18n: './i18n.config.ts',
    // Explícit: el mòdul avisa que aquesta optimització s'elimina a la v10.
    bundle: { optimizeTranslationDirective: false },
  },

  app: {
    head: {
      title: 'Sign360',
      meta: [{ name: 'description', content: 'Gestió i signatura de documents' }],
    },
  },

  compatibilityDate: '2025-01-01',
})
