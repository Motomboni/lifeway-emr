/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string
    readonly VITE_APP_NAME: string
    readonly VITE_APP_SHORT_NAME: string
    readonly VITE_SENTRY_DSN?: string
    readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string
    readonly VITE_APP_VERSION?: string
    readonly MODE: string
    readonly BASE_URL: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
