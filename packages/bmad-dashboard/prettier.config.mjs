/**
 * @see https://prettier.io/docs/configuration
 * @type {import("prettier").Config}
 */
const config = {
  $schema: 'https://json.schemastore.org/prettierrc',
  plugins: ['prettier-plugin-packagejson'],
  singleQuote: true,
  overrides: [
    {
      files: ['**/*.jsonc'],
      options: {
        trailingComma: 'none',
      },
    },
  ],
};

export default config;
