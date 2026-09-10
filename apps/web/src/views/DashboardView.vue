<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDashboard, getDevices } from '../api'

const dashboard = ref({ wells: 0, online_devices: 0, active_alarms: 0 })
const devices = ref<{ id: string; status: string; last_heartbeat: string | null }[]>([])
const error = ref('')

onMounted(async () => {
  try {
    const [dashboardData, deviceData] = await Promise.all([getDashboard(), getDevices()])
    dashboard.value = dashboardData
    devices.value = deviceData
  }
  catch { error.value = '尚未连接到云端 API。启动 Compose 后将自动显示实时数据。' }
})
</script>

<template>
  <div class="view">
    <div class="view-title"><div><h2>运行概览</h2><p>边云协同链路与当前油井状态</p></div><span v-if="error" class="hint">{{ error }}</span></div>
    <section class="metric-grid"><article><span>受监测油井</span><strong>{{ dashboard.wells }}</strong><small>已接入时序数据</small></article><article><span>在线边缘设备</span><strong>{{ dashboard.online_devices }}</strong><small>心跳持续更新</small></article><article class="alarm-card"><span>待确认报警</span><strong>{{ dashboard.active_alarms }}</strong><small>需要人工核验</small></article></section>
    <section class="two-column"><article class="panel flow-panel"><div class="panel-head"><h3>数据链路</h3><span>180 秒窗口</span></div><div class="flow"><b>3W Parquet</b><i>→</i><b>Pi Edge</b><i>→</i><b>MQTT / TLS</b><i>→</i><b>Cloud API</b><i>→</i><b>Dashboard</b></div><p>训练、模型评估与完整数据集保留在本机；ECS 仅接收实时回放和执行轻量推理。</p></article><article class="panel"><div class="panel-head"><h3>边缘设备</h3><RouterLink to="/edge">管理回放</RouterLink></div><div v-if="devices.length" class="device-list"><div v-for="device in devices" :key="device.id"><span class="online-dot"></span><b>{{ device.id }}</b><span>{{ device.status }}</span><time>{{ device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString() : '等待心跳' }}</time></div></div><p v-else class="empty">等待树莓派连接 MQTT 并发送心跳。</p></article></section>
  </div>
</template>
