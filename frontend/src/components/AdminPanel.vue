<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const file = ref<File | null>(null)
const heightRange = ref('')
const gender = ref('中性')
const category = ref('Upper-body') // Default category
const uploadStatus = ref('')
const result = ref<any>(null)

// Manage List Logic
const clothesList = ref<any[]>([])
const loadingList = ref(false)
const editingItem = ref<any>(null)
const previewUrl = ref('')
const dbStatus = ref('')

const fetchClothes = async () => {
  loadingList.value = true
  try {
    const res = await axios.get('/api/clothes')
    clothesList.value = res.data
    
    // Check Health for DB Status
    try {
        const health = await axios.get('/api/health')
        const mode = health.data.storage?.mode || 'Unknown'
        dbStatus.value = mode
    } catch(e) {}
    
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
    const selectedFile = target.files[0]
    
    // 1. Check File Type (Must be PNG)
    if (selectedFile.type !== 'image/png') {
      alert("請上傳 PNG 格式的圖片 (必須包含透明背景)！")
      target.value = '' // Clear input
      file.value = null
      previewUrl.value = ''
      return
    }

    // 2. Check for Transparency (Canvas Analysis)
    const img = new Image()
    const objectUrl = URL.createObjectURL(selectedFile)
    img.src = objectUrl
    
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      
      canvas.width = img.width
      canvas.height = img.height
      
      if (!ctx) {
         // Fallback if canvas failed (rare)
         file.value = selectedFile
         previewUrl.value = objectUrl
         return
      }

      ctx.drawImage(img, 0, 0)
      
      try {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        const data = imageData.data
        let hasTransparency = false
        
        // Sample pixels (checking every 10th pixel for speed)
        for (let i = 3; i < data.length; i += 40) { 
          if (data[i] < 250) { // Alpha channel < 250 (allowing slight anti-aliasing but looking for holes)
             hasTransparency = true
             break
          }
        }
        
        if (!hasTransparency) {
           alert("錯誤：偵測不到透明背景！\n\n管理者上傳規定：\n1. 必須是去背過的 PNG 圖檔。\n2. 請使用 remove.bg 等工具去背後再上傳。")
           target.value = ''
           file.value = null
           previewUrl.value = ''
           URL.revokeObjectURL(objectUrl)
        } else {
           // Valid
           file.value = selectedFile
           previewUrl.value = objectUrl
        }
        
      } catch (err) {
         console.error("Transparency check failed:", err)
         // Allow upload if check fails (fail open) but warn
         file.value = selectedFile
         previewUrl.value = objectUrl
      }
    }
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
  formData.append('category', category.value)

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

// New methods for try-on image and outfit suggestion
const generateTryOnImage = async () => {
  if (!result.value || !result.value.id) {
    alert('請先上傳衣物並獲取分析結果')
    return
  }

  try {
    const res = await axios.post('/api/tryon', { clothing_id: result.value.id })
    const imageUrl = res.data.image_url

    // Open in new tab or download
    window.open(imageUrl, '_blank')
  } catch (err) {
    console.error(err)
    alert('生成試穿照片時發生錯誤')
  }
}

const suggestOutfit = async () => {
  if (!result.value || !result.value.style) {
    alert('請先上傳衣物並獲取分析結果')
    return
  }

  try {
    const res = await axios.post('/api/suggest-outfit', { style: result.value.style })
    const suggestedClothes = res.data

    // TODO: Handle displaying suggested outfits (e.g., show in a modal or new section)
    console.log('Suggested outfits:', suggestedClothes)
  } catch (err) {
    console.error(err)
    alert('獲取建議穿搭時發生錯誤')
  }
}
</script>

<template>
  <div class="glass-panel p-8 rounded-2xl max-w-4xl mx-auto">
    <div class="flex justify-between items-start mb-8">
      <div>
        <h2 class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
          Upload New Clothing
        </h2>
        <p v-if="dbStatus" class="text-xs mt-2 font-mono" :class="dbStatus.includes('MongoDB') ? 'text-emerald-400' : 'text-orange-400'">
           Storage: {{ dbStatus }}
        </p>
      </div>
    </div>
    
    <div class="space-y-6 mb-12">
      <!-- Upload Section -->
      <div class="group">
        <label class="block text-sm font-medium text-slate-400 mb-2">Upload Image</label>
        <div class="relative h-96 border-2 border-dashed border-slate-600 rounded-xl p-8 transition-colors group-hover:border-purple-500/50 bg-slate-800/20 text-center overflow-hidden flex flex-col justify-center items-center">
          <input type="file" @change="onFileChange" accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"/>
          
          <div v-if="previewUrl" class="absolute inset-0 w-full h-full bg-slate-900 z-0">
             <img :src="previewUrl" class="w-full h-full object-contain p-4" />
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
        
        <div class="col-span-1 md:col-span-2">
            <label class="block text-sm font-medium text-slate-400 mb-2">Clothing Type (Category)</label>
            <select v-model="category" class="input-tech w-full px-4 py-3 appearance-none">
              <optgroup label="Upper Body">
                <option value="Upper-body" class="bg-slate-800">Upper Body (通用上身/外套)</option>
              </optgroup>
              <optgroup label="Skirts (裙子)">
                <option value="Mini Skirt" class="bg-slate-800">3分裙 (Mini/Short Skirt)</option>
                <option value="Midi Skirt" class="bg-slate-800">5分裙 (Knee Length)</option>
                <option value="Long Skirt" class="bg-slate-800">7分裙 (Calf Length)</option>
                <option value="Maxi Skirt" class="bg-slate-800">9分裙 (Ankle/Full Length)</option>
              </optgroup>
              <optgroup label="Pants (褲子)">
                 <option value="Hot Pants" class="bg-slate-800">3分褲 (Shorts/Hot Pants)</option>
                 <option value="Capri Pants" class="bg-slate-800">5分褲 (Capri/Knee Length)</option>
                 <option value="Ankle Pants" class="bg-slate-800">9分褲 (Ankle Length)</option>
                 <option value="Trousers" class="bg-slate-800">10分褲 (Full Length)</option>
              </optgroup>
              <optgroup label="Full Body">
                <option value="Dresses" class="bg-slate-800">Dress (連身裙/全身)</option>
              </optgroup>
            </select>
            <p class="text-xs text-slate-500 mt-1">請正確選擇，否則試穿效果會錯誤 (例如褲子跑到胸部)</p>
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
            
            <div class="col-span-2">
                <label class="block text-sm text-slate-400 mb-1">Clothing Type (Category)</label>
                <select v-model="editingItem.category" class="input-tech w-full px-3 py-2 text-sm appearance-none">
                  <optgroup label="Upper Body">
                    <option value="Upper-body" class="bg-slate-800">Upper Body</option>
                  </optgroup>
                  <optgroup label="Skirts">
                    <option value="Mini Skirt" class="bg-slate-800">3分裙 (Mini)</option>
                    <option value="Midi Skirt" class="bg-slate-800">5分裙 (Knee)</option>
                    <option value="Long Skirt" class="bg-slate-800">7分裙 (Calf)</option>
                    <option value="Maxi Skirt" class="bg-slate-800">9分裙 (Full)</option>
                  </optgroup>
                  <optgroup label="Pants">
                     <option value="Hot Pants" class="bg-slate-800">3分褲 (Shorts)</option>
                     <option value="Capri Pants" class="bg-slate-800">5分褲 (Knee)</option>
                     <option value="Ankle Pants" class="bg-slate-800">9分褲 (Ankle)</option>
                     <option value="Trousers" class="bg-slate-800">10分褲 (Full)</option>
                  </optgroup>
                  <optgroup label="Full Body">
                    <option value="Dresses" class="bg-slate-800">Dress</option>
                  </optgroup>
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

    <!-- Try-On and Suggestion Section -->
    <div class="mt-12">
      <h2 class="text-2xl font-bold text-white mb-4">試穿照片生成與建議穿搭</h2>
      
      <div class="space-y-4">
        <div>
          <h3 class="text-lg font-semibold text-purple-300">生成試穿照片</h3>
          <button @click="generateTryOnImage" class="btn-tech px-4 py-2 text-lg w-full">
            生成試穿照片
          </button>
        </div>
        
        <div>
          <h3 class="text-lg font-semibold text-purple-300">建議穿搭</h3>
          <button @click="suggestOutfit" class="btn-tech px-4 py-2 text-lg w-full">
            建議穿搭
          </button>
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
