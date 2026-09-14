<script setup>
import { useToast } from 'vue-toastification'

const { t } = useI18n()
const toast = useToast()
const { $DocumentSignApiService } = useNuxtApp()
const { SIGN_STATUS, label, badgeClass, icon, canSend } = useSignStatus()
const { formatDateTime } = useFormatDate()

const items = ref([])
const count = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref([])
const page = ref(1)

const showUpload = ref(false)
const sendingId = ref(null)

const STATUS_OPTIONS = [
  SIGN_STATUS.PENDING,
  SIGN_STATUS.SENDED,
  SIGN_STATUS.SIGNED,
  SIGN_STATUS.EXPIRED,
  SIGN_STATUS.ERROR,
]

const load = async () => {
  loading.value = true
  try {
    const response = await $DocumentSignApiService.getAll({
      search: search.value,
      status: statusFilter.value.join(','),
      page: page.value,
    })
    items.value = response?.results ?? response ?? []
    count.value = response?.count ?? items.value.length
  } catch {
    // El toast d'error ja l'ha mostrat `api-manager`
  } finally {
    loading.value = false
  }
}

const toggleStatus = (value) => {
  const index = statusFilter.value.indexOf(value)
  if (index === -1) statusFilter.value.push(value)
  else statusFilter.value.splice(index, 1)
  page.value = 1
  load()
}

let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 350)
})

const sendToSign = async (item) => {
  sendingId.value = item.id
  try {
    await $DocumentSignApiService.sendToSign(item.id)
    toast.success(t('sign.sent_ok'))
    await load()
  } catch {
    // error ja notificat
  } finally {
    sendingId.value = null
  }
}

const download = (item) => {
  const filename =
    item.document_file_signed_detail?.document_name ||
    item.document_file_detail?.document_name ||
    `${item.token}.pdf`
  return $DocumentSignApiService.download(item.id, filename)
}

const onUploaded = async () => {
  showUpload.value = false
  toast.success(t('sign.upload_ok'))
  page.value = 1
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold text-gray-900">{{ $t('sign.title') }}</h1>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
          :disabled="loading"
          @click="load"
        >
          <Icon name="fa6-solid:rotate" class="w-3 h-3 mr-1" />{{ $t('sign.refresh') }}
        </button>
        <button
          type="button"
          class="rounded-md bg-indigo-600 px-3 py-1.5 font-semibold text-white shadow-sm hover:bg-indigo-500"
          @click="showUpload = true"
        >
          <Icon name="fa6-solid:upload" class="w-3 h-3 mr-1" />{{ $t('sign.upload') }}
        </button>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 mb-4">
      <div class="relative">
        <Icon
          name="fa6-solid:magnifying-glass"
          class="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          v-model="search"
          type="search"
          :placeholder="$t('common.search')"
          class="rounded-md border-0 py-1.5 pl-8 pr-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 w-64"
        />
      </div>

      <button
        v-for="option in STATUS_OPTIONS"
        :key="option"
        type="button"
        class="rounded-full px-2.5 py-1 ring-1 ring-inset"
        :class="[
          badgeClass(option),
          statusFilter.includes(option) ? 'font-semibold ring-2' : 'opacity-60',
        ]"
        @click="toggleStatus(option)"
      >
        {{ label(option) }}
      </button>
    </div>

    <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr class="text-left text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-2 font-medium">{{ $t('sign.doc_title') }}</th>
            <th class="px-4 py-2 font-medium">{{ $t('sign.signer') }}</th>
            <th class="px-4 py-2 font-medium">{{ $t('sign.status') }}</th>
            <th class="px-4 py-2 font-medium">{{ $t('sign.created_at') }}</th>
            <th class="px-4 py-2 font-medium">{{ $t('sign.signed_at') }}</th>
            <th class="px-4 py-2 font-medium text-right">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="6" class="px-4 py-8 text-center text-gray-500">
              {{ $t('common.loading') }}
            </td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="6" class="px-4 py-8 text-center text-gray-500">
              {{ $t('sign.empty') }}
            </td>
          </tr>
          <tr v-for="item in items" v-else :key="item.id" class="hover:bg-gray-50">
            <td class="px-4 py-2">
              <NuxtLink :to="`/signs/${item.id}`" class="text-indigo-700 hover:underline font-medium">
                {{ item.title || item.token }}
              </NuxtLink>
              <div v-if="item.error_report" class="text-red-600 mt-0.5">
                {{ item.error_report }}
              </div>
            </td>
            <td class="px-4 py-2">
              <div>{{ item.otp_name }}</div>
              <div class="text-gray-500">{{ item.otp_email }}</div>
            </td>
            <td class="px-4 py-2">
              <span
                class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 ring-1 ring-inset"
                :class="badgeClass(item.status)"
              >
                <Icon :name="icon(item.status)" class="w-3 h-3" />
                {{ label(item.status) }}
              </span>
            </td>
            <td class="px-4 py-2 text-gray-600">{{ formatDateTime(item.created_at) }}</td>
            <td class="px-4 py-2 text-gray-600">{{ formatDateTime(item.signed_at) }}</td>
            <td class="px-4 py-2">
              <div class="flex items-center justify-end gap-3">
                <NuxtLink
                  :to="`/signs/${item.id}`"
                  class="text-gray-500 hover:text-indigo-600"
                  :title="$t('sign.view')"
                >
                  <Icon name="fa6-regular:eye" class="w-3.5 h-3.5" />
                </NuxtLink>
                <button
                  type="button"
                  class="text-gray-500 hover:text-indigo-600"
                  :title="$t('sign.download')"
                  @click="download(item)"
                >
                  <Icon name="fa6-solid:download" class="w-3.5 h-3.5" />
                </button>
                <button
                  v-if="canSend(item.status)"
                  type="button"
                  class="text-gray-500 hover:text-indigo-600 disabled:opacity-50"
                  :title="item.status === SIGN_STATUS.PENDING ? $t('sign.send_to_sign') : $t('sign.resend')"
                  :disabled="sendingId === item.id"
                  @click="sendToSign(item)"
                >
                  <Icon name="fa6-solid:paper-plane" class="w-3.5 h-3.5" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="count" class="mt-2 text-gray-500">{{ count }}</p>

    <SignUploadModal v-if="showUpload" @close="showUpload = false" @uploaded="onUploaded" />
  </div>
</template>
