<script setup>
const router = useRouter()
const username = ref('')

onMounted(() => {
  username.value = localStorage.getItem('user_username') || ''
})

const logout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_username')
  router.push('/auth/login')
}
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="bg-white border-b border-gray-200">
      <div class="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <NuxtLink to="/signs" class="flex items-center gap-2 font-semibold text-xl text-indigo-700">
          <Icon name="fa6-solid:file-signature" class="w-4 h-4" />
          {{ $t('app.name') }}
        </NuxtLink>

        <div class="flex items-center gap-4">
          <span v-if="username" class="text-gray-600">
            <Icon name="fa6-regular:user" class="w-3 h-3 mr-1" />{{ username }}
          </span>
          <button
            type="button"
            class="text-gray-600 hover:text-red-600"
            @click="logout"
          >
            <Icon name="fa6-solid:right-from-bracket" class="w-3.5 h-3.5 mr-1" />
            {{ $t('login.logout') }}
          </button>
        </div>
      </div>
    </header>

    <main class="flex-1 mx-auto w-full max-w-6xl px-4 py-6">
      <slot />
    </main>
  </div>
</template>
