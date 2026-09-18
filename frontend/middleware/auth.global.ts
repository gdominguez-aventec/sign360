const isAuthenticated = () => localStorage.getItem('auth_token') !== null

export default defineNuxtRouteMiddleware((to) => {
  if (!import.meta.client) return

  const no_auth_paths = ['/auth/login', '/auth/logout']
  if (no_auth_paths.includes(to.path)) return

  if (!isAuthenticated()) {
    // Es desa `path` (no `fullPath`) perquè els paràmetres no quedin a la
    // barra d'adreces després del login.
    const redirect = to.path
    if (redirect && redirect !== '/') {
      return navigateTo({ path: '/auth/login', query: { redirect } })
    }
    return navigateTo('/auth/login')
  }
})
