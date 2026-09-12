<script setup lang="ts">
const navigation = [
  { to: '/', label: '总览', icon: '◉' },
  { to: '/monitor', label: '实时监测', icon: '⌁' },
  { to: '/models', label: '模型中心', icon: '◈' },
  { to: '/diagnostics', label: '辅助诊断', icon: '⌘' },
  { to: '/alarms', label: '报警中心', icon: '!' },
  { to: '/history', label: '历史事件', icon: '◷' },
  { to: '/edge', label: '边缘与回放', icon: '↗' },
]
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">◈</span><div><strong>OilWell AI</strong><small>EDGE · CLOUD · INSIGHT</small></div></div>
      <nav aria-label="主导航"><RouterLink v-for="item in navigation" :key="item.to" :to="item.to"><span>{{ item.icon }}</span>{{ item.label }}</RouterLink></nav>
      <div class="sidebar-foot">教学演示系统<br /><small>AI 仅作教学辅助</small></div>
    </aside>
    <section class="workspace"><header><div><p class="eyebrow">石油智能信息系统工程</p><h1>油井异常监测</h1></div><div class="clock">边云协同监测</div></header><RouterView /></section>
  </main>
</template>
