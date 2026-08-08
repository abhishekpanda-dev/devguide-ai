export function dashboardFocusTarget(repositoryId: string, analysisId: string, search: string) {
  const source = new URLSearchParams(search)
  const target = new URLSearchParams({ analysis: analysisId })
  const focus = source.get('focus')
  if (focus) target.set('focus', focus)
  return `/repositories/${repositoryId}?${target}`
}
