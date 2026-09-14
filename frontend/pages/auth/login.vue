<script setup>
const { t, locale } = useI18n()

definePageMeta({ layout: 'auth' })

const config = useRuntimeConfig()
const apiHost = config.public.apiHost

const username = ref('')
const password = ref('')
const error_message = ref('')
const error_type = ref('error') // 'error' | 'warning' | 'connection'
const loading = ref(false)

const router = useRouter()
const route = useRoute()

/**
 * Codis que retorna el backend (`CustomAuthToken`):
 *   200 → login correcte (username + token)
 *   400 → credencials incorrectes, camps buits o usuari inactiu
 */
const resolveLoginError = (err) => {
  const status = err?.status ?? err?.response?.status ?? null

  if (status === 400) {
    const data = err?.data ?? err?.response?._data ?? {}

    if (
      String(data?.non_field_errors ?? '').toLowerCase().includes('inactive') ||
      String(data?.detail ?? '').toLowerCase().includes('inactive')
    ) {
      error_type.value = 'warning'
      return t('login.inactive_user')
    }

    if (data?.username?.length > 0 || data?.password?.length > 0) {
      error_type.value = 'warning'
      return t('login.empty_fields')
    }

    error_type.value = 'warning'
    return t('login.wrong')
  }

  if (!status) {
    error_type.value = 'connection'
    return t('login.fail')
  }

  error_type.value = 'error'
  return t('login.server_error')
}

const login = async () => {
  loading.value = true
  error_message.value = ''
  error_type.value = 'error'

  try {
    const response = await $fetch(apiHost + '/auth/login/', {
      method: 'POST',
      body: { username: username.value, password: password.value },
    })

    localStorage.setItem('auth_token', response.token)
    localStorage.setItem('user_username', response.username)

    // Només rutes internes: una sola barra inicial, per no convertir el login
    // en un redirector obert.
    const redirect = route.query.redirect
    const isInternal = typeof redirect === 'string' && /^\/(?!\/)/.test(redirect)
    router.push(isInternal ? redirect : '/signs')
  } catch (error) {
    error_message.value = resolveLoginError(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  locale.value = config.public.defaultLocale || 'ca'
})
</script>

<template>
  <div class="w-full max-w-sm px-6 py-12">
    <h2 class="text-center text-2xl font-bold leading-9 tracking-tight text-gray-900">
      {{ $t('login.title') }}
    </h2>
    <p class="mt-1 text-center text-gray-500">{{ $t('app.subtitle') }}</p>

    <div class="mt-10">
      <div
        v-if="error_message"
        role="alert"
        class="flex items-start gap-3 px-4 py-3 rounded-lg border mb-4"
        :class="{
          'bg-red-50 border-red-300 text-red-800': error_type === 'error',
          'bg-amber-50 border-amber-300 text-amber-800': error_type === 'warning',
          'bg-slate-50 border-slate-300 text-slate-700': error_type === 'connection',
        }"
      >
        <span class="mt-0.5 leading-none select-none" aria-hidden="true">
          <Icon v-if="error_type === 'warning'" name="fa6-solid:triangle-exclamation" class="w-3.5 h-3.5" />
          <Icon v-else-if="error_type === 'connection'" name="fa6-solid:plug" class="w-3.5 h-3.5" />
          <Icon v-else name="fa6-solid:xmark" class="w-3.5 h-3.5" />
        </span>
        <span>{{ error_message }}</span>
      </div>

      <form class="space-y-6" @submit.prevent="login">
        <div>
          <label for="username" class="block font-medium leading-6 text-gray-900">
            {{ $t('common.user') }}
          </label>
          <input
            id="username"
            v-model="username"
            type="text"
            required
            autocomplete="username"
            :placeholder="$t('common.user')"
            class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
          />
        </div>

        <div>
          <label for="password" class="block font-medium leading-6 text-gray-900">
            {{ $t('common.password') }}
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            :placeholder="$t('common.password')"
            class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
          />
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-1.5 font-semibold leading-6 text-white shadow-sm hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {{ loading ? $t('common.loading') : $t('login.enter') }}
        </button>
      </form>
    </div>
  </div>
</template>
