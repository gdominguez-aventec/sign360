import ca from './locales/ca'
import es from './locales/es'
import en from './locales/en'

export default defineI18nConfig(() => ({
  missingWarn: false,
  legacy: false,
  locale: 'ca',
  fallbackLocale: 'ca',
  messages: { ca, es, en },
}))
