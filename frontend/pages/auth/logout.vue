<script setup>
definePageMeta({ layout: 'auth' })

onMounted(() => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_username')
  navigateTo('/auth/login')
})
</script>

<template>
  <div class="text-gray-500">{{ $t('common.loading') }}</div>
</template>
