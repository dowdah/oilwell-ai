<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { acknowledge, getAlarms, type Alarm } from '../api'
const alarms = ref<Alarm[]>([]); const error = ref('')
async function load() { try { alarms.value = await getAlarms() } catch { error.value = '无法读取报警数据。' } }
async function ack(id: number) { const updated = await acknowledge(id); alarms.value = alarms.value.map((alarm) => alarm.id === id ? updated : alarm) }
onMounted(load)
</script>
<template><div class="view"><div class="view-title"><div><h2>报警中心</h2><p>异常事件需要人工确认；模型结果不直接控制现场设备</p></div><button class="secondary" @click="load">刷新</button></div><p v-if="error" class="hint">{{ error }}</p><section class="panel table-panel"><table><thead><tr><th>时间</th><th>油井</th><th>事件</th><th>严重度</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="alarm in alarms" :key="alarm.id"><td>{{ new Date(alarm.raised_at).toLocaleString() }}</td><td>{{ alarm.well_id }}</td><td><b>{{ alarm.event_type }}</b><small>{{ alarm.message }}</small></td><td><span class="severity">{{ alarm.severity }}</span></td><td>{{ alarm.status }}</td><td><button v-if="alarm.status === 'UNACKNOWLEDGED'" @click="ack(alarm.id)">确认</button></td></tr><tr v-if="!alarms.length"><td colspan="6" class="empty">暂无报警。带有非 Normal event hint 的回放数据会触发教学演示报警。</td></tr></tbody></table></section></div></template>
