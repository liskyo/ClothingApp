<script setup lang="ts">
import { ref } from 'vue'
import AdminPanel from './components/AdminPanel.vue'
import UserPanel from './components/UserPanel.vue'

const currentView = ref('user') // 'admin' or 'user'
</script>

<template>
  <div class="min-h-screen text-slate-200 selection:bg-purple-500 selection:text-white">
    <!-- Navbar -->
    <nav class="sticky top-0 z-50 glass-panel border-b border-white/10">
      <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 bg-gradient-to-tr from-purple-500 to-pink-500 rounded-lg flex items-center justify-center shadow-lg shadow-purple-500/30">
            <span class="text-white font-bold text-lg">AI</span>
          </div>
          <h1 class="text-2xl font-bold tracking-tight text-white">
            Virtual<span class="text-purple-400">TryOn</span>
          </h1>
        </div>
        
        <div class="flex space-x-2 bg-slate-800/50 p-1 rounded-xl border border-white/5">
          <button 
            @click="currentView = 'user'"
            class="px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300"
            :class="currentView === 'user' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-white/5'"
          >
            使用者試穿 (User)
          </button>
          <button 
            @click="currentView = 'admin'"
            class="px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300"
            :class="currentView === 'admin' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-white/5'"
          >
            管理員 (Admin)
          </button>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-6 py-10 fade-enter-active">
      <transition name="fade" mode="out-in">
        <div v-if="currentView === 'admin'" key="admin">
          <AdminPanel />
        </div>
        <div v-else key="user">
          <UserPanel />
        </div>
      </transition>
    </main>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
