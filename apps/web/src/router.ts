import { createRouter, createWebHistory } from 'vue-router'
import AlarmsView from './views/AlarmsView.vue'
import DashboardView from './views/DashboardView.vue'
import EdgeView from './views/EdgeView.vue'
import MonitorView from './views/MonitorView.vue'
import ModelCenterView from './views/ModelCenterView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/monitor', component: MonitorView },
    { path: '/models', component: ModelCenterView },
    { path: '/alarms', component: AlarmsView },
    { path: '/edge', component: EdgeView },
  ],
})
