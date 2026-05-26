import createClient from 'openapi-fetch';
import type { paths } from './schema';

export const client = createClient<paths>({
  // Pointing to current origin; in a real app this might be an external backend
  baseUrl: window.location.origin,
});

// Interceptor to attach auth token if available
client.use({
  onRequest({ request }) {
    const token = localStorage.getItem('bnd_token');
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  }
});
