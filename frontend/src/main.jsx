import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { systemTheme, themeFromStorage } from './hooks/useTheme'
import './styles/global.css'

// Theme the very first paint (before React runs) so there is no
// flash of the wrong theme — respects a saved choice, else the OS.
{
  const theme = themeFromStorage() || systemTheme()
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
