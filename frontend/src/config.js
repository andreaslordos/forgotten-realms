export function getBackendUrl() {
  return process.env.NODE_ENV === 'production'
    ? 'https://api.realms.lordos.tech:8080'
    : 'http://localhost:8080';
}
