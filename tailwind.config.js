/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./core/**/*.py",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', "Segoe UI", 'Roboto', "Helvetica Neue", 'sans-serif'],
            },
            colors: {
                'apple-blue': '#007AFF',
                'apple-teal': '#5AC8FA',
                'apple-slate': '#1D1D1F',
                'apple-gray': '#F5F5F7',
            },
        }
    },
    plugins: [],
}
