<script setup>
import { useToast } from 'vue-toastification'

const emit = defineEmits(['close', 'uploaded'])

const { t } = useI18n()
const toast = useToast()
const { $DocumentSignApiService } = useNuxtApp()

const file = ref(null)
const title = ref('')
const description = ref('')
const otpName = ref('')
const otpEmail = ref('')
const otpPhone = ref('')
const sendNow = ref(true)
const saving = ref(false)

const onFileChange = (event) => {
  const selected = event.target.files?.[0] ?? null
  if (selected && selected.type !== 'application/pdf') {
    toast.error(t('sign.only_pdf'))
    event.target.value = ''
    file.value = null
    return
  }
  file.value = selected
  if (selected && !title.value) title.value = selected.name.replace(/\.pdf$/i, '')
}

const submit = async () => {
  if (!file.value) {
    toast.error(t('sign.only_pdf'))
    return
  }

  saving.value = true
  try {
    const response = await $DocumentSignApiService.create({
      file: file.value,
      title: title.value,
      description: description.value,
      otpName: otpName.value,
      otpEmail: otpEmail.value,
      otpPhone: otpPhone.value,
      sendNow: sendNow.value,
    })

    // El document sempre queda guardat; només l'enviament pot haver fallat.
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
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
    <div class="w-full max-w-lg rounded-lg bg-white shadow-xl">
      <div class="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <h2 class="text-lg font-semibold text-gray-900">{{ $t('sign.upload_title') }}</h2>
        <button type="button" class="text-gray-400 hover:text-gray-700" @click="emit('close')">
          <Icon name="fa6-solid:xmark" class="w-4 h-4" />
        </button>
      </div>

      <form class="px-5 py-4 space-y-4" @submit.prevent="submit">
        <div>
          <label class="block font-medium text-gray-900">{{ $t('sign.file') }} *</label>
          <input
            type="file"
            accept="application/pdf"
            required
            class="mt-2 block w-full rounded-md border border-gray-300 p-1.5 file:mr-3 file:rounded file:border-0 file:bg-indigo-50 file:px-2 file:py-1 file:text-indigo-700"
            @change="onFileChange"
          />
        </div>

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
          <textarea
            v-model="description"
            rows="2"
            class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
          />
        </div>

        <fieldset class="border-t border-gray-200 pt-3">
          <legend class="font-semibold text-gray-700">{{ $t('sign.signer') }}</legend>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 mt-2">
            <div class="sm:col-span-2">
              <label class="block font-medium text-gray-900">{{ $t('sign.signer_name') }} *</label>
              <input
                v-model="otpName"
                type="text"
                required
                class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
            </div>
            <div>
              <label class="block font-medium text-gray-900">{{ $t('sign.signer_email') }} *</label>
              <input
                v-model="otpEmail"
                type="email"
                required
                class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
            </div>
            <div>
              <label class="block font-medium text-gray-900">{{ $t('sign.signer_phone') }}</label>
              <input
                v-model="otpPhone"
                type="tel"
                class="mt-2 block w-full rounded-md border-0 p-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
              />
            </div>
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
