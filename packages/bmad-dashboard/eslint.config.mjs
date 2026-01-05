import pluginJs from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';
import perfectionist from 'eslint-plugin-perfectionist';
import pluginReact from 'eslint-plugin-react';
import pluginReactHooks from 'eslint-plugin-react-hooks';
import sonarjs from 'eslint-plugin-sonarjs';
import eslintPluginUnicorn from 'eslint-plugin-unicorn';
import globals from 'globals';
import tseslint from 'typescript-eslint';

/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  // Recommended ESLint rules
  pluginJs.configs.recommended,

  // Recommended TypeScript strict rules
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  // Recommended Unicorn rules for code quality
  eslintPluginUnicorn.configs.recommended,

  // SonarJS rules for bug detection
  {
    ...sonarjs.configs.recommended,
    rules: {
      ...sonarjs.configs.recommended.rules,
      // Adjusted thresholds for moderate complexity
      'sonarjs/cognitive-complexity': ['error', 20],
      'sonarjs/todo-tag': 'error',
    },
  },

  // Perfectionist for import/member sorting
  {
    plugins: { perfectionist },
    rules: {
      ...perfectionist.configs['recommended-natural'].rules,
      // Import sorting: React first, then external, then internal
      'perfectionist/sort-imports': [
        'error',
        {
          customGroups: [
            { elementNamePattern: '^react$|^react-.+', groupName: 'react' },
            { elementNamePattern: '^ink$|^ink/.+', groupName: 'ink' },
          ],
          groups: [
            'react',
            'ink',
            'type-import',
            ['value-builtin', 'value-external'],
            'type-internal',
            'value-internal',
            ['type-parent', 'type-sibling', 'type-index'],
            ['value-parent', 'value-sibling', 'value-index'],
            'ts-equals-import',
            'unknown',
          ],
          internalPattern: ['^~/.+', '^@/.+'],
          newlinesBetween: 1,
          type: 'natural',
        },
      ],
      // Disable object property sorting - semantic grouping matters more
      'perfectionist/sort-objects': 'off',
    },
  },

  // Language options for TypeScript (non-test files)
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    ignores: ['**/*.test.ts', '**/*.test.tsx'],
    languageOptions: {
      ecmaVersion: 2025,
      globals: { ...globals.node },
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: import.meta.dirname,
      },
      sourceType: 'module',
    },
  },

  // Language options for test files (use tsconfig.test.json)
  {
    files: ['**/*.test.ts', '**/*.test.tsx'],
    languageOptions: {
      ecmaVersion: 2025,
      globals: { ...globals.node },
      parserOptions: {
        project: './tsconfig.test.json',
        tsconfigRootDir: import.meta.dirname,
      },
      sourceType: 'module',
    },
  },

  // Language options for config files (use default project service)
  {
    files: ['*.mjs'],
    languageOptions: {
      ecmaVersion: 2025,
      globals: { ...globals.node },
      parserOptions: {
        projectService: {
          allowDefaultProject: ['*.mjs'],
          defaultProject: 'tsconfig.json',
        },
        tsconfigRootDir: import.meta.dirname,
      },
      sourceType: 'module',
    },
  },

  // Naming conventions - CRITICAL for consistency
  {
    rules: {
      // Code identifier naming conventions
      '@typescript-eslint/naming-convention': [
        'error',
        // Default: camelCase for most identifiers
        { format: ['camelCase'], selector: 'default' },
        // Variables: camelCase, UPPER_CASE, or PascalCase (React components)
        {
          format: ['camelCase', 'UPPER_CASE', 'PascalCase'],
          selector: 'variable',
        },
        // Functions: camelCase or PascalCase (React components)
        {
          format: ['camelCase', 'PascalCase'],
          selector: 'function',
        },
        // Parameters: camelCase, allow leading underscore for unused
        {
          format: ['camelCase'],
          leadingUnderscore: 'allow',
          selector: 'parameter',
        },
        // Class, interface, type, enum: PascalCase (NO "I" prefix!)
        { format: ['PascalCase'], selector: 'typeLike' },
        // Enum members: UPPER_CASE
        { format: ['UPPER_CASE'], selector: 'enumMember' },
        // Object literal properties: flexible (external APIs)
        { format: null, selector: 'objectLiteralProperty' },
        // Imports: flexible (can't control external packages)
        { format: null, selector: 'import' },
      ],
      // Allow null - APIs use null semantically
      'unicorn/no-null': 'off',
      // Allow 'DevPod' as it's a product name, not an abbreviation
      'unicorn/prevent-abbreviations': [
        'error',
        {
          allowList: {
            DevPod: true,
            devpod: true,
            DevPodStatus: true,
            formatDevPodStatus: true,
          },
        },
      ],
    },
  },

  // React plugin configuration for .tsx files
  {
    files: ['src/**/*.tsx'],
    plugins: {
      react: pluginReact,
      'react-hooks': pluginReactHooks,
    },
    rules: {
      ...pluginReact.configs.recommended.rules,
      ...pluginReactHooks.configs.recommended.rules,
      // React 19 doesn't require importing React
      'react/react-in-jsx-scope': 'off',
      // Props validation handled by TypeScript
      'react/prop-types': 'off',
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },

  // React component files: PascalCase (matches exported component name)
  {
    files: ['src/components/**/*.tsx'],
    rules: {
      'unicorn/filename-case': ['error', { case: 'pascalCase' }],
    },
  },

  // Other TypeScript files: camelCase
  {
    files: ['**/*.{ts,tsx,mjs}'],
    ignores: ['src/components/**/*.tsx'],
    rules: {
      'unicorn/filename-case': ['error', { case: 'camelCase' }],
    },
  },

  // Configuration files - relax rules
  {
    files: ['*.config.{mjs,js,ts}'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
    },
  },

  // Test files configuration
  {
    files: ['**/*.test.{ts,tsx}', '**/__tests__/**/*.{ts,tsx}'],
    rules: {
      // Relax type safety in tests for mocks and fixtures
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
      // Test-specific sonarjs overrides
      'sonarjs/no-nested-functions': 'off',
    },
  },

  // Files or directories to ignore
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },

  // Prettier config - MUST be last to disable rules that conflict with Prettier
  eslintConfigPrettier,
];

export default eslintConfig;
