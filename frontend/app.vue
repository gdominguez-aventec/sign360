<script setup lang="ts">
const config = useRuntimeConfig()
const env = config.public.env
</script>

<template>
  <div>
    <!-- Distintiu d'entorn: només fora de producció -->
    <div
      v-if="env && env !== 'prod' && env !== 'production'"
      :class="[
        'fixed top-0 left-0 z-[9999] text-white px-4 pb-1 text-sm font-bold shadow-lg rounded-br-md',
        String(env).toUpperCase() === 'LOCAL' ? 'bg-green-500' : 'bg-orange-500',
      ]"
    >
      {{ String(env).toUpperCase() }}
    </div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
