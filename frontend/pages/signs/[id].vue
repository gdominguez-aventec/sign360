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

const selectedDocumentId = ref(null)
// Quina versió es mostra al visor: 'current', 'original' o l'id d'un Document
// concret de la cadena.
const selectedVersion = ref('current')
const pdfUrl = ref('')
const pdfLoading = ref(false)

const selectedDocument = computed(
  () => item.value?.documents.find((doc) => doc.id === selectedDocumentId.value) ?? null
)

const versionOptions = computed(() => {
  const doc = selectedDocument.value
  if (!doc) return []
  return [
    { value: 'original', label: `${t('sign.original_version')} · v${doc.original_document_detail.version}` },
    ...doc.signatures.map((signature) => ({
      value: signature.document,
      label: `v${signature.document_detail.version} · ${t('sign.signed_by')} ${signature.signer_order}. ${signature.signer_name}`,
    })),
  ]
})

const releaseUrl = () => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
}

// El visor és un <iframe> sobre un blob: l'endpoint del PDF demana el token a
// la capçalera i un <iframe src="..."> no en pot enviar cap.
const loadPdf = async () => {
  releaseUrl()
  const doc = selectedDocument.value
  if (!doc) return

  pdfLoading.value = true
  try {
    let blob
    if (selectedVersion.value === 'current') {
      blob = await $DocumentSignApiService.documentBlob(doc.id)
    } else if (selectedVersion.value === 'original') {
      blob = await $DocumentSignApiService.documentBlob(doc.id, { original: true })
    } else {
      blob = await $DocumentSignApiService.versionBlob(selectedVersion.value)
    }
    pdfUrl.value = URL.createObjectURL(blob)
  } catch {
    pdfUrl.value = ''
  } finally {
    pdfLoading.value = false
  }
}

const load = async () => {
  loading.value = true
  try {
    item.value = await $DocumentSignApiService.get(id)
    if (!selectedDocumentId.value || !selectedDocument.value) {
      selectedDocumentId.value = item.value.documents[0]?.id ?? null
      selectedVersion.value = 'current'
    }
    await loadPdf()
  } catch {
    item.value = null
  } finally {
    loading.value = false
  }
}

const selectDocument = async (documentId) => {
  selectedDocumentId.value = documentId
  selectedVersion.value = 'current'
  await loadPdf()
}

const sendToSign = async (signer = null) => {
  sending.value = true
  try {
    const response = await $DocumentSignApiService.sendToSign(
      id,
      signer ? { signer: signer.id, force: true } : {}
    )
    toast.success(`${t('sign.sent_ok')} — ${response.sent_to}`)
    await load()
  } catch {
    // error ja notificat
  } finally {
    sending.value = false
  }
}

const downloadCurrent = (doc) =>
  $DocumentSignApiService.downloadDocument(doc.id, doc.current_document_detail.document_name)

const downloadOriginal = (doc) =>
  $DocumentSignApiService.downloadDocument(doc.id, doc.original_document_detail.document_name, {
    original: true,
  })

watch(selectedVersion, loadPdf)

onMounted(load)
onBeforeUnmount(releaseUrl)
</script>

