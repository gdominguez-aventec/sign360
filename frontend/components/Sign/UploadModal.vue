<script setup>
import { useToast } from 'vue-toastification'

const emit = defineEmits(['close', 'uploaded'])

const { t } = useI18n()
const toast = useToast()
const { $DocumentSignApiService } = useNuxtApp()
const { formatSize } = useFormatDate()

const files = ref([])
const title = ref('')
const description = ref('')
const signers = ref([{ name: '', email: '', phone: '' }])
const sendNow = ref(true)
const saving = ref(false)
const fileInput = ref(null)

const addFiles = (event) => {
  const selected = Array.from(event.target.files || [])
  const rejected = selected.filter((file) => file.type !== 'application/pdf')
  if (rejected.length) toast.error(t('sign.only_pdf'))

  // Evita duplicats si l'usuari torna a triar el mateix fitxer
  const accepted = selected.filter((file) => file.type === 'application/pdf')
  accepted.forEach((file) => {
    if (!files.value.some((f) => f.name === file.name && f.size === file.size)) {
      files.value.push(file)
    }
  })

  if (!title.value && files.value.length) {
    title.value = files.value[0].name.replace(/\.pdf$/i, '')
  }
  event.target.value = ''
}

const removeFile = (index) => files.value.splice(index, 1)

const addSigner = () => signers.value.push({ name: '', email: '', phone: '' })
const removeSigner = (index) => {
  if (signers.value.length > 1) signers.value.splice(index, 1)
}

const submit = async () => {
  if (!files.value.length) {
    toast.error(t('sign.only_pdf'))
    return
  }

  saving.value = true
  try {
    const response = await $DocumentSignApiService.create({
      files: files.value,
      title: title.value,
      description: description.value,
      signers: signers.value.map((signer) => ({
        name: signer.name,
        email: signer.email,
        phone: signer.phone || '',
      })),
      sendNow: sendNow.value,
    })

    // Els documents sempre queden desats; només l'enviament pot haver fallat.
    if (response?.send_error) toast.warning(`${t('sign.send_error')}: ${response.send_error}`)

    emit('uploaded', response)
  } catch {
    // error ja notificat per api-manager
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 px-4 py-8">
    <div class="w-full max-w-3xl rounded-lg bg-white shadow-xl">
      <div class="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <h2 class="text-lg font-semibold text-gray-900">{{ $t('sign.upload_title') }}</h2>
        <button type="button" class="text-gray-400 hover:text-gray-700" @click="emit('close')">
          <Icon name="fa6-solid:xmark" class="w-4 h-4" />
        </button>
      </div>

      <form class="px-5 py-4 space-y-5" @submit.prevent="submit">
        <!-- Documents -->
        <fieldset>
          <div class="flex items-center justify-between">
            <legend class="font-semibold text-gray-700">{{ $t('sign.files') }} *</legend>
            <button
              type="button"
              class="rounded-md border border-gray-300 bg-white px-2 py-1 text-gray-700 hover:bg-gray-50"
              @click="fileInput?.click()"
            >
              <Icon name="fa6-solid:plus" class="w-3 h-3 mr-1" />{{ $t('sign.add_file') }}
            </button>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="application/pdf"
            multiple
            class="hidden"
            @change="addFiles"
          />

          <ul v-if="files.length" class="mt-2 divide-y divide-gray-100 rounded-md border border-gray-200">
            <li
              v-for="(file, index) in files"
              :key="`${file.name}-${file.size}`"
              class="flex items-center justify-between px-3 py-2"
            >
              <span class="flex items-center gap-2 min-w-0">
                <Icon name="fa6-regular:file-pdf" class="w-3.5 h-3.5 text-red-500 shrink-0" />
                <span class="truncate">{{ file.name }}</span>
                <span class="text-gray-400 shrink-0">{{ formatSize(file.size) }}</span>
              </span>
              <button
                type="button"
                class="text-gray-400 hover:text-red-600 shrink-0"
                :title="$t('sign.remove')"
                @click="removeFile(index)"
              >
                <Icon name="fa6-solid:xmark" class="w-3.5 h-3.5" />
              </button>
            </li>
          </ul>
          <p v-else class="mt-2 rounded-md border border-dashed border-gray-300 px-3 py-6 text-center text-gray-500">
            {{ $t('sign.only_pdf') }}
          </p>
        </fieldset>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label class="block font-medium text-gray-900">{{ $t('sign.doc_title') }}</label>
            <input
              v-model="title"
              type="text"
              class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
            />
          </div>
          <div>
            <label class="block font-medium text-gray-900">{{ $t('sign.description') }}</label>
            <input
              v-model="description"
              type="text"
              class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
            />
          </div>
        </div>

        <!-- Signants -->
        <fieldset class="border-t border-gray-200 pt-3">
          <div class="flex items-center justify-between">
            <legend class="font-semibold text-gray-700">{{ $t('sign.signers') }} *</legend>
            <button
              type="button"
              class="rounded-md border border-gray-300 bg-white px-2 py-1 text-gray-700 hover:bg-gray-50"
              @click="addSigner"
            >
              <Icon name="fa6-solid:plus" class="w-3 h-3 mr-1" />{{ $t('sign.add_signer') }}
            </button>
          </div>
          <p class="mt-1 text-gray-500">{{ $t('sign.chain_note') }}</p>

          <div
            v-for="(signer, index) in signers"
            :key="index"
            class="mt-2 flex items-start gap-2 rounded-md border border-gray-200 p-2"
          >
            <span
              class="mt-1.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-50 font-semibold text-indigo-700"
            >
              {{ index + 1 }}
            </span>
            <div class="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-3">
              <input
                v-model="signer.name"
                type="text"
                required
                :placeholder="$t('sign.signer_name')"
                class="block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
              <input
                v-model="signer.email"
                type="email"
                required
                :placeholder="$t('sign.signer_email')"
                class="block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
              <input
                v-model="signer.phone"
                type="tel"
                :placeholder="$t('sign.signer_phone')"
                class="block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
            </div>
            <button
              type="button"
              class="mt-1.5 shrink-0 text-gray-400 hover:text-red-600 disabled:opacity-30"
              :disabled="signers.length === 1"
              :title="$t('sign.remove')"
              @click="removeSigner(index)"
            >
              <Icon name="fa6-solid:xmark" class="w-3.5 h-3.5" />
            </button>
          </div>
        </fieldset>

        <label class="flex items-center gap-2">
          <input v-model="sendNow" type="checkbox" class="rounded border-gray-300 text-indigo-600" />
          <span>{{ $t('sign.send_now') }}</span>
        </label>

        <div class="flex justify-end gap-2 border-t border-gray-200 pt-3">
          <button
            type="button"
            class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="rounded-md bg-indigo-600 px-3 py-1.5 font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-60"
          >
            {{ saving ? $t('common.loading') : $t('common.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
