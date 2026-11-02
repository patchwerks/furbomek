export default defineNuxtConfig({
  srcDir: '.',
  ssr: false,
  devtools: { enabled: false },
  modules: [],
  css: ['bootstrap/dist/css/bootstrap.min.css', '~/viewer.css'],
  typescript: { strict: true, typeCheck: true },
  app: { head: {
    title: 'Furb-o-Mek · Presentation preview',
    meta: [{ 'http-equiv': 'Content-Security-Policy', content: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; media-src 'none'" }],
  } },
})
