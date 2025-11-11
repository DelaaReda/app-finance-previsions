module.exports = {
  // root: true is omitted to remain compatible with the ESLint flat config loader
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended'
  ],
  settings: {
    react: { version: 'detect' }
  },
  rules: {
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'react/react-in-jsx-scope': 'off',
    'react/jsx-uses-react': 'off',
    'no-restricted-imports': ['error', {
      patterns: ['@mui/*'],
      paths: [
        { name: '@mui/material', message: 'Utilise les composants Mantine via @/ui' },
        { name: '@mui/icons-material', message: 'Utilise @tabler/icons-react' }
      ]
    }]
  }
};
