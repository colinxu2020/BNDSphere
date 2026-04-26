import { client } from '@/client/client.gen';

export const API_BASE_URL = '/';

client.setConfig({
  baseUrl: '/',
});

client.interceptors.request.use((request, options) => {
  const token = localStorage.getItem('token');
  if (token) {
    request.headers.set('Authorization', `Bearer ${token}`);
  }
  return request;
});
