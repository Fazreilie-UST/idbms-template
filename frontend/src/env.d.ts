/// <reference types="vite/client" />

declare global {
  interface Window {
    /**
     * Runtime config injected by `public/env.js` (dev) or `entrypoint.sh`
     * (Docker). Read by `src/config.ts`. Always optional because
     * deployments without that file fall back to the dev default.
     */
    _env_?: {
      API_URL?: string;
    };
  }
}

export {};
