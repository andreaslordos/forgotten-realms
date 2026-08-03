export function getBackendUrl() {
  const configuredUrl = process.env.REACT_APP_BACKEND_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, '');
  }

  return process.env.NODE_ENV === 'production'
    ? 'https://realms-api.lordos.tech'
    : 'http://localhost:8080';
}
