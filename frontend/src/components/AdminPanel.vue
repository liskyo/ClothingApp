<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const file = ref<File | null>(null)
const heightRange = ref('')
const gender = ref('中性')
const uploadStatus = ref('')
const result = ref<any>(null)

// Manage List Logic
const clothesList = ref<any[]>([])
const loadingList = ref(false)
const editingItem = ref<any>(null)
const previewUrl = ref('')

const fetchClothes = async () => {
  loadingList.value = true
  try {
    const res = await axios.get('/api/clothes')
    clothesList.value = res.data
  } catch (e) {
    console.error("Failed to fetch clothes", e)
  } finally {
    loadingList.value = false
  }
}

onMounted(() => {
  fetchClothes()
})

const deleteItem = async (id: string) => {
  if(!confirm("Are you sure you want to delete this item? This cannot be undone.")) return
  
  try {
    await axios.delete(`/api/clothes/${id}`)
    clothesList.value = clothesList.value.filter(item => item.id !== id)
  } catch (e) {
    alert("Delete failed.")
    console.error(e)
  }
}

const openEdit = (item: any) => {
  editingItem.value = { ...item }
}

const saveEdit = async () => {
  if(!editingItem.value) return
  
  try {
    await axios.put(`/api/clothes/${editingItem.value.id}`, editingItem.value)
    const index = clothesList.value.findIndex(c => c.id === editingItem.value.id)
    if(index !== -1) {
      clothesList.value[index] = { ...editingItem.value }
    }
    editingItem.value = null
  } catch (e) {
    alert("Update failed.")
    console.error(e)
  }
}

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    file.value = target.files[0]
    previewUrl.value = URL.createObjectURL(file.value)
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
    fetchClothes()
  } catch (err) {
    console.error(err)
    uploadStatus.value = 'Error uploading.'
  }
}
</script>

<template>
  <div class="glass-panel p-8 rounded-2xl max-w-4xl mx-auto">
    <h2 class="text-3xl font-bold mb-8 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
      Upload New Clothing
    </h2>
    
    <div class="space-y-6 mb-12">
      <!-- Upload Section -->
      <div class="group">
        <label class="block text-sm font-medium text-slate-400 mb-2">Upload Image</label>
        <div class="relative border-2 border-dashed border-slate-600 rounded-xl p-8 transition-colors group-hover:border-purple-500/50 bg-slate-800/20 text-center overflow-hidden">
          <input type="file" @change="onFileChange" accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"/>
          
          <div v-if="previewUrl" class="absolute inset-0 w-full h-full bg-slate-900 z-0">
             <img :src="previewUrl" class="w-full h-full object-contain" />
          </div>

          <div v-else class="space-y-2 relative z-0">
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

    <!-- Edit/Delete Section -->
    <div class="border-t border-white/10 pt-10">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-white">Manage Clothes</h2>
        <button @click="fetchClothes" class="text-sm px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh List
        </button>
      </div>
      <div v-if="loadingList" class="text-center text-slate-400">Loading list...</div>
      
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="item in clothesList" :key="item.id" class="relative group bg-slate-800/40 rounded-xl overflow-hidden border border-white/5 hover:border-purple-500/30 transition-all">
          <div class="aspect-[3/4] relative overflow-hidden bg-slate-900">
             <img :src="item.image_url" class="w-full h-full object-cover transition duration-500 group-hover:scale-110" loading="lazy">
             <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center p-4 gap-2">
                <button @click="openEdit(item)" class="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg text-sm">Edit</button>
                <button @click="deleteItem(item.id)" class="bg-red-600 hover:bg-red-500 text-white p-2 rounded-lg text-sm">Delete</button>
             </div>
          </div>
          <div class="p-4">
            <h3 class="font-bold text-white truncate">{{ item.name }}</h3>
            <p class="text-sm text-slate-400">{{ item.style }}</p>
             <p class="text-xs text-slate-500 mt-1">{{ item.gender }} · {{ item.height_range }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="editingItem" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div class="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-4">Edit Clothing</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Name</label>
            <input v-model="editingItem.name" type="text" class="input-tech w-full px-3 py-2 text-sm">
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Style</label>
            <input v-model="editingItem.style" type="text" class="input-tech w-full px-3 py-2 text-sm">
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-slate-400 mb-1">Height Range</label>
              <input v-model="editingItem.height_range" type="text" class="input-tech w-full px-3 py-2 text-sm">
            </div>
            <div>
              <label class="block text-sm text-slate-400 mb-1">Gender</label>
              <select v-model="editingItem.gender" class="input-tech w-full px-3 py-2 text-sm appearance-none">
                 <option class="bg-slate-800">中性</option>
                 <option class="bg-slate-800">女性</option>
                 <option class="bg-slate-800">男性</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-8">
          <button @click="editingItem = null" class="px-4 py-2 text-slate-400 hover:text-white transition">Cancel</button>
          <button @click="saveEdit" class="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition">Save Changes</button>
        </div>
      </div>
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
