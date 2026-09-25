import { createApp } from 'vue'
import naive from 'naive-ui'

import App from './App.vue'
import router from './router'

import './assets/main.css'
import './echarts'
import 'vfonts/Lato.css'
import 'vfonts/FiraCode.css'

const app = createApp(App)
app.use(naive)
app.use(router)
app.mount('#app')
