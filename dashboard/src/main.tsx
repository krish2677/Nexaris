import { Buffer } from 'buffer'
;(window as any).Buffer = Buffer

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import SolanaWalletProvider from './WalletProvider'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SolanaWalletProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </SolanaWalletProvider>
  </StrictMode>,
)
