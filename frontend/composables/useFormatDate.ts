import dayjs from 'dayjs'

export const useFormatDate = () => {
  const formatDateTime = (value?: string | null) =>
    value ? dayjs(value).format('DD/MM/YYYY HH:mm') : '—'

  const formatDate = (value?: string | null) =>
    value ? dayjs(value).format('DD/MM/YYYY') : '—'

  const formatSize = (bytes?: number | null) => {
    if (!bytes && bytes !== 0) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return { formatDate, formatDateTime, formatSize }
}
