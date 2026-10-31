// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    name: 'furbomek/preserve-lint-enforcement',
    rules: {
      // Nuxt 1.x no longer enables this existing import-x rule by default.
      'import/no-self-import': 'error',
      // ESLint 8 checked every constant loop, including while (true).
      'no-constant-condition': ['error', { checkLoops: 'all' }],
    },
  },
)
