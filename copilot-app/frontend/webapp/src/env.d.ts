// Extra vite env keys used in this project
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_MOCKS?: string;
  readonly VITE_ENABLE_SSE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
