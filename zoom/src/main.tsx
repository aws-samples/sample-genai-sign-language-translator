import React from 'react'
import { createRoot } from 'react-dom/client'
import ZoomApp from './components/ZoomApp'
import './index.css'

const root = createRoot(document.getElementById('root')!)
root.render(<ZoomApp />)
