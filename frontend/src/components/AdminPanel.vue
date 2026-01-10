<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const file = ref<File | null>(null)
const heightRange = ref('')
const gender = ref('中性')
const uploadStatus = ref('')
const result = ref<any>(null)

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files) {
    file.value = target.files[0]
  }
}

const upload = async () => {
  if (!file.value || !heightRange.value) {
    alert('請填寫完整資訊')
    return
  }

  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('height_range', heightRange.value)
  formData.append('gender', gender.value)

  uploadStatus.value = 'Analyzing...'
  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    result.value = res.data
    uploadStatus.value = 'Upload Successful!'
  } catch (err) {
    console.error(err)
    uploadStatus.value = 'Error uploading.'
  }
}
</script>

<template>
  <div class="glass-panel p-8 rounded-2xl max-w-2xl mx-auto">
    <h2 class="text-3xl font-bold mb-8 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
      Upload New Clothing
    </h2>
    
    <div class="space-y-6">
      <div class="group">
        <label class="block text-sm font-medium text-slate-400 mb-2">Upload Image</label>
        <div class="relative border-2 border-dashed border-slate-600 rounded-xl p-8 transition-colors group-hover:border-purple-500/50 bg-slate-800/20 text-center">
          <input type="file" @change="onFileChange" accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"/>
          <div class="space-y-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto text-slate-400 group-hover:text-purple-400 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="text-slate-400 group-hover:text-white transition">Click to upload or drag and drop</p>
          </div>
        </div>
        <p v-if="file" class="mt-2 text-sm text-purple-400 font-medium">Selected: {{ file.name }}</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="block text-sm font-medium text-slate-400 mb-2">Height Range</label>
          <input v-model="heightRange" type="text" class="input-tech w-full px-4 py-3" placeholder="e.g. 150-165cm">
        </div>

        <div>
           <label class="block text-sm font-medium text-slate-400 mb-2">Gender Category</label>
           <select v-model="gender" class="input-tech w-full px-4 py-3 appearance-none">
             <option class="bg-slate-800">中性</option>
             <option class="bg-slate-800">女性</option>
             <option class="bg-slate-800">男性</option>
           </select>
        </div>
      </div>

      <button @click="upload" class="btn-tech w-full py-3 mt-4 text-lg">
        AI Analyze & Upload
      </button>

      <!-- Status & Results -->
      <transition name="fade">
        <div v-if="uploadStatus" class="mt-6 p-4 rounded-lg bg-slate-800/50 text-center border border-white/5">
          <p :class="uploadStatus.includes('Error') ? 'text-red-400' : 'text-emerald-400'" class="font-medium">
            {{ uploadStatus }}
          </p>
        </div>
      </transition>

      <transition name="fade">
        <div v-if="result" class="mt-8 border-t border-white/10 pt-6">
          <h3 class="text-xl font-bold mb-4 text-white">Analysis Result</h3>
          <dl class="grid grid-cols-2 gap-4">
            <div class="bg-slate-800/40 p-4 rounded-xl">
              <dt class="text-xs text-slate-400 uppercase tracking-wider">Name</dt>
              <dd class="mt-1 text-lg font-medium text-white">{{ result.name }}</dd>
            </div>
            <div class="bg-slate-800/40 p-4 rounded-xl">
              <dt class="text-xs text-slate-400 uppercase tracking-wider">Style</dt>
              <dd class="mt-1 text-lg font-medium text-purple-300">{{ result.style }}</dd>
            </div>
          </dl>
          <div class="mt-4 text-center">
            <span class="text-xs text-slate-500">ID: {{ result.id }}</span>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
