/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      spacing: {
        22: '5.5rem',   // 88px
        24: '6rem',     // 96px
        26: '6.5rem',   // 104px
        28: '7rem',     // 112px
        30: '7.5rem',   // 120px
        32: '8rem',     // 128px
        36: '9rem',     // 144px
      },
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
