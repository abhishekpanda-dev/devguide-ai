export function dashboardFocusTarget(repositoryId: string, search: string) {
  const focus = new URLSearchParams(search).get('focus')
  return focus ? `/repositories/${repositoryId}?focus=${encodeURIComponent(focus)}` : null
}
