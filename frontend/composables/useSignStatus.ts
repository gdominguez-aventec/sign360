// Estats de `DocumentSign` al backend (documentmanager/models.py).
export const SIGN_STATUS = {
  PENDING: 1,
  SENDED: 2,
  SIGNED: 3,
  EXPIRED: 4,
  ERROR: -1,
} as const

const BADGE_CLASSES: Record<number, string> = {
  [SIGN_STATUS.PENDING]: 'bg-slate-100 text-slate-700 ring-slate-300',
  [SIGN_STATUS.SENDED]: 'bg-blue-50 text-blue-700 ring-blue-300',
  [SIGN_STATUS.SIGNED]: 'bg-green-50 text-green-700 ring-green-300',
  [SIGN_STATUS.EXPIRED]: 'bg-amber-50 text-amber-800 ring-amber-300',
  [SIGN_STATUS.ERROR]: 'bg-red-50 text-red-700 ring-red-300',
}

const ICONS: Record<number, string> = {
  [SIGN_STATUS.PENDING]: 'fa6-regular:clock',
  [SIGN_STATUS.SENDED]: 'fa6-solid:paper-plane',
  [SIGN_STATUS.SIGNED]: 'fa6-solid:circle-check',
  [SIGN_STATUS.EXPIRED]: 'fa6-solid:hourglass-end',
  [SIGN_STATUS.ERROR]: 'fa6-solid:triangle-exclamation',
}

export const useSignStatus = () => {
  const { t } = useI18n()

  const label = (status: number) => t(`sign.status_${status}`)
  const badgeClass = (status: number) => BADGE_CLASSES[status] ?? BADGE_CLASSES[SIGN_STATUS.PENDING]
  const icon = (status: number) => ICONS[status] ?? ICONS[SIGN_STATUS.PENDING]

  // Un document firmat no es pot reenviar: la nova sessió invalidaria el PDF
  // que ja tenim guardat. Es pot forçar des del detall si cal.
  const canSend = (status: number) => status !== SIGN_STATUS.SIGNED

  return { SIGN_STATUS, label, badgeClass, icon, canSend }
}
