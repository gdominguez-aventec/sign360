export default defineNuxtConfig({
  devtools: { enabled: true },

  ssr: false,

  // Nuxt 4 posa el codi de l'aplicació dins d'`app/`. Aquí es manté a l'arrel,
  // com a `avsis-customers-frontend`, perquè les dues bases de codi es puguin
  // llegir igual.
  srcDir: '.',

  runtimeConfig: {
    public: {
      // URL del backend Django (backend/)
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
    // L'idioma no va a l'URL: es tria en temps d'execució (LANGUAGE), i és el
    // que ja feia el mòdul quan no hi havia cap `locales` declarat.
    strategy: 'no_prefix',
    defaultLocale: 'ca',
    locales: [
      { code: 'ca', language: 'ca-ES' },
      { code: 'es', language: 'es-ES' },
      { code: 'en', language: 'en-GB' },
    ],
  },

  app: {
    head: {
      title: 'app.aqua360-sign',
      meta: [{ name: 'description', content: 'Gestió i signatura de documents' }],
    },
  },

  compatibilityDate: '2025-01-01',
})
