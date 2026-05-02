import { createApp } from 'vue'
import App from './App.vue'

// Theme system
import './themes/base.css'
import './themes/tokens/cosmic-purple.css'
import './themes/tokens/clean-light.css'
import './themes/tokens/candy-pastel.css'
import './themes/tokens/liquid-glass.css'
import './themes/tokens/twilight-gradient.css'
import './themes/tokens/neon-city.css'
import './themes/tokens/vaporwave.css'
import './themes/tokens/sakura-bloom.css'
import './themes/tokens/ocean-abyss.css'
import './themes/tokens/lava-ember.css'
import './themes/tokens/neumorphism-light.css'
import './themes/tokens/neumorphism-dark.css'

document.documentElement.setAttribute('data-theme', 'cosmic-purple')

createApp(App).mount('#app')
