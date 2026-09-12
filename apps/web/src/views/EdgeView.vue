<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { command, getDevices, type Device } from '../api'
const devices = ref<Device[]>([])
const message = ref('')
const speed = ref(10)
const selected = ref<Record<string, string>>({})
const pending = ref<Record<string, string>>({})
const deadlines: Record<string, number> = {}
let timer: ReturnType<typeof setInterval> | undefined
function instances(device: Device): string[] {
  return Array.isArray(device.metrics.available_instances) ? device.metrics.available_instances.filter((x): x is string => typeof x === 'string') : []
}
async function load() {
  try {
    devices.value = await getDevices()
    for (const device of devices.value) {
      const id = pending.value[device.id]
      if (!id) continue
      const ack = device.metrics.last_command as { command_id?: string; command?: string; status?: string; reason?: string } | undefined
      if (ack?.command_id === id) {
        message.value = ack.status === 'applied' ? `${device.id} 已执行 ${ack.command}` : `${device.id} 拒绝执行：${ack.reason ?? '请检查回放状态'}`
        delete pending.value[device.id]
      } else if (Date.now() > deadlines[device.id]!) {
        message.value = `${device.id} 尚未确认执行，请检查设备连接后刷新状态。`
        delete pending.value[device.id]
      }
    }
  } catch { message.value = '暂时无法获取边缘设备状态。' }
}
async function send(deviceId: string, payload: Record<string, unknown>) {
  if (pending.value[deviceId]) return
  try {
    const result = await command(deviceId, payload)
    pending.value[deviceId] = result.command_id
    deadlines[deviceId] = Date.now() + 15000
    message.value = `${payload.command} 已发送，等待 ${deviceId} 确认。`
    await load()
  } catch { message.value = '指令未发送，请检查连接与输入。' }
}
onMounted(() => { void load(); timer = setInterval(() => { void load() }, 2000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
<template>
  <div class="view">
    <div class="view-title"><div><h2>边缘设备与数据回放</h2><p>选择已挂载的教学实例，等待设备确认每次操作。</p></div><button class="secondary" @click="load">刷新状态</button></div>
    <p v-if="message" class="hint" role="status">{{ message }}</p>
    <section v-if="devices.length" class="edge-grid">
      <article v-for="device in devices" :key="device.id" class="panel edge-card">
        <div class="panel-head"><h3>{{ device.id }}</h3><span>{{ device.status }}</span></div>
        <dl><dt>最后心跳</dt><dd>{{ device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleString() : '—' }}</dd><dt>当前速度</dt><dd>{{ device.metrics.speed ?? '—' }}×</dd><dt>回放实例</dt><dd>{{ device.metrics.instance ?? '尚未加载' }}</dd></dl>
        <fieldset :disabled="Boolean(pending[device.id]) || device.status === 'OFFLINE'" style="border:0;padding:0;margin:0">
          <div class="controls"><button @click="send(device.id, { command: 'START' })">开始</button><button class="secondary" @click="send(device.id, { command: 'PAUSE' })">暂停</button><button class="secondary" @click="send(device.id, { command: 'STOP' })">停止</button></div>
          <div class="speed"><label>回放速度 <select v-model="speed"><option v-for="item in [1,5,10,20]" :key="item" :value="item">{{ item }}×</option></select></label><button @click="send(device.id, { command: 'SET_SPEED', speed })">应用</button></div>
          <div class="speed"><label>教学实例 <select v-model="selected[device.id]"><option disabled value="">请选择实例</option><option v-for="item in instances(device)" :key="item" :value="item">{{ item }}</option></select></label><button :disabled="!selected[device.id] || device.status === 'REPLAYING' || device.status === 'PAUSED'" @click="send(device.id, { command: 'LOAD_INSTANCE', instance: selected[device.id] })">加载实例</button></div>
          <p class="hint">切换实例前请先停止当前回放。</p>
        </fieldset>
      </article>
    </section>
    <section v-else class="panel empty">等待树莓派 Edge Agent 上线。</section>
  </div>
</template>
