import { Toaster } from '@/components/ui/toaster'
import { ThemeProvider } from '@/components/theme-provider'
import { UnifiedInterface } from '@/components/UnifiedInterface'

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <div className="min-h-screen bg-background">
        <UnifiedInterface />
        <Toaster />
      </div>
    </ThemeProvider>
  )
}

export default App 