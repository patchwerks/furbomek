import { createApp } from 'vue';
import App from './App.vue';
import LiveStudio from './LiveStudio.vue';
import './style.css';
createApp(new URLSearchParams(location.search).get('mode') === 'live' ? LiveStudio : App).mount('#app');
