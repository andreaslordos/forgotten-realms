import { getBackendUrl } from './config';

const originalNodeEnv = process.env.NODE_ENV;

afterEach(() => {
  delete process.env.REACT_APP_BACKEND_URL;
  process.env.NODE_ENV = originalNodeEnv;
});

test('uses the local backend outside production', () => {
  expect(getBackendUrl()).toBe('http://localhost:8080');
});

test('uses a configured backend URL and removes trailing slashes', () => {
  process.env.REACT_APP_BACKEND_URL = ' https://preview.example.test/// ';

  expect(getBackendUrl()).toBe('https://preview.example.test');
});

test('keeps the current production origin until a tunnel URL is configured', () => {
  process.env.NODE_ENV = 'production';

  expect(getBackendUrl()).toBe('https://realms-api.lordos.tech');
});
