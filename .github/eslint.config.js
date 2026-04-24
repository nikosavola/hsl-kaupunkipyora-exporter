const globals = require("globals");
const prettier = require("eslint-config-prettier");
const js = require("@eslint/js");

module.exports = [
  js.configs.recommended,
  prettier,
  {
    // Global settings for all files
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
        globalThis: "readonly",
        loadPyodide: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    },
  },
  {
    // Special settings for the configuration file itself (Node.js/CommonJS)
    files: [".github/eslint.config.js"],
    languageOptions: {
      sourceType: "commonjs",
      globals: {
        ...globals.node,
      },
    },
  },
];
