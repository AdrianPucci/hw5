import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Start the board with `npm run dev` (http://localhost:5173). The page calls the FastAPI back end
// directly at http://localhost:8000 (src/api.ts); the back end allows this origin with CORS.
export default defineConfig({
  plugins: [react()],
})
