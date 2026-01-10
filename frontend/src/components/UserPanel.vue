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
  <div class="space-y-8">
    <!-- Studio Control Panel -->
    <section class="glass-panel p-6 rounded-2xl relative overflow-hidden">
      <!-- Background Effect -->
      <div class="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>

      <div class="space-y-6">
         <!-- Top Controls: Inputs line up -->
         <div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
            <!-- Height -->
            <div>
               <label class="block text-sm font-medium text-slate-400 mb-2">Height (cm)</label>
               <input v-model="userHeight" @change="fetchClothes" type="text" class="input-tech w-full px-4 py-3" placeholder="e.g. 160">
            </div>
            
            <!-- Gender -->
            <div>
               <label class="block text-sm font-medium text-slate-400 mb-2">Gender Preference</label>
               <select v-model="userGender" @change="fetchClothes" class="input-tech w-full px-4 py-3 appearance-none">
                 <option class="bg-slate-800">中性</option>
                 <option class="bg-slate-800">女性</option>
                 <option class="bg-slate-800">男性</option>
               </select>
            </div>
            
            <!-- File Upload (Showing Filename) -->
            <div>
               <label class="block text-sm font-medium text-slate-400 mb-2">Upload Photo</label>
               <label class="flex items-center justify-between w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl cursor-pointer hover:border-purple-500 transition-colors group">
                  <span class="text-slate-300 truncate mr-2">{{ userFile ? userFile.name : 'Choose a full body photo...' }}</span>
                  <div class="bg-slate-700 text-xs px-2 py-1 rounded text-white group-hover:bg-purple-600 transition-colors">Browse</div>
                  <input type="file" @change="onUserFileChange" accept="image/*" class="hidden"/>
               </label>
            </div>
         </div>

         <!-- Lower Block: Split View Studio -->
         <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <!-- Left: User Preview -->
            <div class="relative aspect-[3/4] bg-slate-900/50 rounded-2xl border border-dashed border-slate-700 flex items-center justify-center overflow-hidden">
                <p v-if="!userPhotoPreview" class="text-slate-500 flex flex-col items-center">
                   <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                   <span>User Photo Preview</span>
                </p>
                <img v-else :src="userPhotoPreview" class="w-full h-full object-cover" />
                <div class="absolute top-3 left-3 bg-black/50 backdrop-blur px-3 py-1 rounded-full text-xs text-white">Your Photo</div>
            </div>

            <!-- Right: Try-On Result -->
            <div class="relative aspect-[3/4] bg-slate-900/50 rounded-2xl border border-dashed border-slate-700 flex items-center justify-center overflow-hidden">
                <!-- Placeholder / Loading / Result -->
                
                <!-- State 1: Loading -->
                <div v-if="loading" class="absolute inset-0 z-10 bg-slate-900/80 backdrop-blur flex flex-col items-center justify-center">
                     <div class="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                     <span class="text-indigo-400 font-bold animate-pulse">Designing New Look...</span>
                </div>

                <!-- State 2: Result exists -->
                <div v-if="tryOnResult" class="w-full h-full relative group">
                    <img :src="tryOnResult" class="w-full h-full object-cover" />
                    <div class="absolute bottom-4 right-4 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <a :href="tryOnResult" download="try-on.jpg" class="bg-indigo-600 hover:bg-indigo-500 text-white p-2 rounded-lg shadow-lg">
                           <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        </a>
                    </div>
                </div>

                <!-- State 3: Nothing yet -->
                <div v-else-if="!loading" class="text-slate-500 flex flex-col items-center text-center p-6">
                   <div v-if="selectedCloth" class="mb-4 relative w-32 h-32 rounded-lg overflow-hidden border border-slate-600">
                      <img :src="selectedCloth.image_url" class="w-full h-full object-cover opacity-70" />
                   </div>
                   <span v-if="selectedCloth">Processing... (If stuck, click Try Again)</span>
                   <span v-else>Select an item below to see the result here</span>
                </div>
                
                <div class="absolute top-3 left-3 bg-indigo-600/80 backdrop-blur px-3 py-1 rounded-full text-xs text-white">Try-On Result</div>
            </div>
         </div>
      </div>
    </section>

    <!-- Gallery Section -->
    <section>
      <h2 class="text-2xl font-bold mb-6 text-white flex items-center">
        <span class="w-8 h-8 rounded-full bg-pink-500 flex items-center justify-center text-sm mr-3">2</span>
        Wardrobe Collection
      </h2>
      
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        <div v-for="cloth in clothes" :key="cloth.id" class="group relative bg-slate-800/40 rounded-2xl overflow-hidden border border-white/5 hover:border-purple-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-purple-500/20 hover:-translate-y-2">
           <!-- Image -->
           <div class="aspect-[3/4] w-full overflow-hidden bg-slate-900 relative">
             <img :src="cloth.image_url" :alt="cloth.name" class="h-full w-full object-cover object-center transition-transform duration-700 group-hover:scale-110">
           </div>
           
           <!-- Content -->
           <div class="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-slate-900/90 to-transparent">
             <h3 class="text-lg font-bold text-white leading-tight mb-1">{{ cloth.name }}</h3>
             <button @click="tryOn(cloth)" class="w-full mt-2 bg-white/10 hover:bg-white text-white hover:text-indigo-900 font-bold py-2 rounded-lg backdrop-blur-sm transition-all duration-300">
               Try On
             </button>
           </div>
        </div>
      </div>
    </section>
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
