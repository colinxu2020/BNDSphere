// openapi-ts.config.ts
import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'src/lib/openapi.json',
  output: {
    format: 'prettier',
    path: 'src/client',
  },
  client: 'fetch',
  types: {
    enums: 'javascript',
  },
});
