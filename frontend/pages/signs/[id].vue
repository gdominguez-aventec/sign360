<script setup>
import { useToast } from 'vue-toastification'

const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const { $DocumentSignApiService } = useNuxtApp()
const { SIGN_STATUS, label, badgeClass, icon, canSend } = useSignStatus()
const { formatDateTime, formatSize } = useFormatDate()

const id = route.params.id
const item = ref(null)
const loading = ref(true)
const sending = ref(false)

// El visor és un <iframe> sobre un blob: l'endpoint del PDF demana el token a
// la capçalera i un <iframe src="..."> no en pot enviar cap.
const pdfUrl = ref('')

const loadPdf = async () => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
  if (!item.value?.document_file && !item.value?.document_file_signed) return
  try {
    const blob = await $DocumentSignApiService.getBlob(id)
    pdfUrl.value = URL.createObjectURL(blob)
  } catch {
    pdfUrl.value = ''
  }
}

const load = async () => {
  loading.value = true
  try {
    item.value = await $DocumentSignApiService.get(id)
    await loadPdf()
  } catch {
    item.value = null
  } finally {
    loading.value = false
  }
}

const sendToSign = async (force = false) => {
  sending.value = true
  try {
    await $DocumentSignApiService.sendToSign(id, force ? { force: true } : {})
    toast.success(t('sign.sent_ok'))
    await load()
  } catch {
    // error ja notificat
  } finally {
    sending.value = false
  }
}

const download = () =>
  $DocumentSignApiService.download(
    id,
    item.value?.document_file_signed_detail?.document_name ||
      item.value?.document_file_detail?.document_name ||
      `${item.value?.token}.pdf`
  )

const downloadOriginal = () =>
  $DocumentSignApiService.downloadOriginal(
    id,
    item.value?.document_file_detail?.document_name || `${item.value?.token}.pdf`
  )

onMounted(load)
onBeforeUnmount(() => {
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
})
</script>

<template>
  <div>
    <NuxtLink to="/signs" class="text-gray-500 hover:text-indigo-600">
      <Icon name="fa6-solid:arrow-left" class="w-3 h-3 mr-1" />{{ $t('common.back') }}
    </NuxtLink>

    <div v-if="loading" class="mt-6 text-gray-500">{{ $t('common.loading') }}</div>
    <div v-else-if="!item" class="mt-6 text-gray-500">{{ $t('common.no_results') }}</div>

    <div v-else class="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Visor -->
      <div class="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div class="flex items-center justify-between border-b border-gray-200 px-4 py-2">
          <span class="font-semibold text-gray-700">
            {{ item.document_file_signed ? $t('sign.signed_copy') : $t('sign.original') }}
          </span>
          <button
            type="button"
            class="text-gray-500 hover:text-indigo-600"
            :title="$t('sign.download')"
            @click="download"
          >
            <Icon name="fa6-solid:download" class="w-3.5 h-3.5" />
          </button>
        </div>
        <iframe
          v-if="pdfUrl"
          :src="pdfUrl"
          class="w-full"
          style="height: 70vh"
          title="PDF"
        />
        <div v-else class="px-4 py-16 text-center text-gray-500">
          {{ $t('common.no_results') }}
        </div>
      </div>

      <!-- Fitxa -->
      <div class="bg-white rounded-lg border border-gray-200 p-4 space-y-4 self-start">
        <div>
          <h1 class="text-xl font-bold text-gray-900">{{ item.title || item.token }}</h1>
          <p v-if="item.description" class="mt-1 text-gray-600">{{ item.description }}</p>
        </div>

        <div>
          <span
            class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 ring-1 ring-inset"
            :class="badgeClass(item.status)"
          >
            <Icon :name="icon(item.status)" class="w-3 h-3" />
            {{ label(item.status) }}
          </span>
        </div>

        <div
          v-if="item.error_report"
          class="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-red-700"
        >
          <span class="font-semibold">{{ $t('sign.error_report') }}:</span> {{ item.error_report }}
        </div>

        <dl class="space-y-2 text-gray-700">
          <div class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.signer_name') }}</dt>
            <dd class="text-right">{{ item.otp_name || '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.signer_email') }}</dt>
            <dd class="text-right break-all">{{ item.otp_email || '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.signer_phone') }}</dt>
            <dd class="text-right">{{ item.otp_phone || '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.created_at') }}</dt>
            <dd class="text-right">{{ formatDateTime(item.created_at) }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.signed_at') }}</dt>
            <dd class="text-right">{{ formatDateTime(item.signed_at) }}</dd>
          </div>
          <div v-if="item.document_file_detail" class="flex justify-between gap-4">
            <dt class="text-gray-500">{{ $t('sign.original') }}</dt>
            <dd class="text-right">{{ formatSize(item.document_file_detail.size) }}</dd>
          </div>
        </dl>

        <div class="border-t border-gray-200 pt-3 space-y-2">
          <button
            v-if="canSend(item.status)"
            type="button"
            :disabled="sending"
            class="w-full rounded-md bg-indigo-600 px-3 py-1.5 font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-60"
            @click="sendToSign(false)"
          >
            <Icon name="fa6-solid:paper-plane" class="w-3 h-3 mr-1" />
            {{ item.status === SIGN_STATUS.PENDING ? $t('sign.send_to_sign') : $t('sign.resend') }}
          </button>

          <button
            type="button"
            class="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            @click="download"
          >
            <Icon name="fa6-solid:download" class="w-3 h-3 mr-1" />{{ $t('sign.download') }}
          </button>

          <button
            v-if="item.document_file_signed"
            type="button"
            class="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            @click="downloadOriginal"
          >
            <Icon name="fa6-regular:file-lines" class="w-3 h-3 mr-1" />
            {{ $t('sign.download_original') }}
          </button>

          <button
            type="button"
            class="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            @click="load"
          >
            <Icon name="fa6-solid:rotate" class="w-3 h-3 mr-1" />{{ $t('sign.refresh') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