<template>
  <div>
    <NuxtLink to="/signs" class="text-gray-500 hover:text-indigo-600">
      <Icon name="fa6-solid:arrow-left" class="w-3 h-3 mr-1" />{{ $t('common.back') }}
    </NuxtLink>

    <div v-if="loading" class="mt-6 text-gray-500">{{ $t('common.loading') }}</div>
    <div v-else-if="!item" class="mt-6 text-gray-500">{{ $t('common.no_results') }}</div>

    <div v-else class="mt-3 grid grid-cols-1 gap-4 xl:grid-cols-4">
      <!-- Visor: ocupa la major part de l'amplada -->
      <div class="xl:col-span-3 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-4 py-2">
          <div class="flex flex-wrap items-center gap-2">
            <!-- Pestanyes de documents -->
            <button
              v-for="doc in item.documents"
              :key="doc.id"
              type="button"
              class="inline-flex items-center gap-1 rounded-md px-2 py-1 ring-1 ring-inset"
              :class="
                doc.id === selectedDocumentId
                  ? 'bg-indigo-50 text-indigo-700 ring-indigo-300 font-semibold'
                  : 'bg-white text-gray-600 ring-gray-300 hover:bg-gray-50'
              "
              @click="selectDocument(doc.id)"
            >
              <Icon name="fa6-regular:file-pdf" class="w-3 h-3 text-red-500" />
              <span class="max-w-[16rem] truncate">
                {{ doc.original_document_detail.document_name }}
              </span>
              <Icon
                v-if="doc.is_signed"
                name="fa6-solid:circle-check"
                class="w-3 h-3 text-green-600"
              />
            </button>
          </div>

          <div v-if="selectedDocument" class="flex items-center gap-2">
            <select
              v-model="selectedVersion"
              class="rounded-md border-0 py-1 pl-2 pr-8 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
            >
              <option value="current">
                {{ $t('sign.current_version') }} · v{{ selectedDocument.current_document_detail.version }}
              </option>
              <option v-for="option in versionOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <button
              type="button"
              class="text-gray-500 hover:text-indigo-600"
              :title="$t('sign.download')"
              @click="downloadCurrent(selectedDocument)"
            >
              <Icon name="fa6-solid:download" class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div v-if="pdfLoading" class="px-4 py-16 text-center text-gray-500">
          {{ $t('common.loading') }}
        </div>
        <iframe
          v-else-if="pdfUrl"
          :src="pdfUrl"
          class="w-full flex-1"
          style="min-height: 75vh"
          title="PDF"
        />
        <div v-else class="px-4 py-16 text-center text-gray-500">
          {{ $t('sign.select_document') }}
        </div>
      </div>

      <!-- Fitxa -->
      <div class="space-y-4">
        <div class="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
          <div>
            <h1 class="text-xl font-bold text-gray-900">{{ item.title || item.token }}</h1>
            <p v-if="item.description" class="mt-1 text-gray-600">{{ item.description }}</p>
          </div>

          <span
            class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 ring-1 ring-inset"
            :class="badgeClass(item.status)"
          >
            <Icon :name="icon(item.status)" class="w-3 h-3" />
            {{ label(item.status) }}
          </span>

          <div
            v-if="item.error_report"
            class="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-red-700"
          >
            <span class="font-semibold">{{ $t('sign.error_report') }}:</span> {{ item.error_report }}
          </div>

          <dl class="space-y-2 text-gray-700">
            <div class="flex justify-between gap-4">
              <dt class="text-gray-500">{{ $t('sign.created_at') }}</dt>
              <dd>{{ formatDateTime(item.created_at) }}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-gray-500">{{ $t('sign.signed_at') }}</dt>
              <dd>{{ formatDateTime(item.signed_at) }}</dd>
            </div>
          </dl>

          <div class="border-t border-gray-200 pt-3 space-y-2">
            <button
              v-if="canSend(item.status) && item.next_signer"
              type="button"
              :disabled="sending"
              class="w-full rounded-md bg-indigo-600 px-3 py-1.5 font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-60"
              @click="sendToSign()"
            >
              <Icon name="fa6-solid:paper-plane" class="w-3 h-3 mr-1" />
              {{ $t('sign.send_next') }}: {{ item.next_signer.name }}
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

        <!-- Cadena de signants -->
        <div class="bg-white rounded-lg border border-gray-200 p-4">
          <h2 class="font-semibold text-gray-700">{{ $t('sign.signers') }}</h2>
          <p class="mt-1 text-gray-500">{{ $t('sign.chain_note') }}</p>

          <ol class="mt-3 space-y-2">
            <li
              v-for="signer in item.signers"
              :key="signer.id"
              class="flex items-start gap-2 rounded-md border border-gray-200 p-2"
            >
              <span
                class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-semibold ring-1 ring-inset"
                :class="badgeClass(signer.status)"
              >
                {{ signer.order }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="font-medium text-gray-900 truncate">{{ signer.name }}</div>
                <div class="text-gray-500 truncate">{{ signer.email }}</div>
                <div class="mt-0.5 flex items-center gap-1">
                  <Icon :name="icon(signer.status)" class="w-3 h-3" />
                  <span>{{ label(signer.status) }}</span>
                  <span v-if="signer.signed_at" class="text-gray-500">
                    · {{ formatDateTime(signer.signed_at) }}
                  </span>
                </div>
                <div v-if="signer.error_report" class="mt-0.5 text-red-600">
                  {{ signer.error_report }}
                </div>
                <button
                  v-if="signer.status === SIGN_STATUS.EXPIRED || signer.status === SIGN_STATUS.ERROR"
                  type="button"
                  :disabled="sending"
                  class="mt-1 rounded-md border border-gray-300 bg-white px-2 py-0.5 text-gray-700 hover:bg-gray-50 disabled:opacity-60"
                  @click="sendToSign(signer)"
                >
                  <Icon name="fa6-solid:rotate-right" class="w-3 h-3 mr-1" />
                  {{ $t('sign.retry_signer') }}
                </button>
              </div>
            </li>
          </ol>
        </div>

        <!-- Documents i les seves versions -->
        <div class="bg-white rounded-lg border border-gray-200 p-4">
          <h2 class="font-semibold text-gray-700">{{ $t('sign.documents') }}</h2>
          <ul class="mt-3 space-y-2">
            <li
              v-for="doc in item.documents"
              :key="doc.id"
              class="rounded-md border border-gray-200 p-2"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="min-w-0 truncate font-medium text-gray-900">
                  {{ doc.original_document_detail.document_name }}
                </span>
                <span class="shrink-0 text-gray-400">
                  {{ formatSize(doc.current_document_detail.size) }}
                </span>
              </div>
              <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                <button
                  type="button"
                  class="text-gray-500 hover:text-indigo-600"
                  @click="downloadOriginal(doc)"
                >
                  <Icon name="fa6-regular:file-lines" class="w-3 h-3 mr-1" />
                  {{ $t('sign.original_version') }}
                </button>
                <button
                  v-if="doc.is_signed"
                  type="button"
                  class="text-gray-500 hover:text-indigo-600"
                  @click="downloadCurrent(doc)"
                >
                  <Icon name="fa6-solid:download" class="w-3 h-3 mr-1" />
                  {{ $t('sign.current_version') }} (v{{ doc.current_document_detail.version }})
                </button>
                <span v-else class="text-gray-400">{{ $t('sign.no_signature_yet') }}</span>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
