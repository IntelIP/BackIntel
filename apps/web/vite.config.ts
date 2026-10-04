import {defineConfig} from 'vite';

export default defineConfig({
  // Rollup's call-interaction analysis stalls on this workspace's nested views.
  // Preserve module behavior and bound build time for the local benchmark UI.
  build: {rollupOptions: {treeshake: false}},
});
