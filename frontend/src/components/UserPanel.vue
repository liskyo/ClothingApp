<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Cloth {
  id: string
  name: string
  image_url: string
  height_range: string
  gender: string
  style: string
}

const clothes = ref<Cloth[]>([])
const userHeight = ref('')
const userGender = ref('中性')
const userFile = ref<File | null>(null)
const userPhotoPreview = ref<string | null>(null)
const selectedCloth = ref<Cloth | null>(null)
const tryOnResult = ref<string | null>(null)
const loading = ref(false)

const fetchClothes = async () => {
  try {
    // Applying basic filters on fetch
    // Note: Backend supports query params, but we can also filter client side for better experience if list is small.
    // Let's use backend params roughly
    const params = new URLSearchParams()
    if (userGender.value && userGender.value !== '中性') params.append('gender', userGender.value)
    if (userHeight.value) params.append('height', userHeight.value)
    
    const res = await axios.get('/api/clothes', { params })
    clothes.value = res.data
  } catch (err) {
    console.error(err)
    alert('無法連線到伺服器，請確認後端是否已啟動。')
  }
}

const onUserFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    userFile.value = target.files[0]
    userPhotoPreview.value = URL.createObjectURL(target.files[0])
  }
}

const tryOn = async (cloth: Cloth) => {
  selectedCloth.value = cloth
  if (!userFile.value) {
    alert('請先上傳您的全身照')
    return
  }
  
  loading.value = true
  tryOnResult.value = null
  
  const formData = new FormData()
  formData.append('file', userFile.value)
  formData.append('clothes_id', cloth.id.replace('.jpg', '')) // Make sure ID is just the code
  
  try {
    const res = await axios.post('/api/try-on', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob'
    })
    
    tryOnResult.value = URL.createObjectURL(res.data)
  } catch (err) {
    console.error(err)
    alert('試穿失敗')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchClothes()
})
</script>

<template>
  <div class="space-y-12">
    <!-- User Info Section -->
    <section class="glass-panel p-8 rounded-2xl relative overflow-hidden">
      <div class="absolute top-0 right-0 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
      
      <h2 class="text-2xl font-bold mb-6 text-white flex items-center">
        <span class="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-sm mr-3">1</span>
        Create Your Profile
      </h2>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 items-end">
        <div>
           <label class="block text-sm font-medium text-slate-400 mb-2">Your Height (cm)</label>
           <input v-model="userHeight" @change="fetchClothes" type="text" class="input-tech w-full px-4 py-3" placeholder="e.g. 160">
        </div>
        <div>
           <label class="block text-sm font-medium text-slate-400 mb-2">Gender Preference</label>
           <select v-model="userGender" @change="fetchClothes" class="input-tech w-full px-4 py-3 appearance-none">
             <option class="bg-slate-800">中性</option>
             <option class="bg-slate-800">女性</option>
             <option class="bg-slate-800">男性</option>
           </select>
        </div>
        <div class="group">
           <label class="block text-sm font-medium text-slate-400 mb-2">Upload Full Body Photo</label>
           
           <label class="relative block w-full aspect-[3/4] border-2 border-dashed border-slate-600 rounded-xl cursor-pointer hover:border-purple-500 hover:bg-slate-800/50 transition-all overflow-hidden bg-slate-900/50 group/upload">
             
             <!-- Preview Image -->
             <img v-if="userPhotoPreview" :src="userPhotoPreview" class="absolute inset-0 w-full h-full object-cover" />
             
             <!-- Placeholder Content (hidden if preview exists) -->
             <div v-if="!userPhotoPreview" class="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                 <div class="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-3 text-purple-400 group-hover/upload:scale-110 transition-transform">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                 </div>
                 <span class="text-sm text-slate-300 font-medium">Click to Upload</span>
                 <span class="text-xs text-slate-500 mt-1">Full body shot recommended</span>
             </div>

             <!-- Overlay to indicate changeability when hovered -->
             <div v-if="userPhotoPreview" class="absolute inset-0 bg-black/50 opacity-0 group-hover/upload:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-sm">
                <span class="text-white font-medium flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                    Change Photo
                </span>
             </div>

             <input type="file" @change="onUserFileChange" accept="image/*" class="hidden"/>
           </label>
        </div>
      </div>
    </section>

    <!-- Gallery Section -->
    <section>
      <h2 class="text-2xl font-bold mb-6 text-white flex items-center">
        <span class="w-8 h-8 rounded-full bg-pink-500 flex items-center justify-center text-sm mr-3">2</span>
        Select to Try-On
      </h2>
      
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        <div v-for="cloth in clothes" :key="cloth.id" class="group relative bg-slate-800/40 rounded-2xl overflow-hidden border border-white/5 hover:border-purple-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-purple-500/20 hover:-translate-y-2">
           <!-- Image -->
           <div class="aspect-[3/4] w-full overflow-hidden bg-slate-900 relative">
             <img :src="cloth.image_url" :alt="cloth.name" class="h-full w-full object-cover object-center transition-transform duration-700 group-hover:scale-110">
             <div class="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent opacity-60"></div>
           </div>
           
           <!-- Content -->
           <div class="absolute bottom-0 inset-x-0 p-4 translate-y-2 group-hover:translate-y-0 transition-transform">
             <div class="flex justify-between items-end">
               <div>
                 <h3 class="text-lg font-bold text-white leading-tight mb-1">{{ cloth.name }}</h3>
                 <p class="text-sm text-purple-300">{{ cloth.style }}</p>
               </div>
               <span class="text-xs bg-white/10 px-2 py-1 rounded text-slate-300">{{ cloth.gender }}</span>
             </div>
             
             <button @click="tryOn(cloth)" class="w-full mt-4 bg-white text-indigo-900 font-bold py-2 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity transform translate-y-4 group-hover:translate-y-0 duration-300">
               Virtual Try On
             </button>
           </div>
        </div>
      </div>
      
      <div v-if="clothes.length === 0" class="text-center py-20 bg-slate-800/30 rounded-3xl border border-dashed border-slate-700">
        <p class="text-slate-500 text-lg">No clothes found holding these filters.</p>
      </div>
    </section>

    <!-- Try-On Result Modal -->
    <transition name="modal">
      <div v-if="loading || tryOnResult" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/90 backdrop-blur-sm" @click="tryOnResult = null"></div>
        
        <!-- Content -->
        <div class="relative bg-slate-800 border border-white/10 rounded-2xl shadow-2xl max-w-lg w-full p-1 overflow-hidden">
          <div class="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-8 text-center relative">
             <div v-if="loading">
               <div class="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
               <h3 class="text-xl font-bold text-white animate-pulse">AI Magic in Progress...</h3>
               <p class="text-slate-400 mt-2">Synthesizing virtual fit</p>
             </div>
             
             <div v-else>
               <h3 class="text-2xl font-bold text-white mb-6">Your New Look</h3>
               <div class="relative rounded-xl overflow-hidden shadow-2xl border border-white/10 mb-8 group">
                 <img :src="tryOnResult!" class="w-full object-cover" />
                 <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
               </div>
               
               <div class="flex gap-4">
                  <button @click="tryOnResult = null" class="flex-1 py-3 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 font-medium transition">
                    Close
                  </button>
                  <a :href="tryOnResult!" download="try-on.jpg" class="flex-1 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-pink-500 text-white font-bold shadow-lg hover:shadow-indigo-500/25 transition">
                    Download
                  </a>
               </div>
             </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
