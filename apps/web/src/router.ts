import { createRouter, createWebHistory } from 'vue-router'
const AlarmsView = () => import('./views/AlarmsView.vue')
const DashboardView = () => import('./views/DashboardView.vue')
const DiagnosticsView = () => import('./views/DiagnosticsView.vue')
const EdgeView = () => import('./views/EdgeView.vue')
const MonitorView = () => import('./views/MonitorView.vue')
const ModelCenterView = () => import('./views/ModelCenterView.vue')

const HistoryView = () => import('./views/HistoryView.vue')

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/monitor', component: MonitorView },
    { path: '/models', component: ModelCenterView },
    { path: '/diagnostics', component: DiagnosticsView },
    { path: '/alarms', component: AlarmsView },
    { path: '/edge', component: EdgeView },
    { path: '/history', component: HistoryView },
  ],
})
