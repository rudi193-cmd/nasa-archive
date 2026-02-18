// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // Update site to your custom domain once configured
  // site: 'https://your-domain.com',
  output: 'static',
  vite: {
    plugins: [tailwindcss()]
  }
});