/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'mc-green': '#8BC34A',
        'mc-green-hover': '#7CB342',
        'mc-orange': '#FF9800',
        'mc-orange-light': '#FFF3E0',
        'mc-gray-bg': '#F5F5F5',
        'mc-gray-border': '#E0E0E0',
        'mc-gray-text': '#757575',
        'mc-dark-text': '#424242',
        'mc-sidebar-bg': '#FAFAFA',
        'mc-sidebar-hover': '#F0F0F0',
        'mc-section-header': '#EEEEEE',
        'mc-header-bg': '#F5F5F5',
      },
      fontFamily: {
        sans: ['Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
