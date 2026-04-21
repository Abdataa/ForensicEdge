// postcss.config.js
// Tailwind CSS v3 PostCSS plugin configuration.
// Do NOT use "@tailwindcss/postcss" — that is the v4 plugin.

module.exports = {
  plugins: {
    tailwindcss:  {},   // v3: the main package IS the postcss plugin
    autoprefixer: {},
  },
};