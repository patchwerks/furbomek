// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  srcDir: '.',
  devtools: {enabled: false},
  modules: ['@bootstrap-vue-next/nuxt', "@nuxt/eslint"],
  css: ['bootstrap/dist/css/bootstrap.min.css'],
  bootstrapVueNext: {
    composables: true, // Will include all composables
    // composables: {useBreadcrumb: true, useColorMode: true, all: false}, // Will include only useBreadcrumb & useColorMode
    // composables: {useBreadcrumb: false, useColorMode: false, all: true} // Will include everything except useBreadcrumb & useColorMode
    directives: {all: true}, // Will include all directives
  },
  ssr: false,
  app: {
    head: {
      link: [
        // {rel: 'preconnect', href: 'https://api.play.ht/'},
      ]
    }
  },
  plugins: [
    // {src: '~/plugins/directives.ts', mode: 'client'}
  ],
  typescript: {
    strict: true,
    typeCheck: true
  }
})