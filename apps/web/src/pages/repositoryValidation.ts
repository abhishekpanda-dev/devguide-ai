export function validateRepositoryUrl(value: string): string | null {
  try {
    const url = new URL(value)
    const parts = url.pathname
      .replace(/\/$/, '')
      .replace(/\.git$/, '')
      .split('/')
      .filter(Boolean)
    if (
      url.protocol !== 'https:' ||
      url.hostname !== 'github.com' ||
      url.username ||
      url.password ||
      url.port ||
      url.search ||
      url.hash ||
      parts.length !== 2 ||
      parts.some((part) => part === '.' || part === '..')
    )
      return 'Enter a public GitHub repository URL in the form https://github.com/owner/repository.'
    return null
  } catch {
    return 'Enter a valid URL.'
  }
}
