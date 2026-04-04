import { createApp } from 'vue';
import { createPinia } from 'pinia';
import PrimeVue from 'primevue/config';
import Aura from '@primevue/themes/aura';
import App from './App.vue';
import router from './router';
import './styles/variables.css';
import './assets/main.css'; // 确保在这里引入

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      // 关键：将 PrimeVue 样式放在 css 层级中，方便 Tailwind 覆盖
      cssLayer: {
        name: 'primevue',
        order: 'tailwind-base, primevue, tailwind-utilities',
      },
      darkModeSelector: '.dark',
    },
  },
});

app.use(router);

app.mount('#app');
