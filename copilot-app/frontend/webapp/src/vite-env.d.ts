/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_MOCKS?: string;
  readonly VITE_ENABLE_SSE?: string;
  readonly VITE_APP_DEBUG?: string;
  readonly VITE_DISABLE_WEB3?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
