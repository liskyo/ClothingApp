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

type Mode = 'try-on' | 'recommend'

const mode = ref<Mode>('try-on')
const clothes = ref<Cloth[]>([])
const userHeight = ref('')
const userWeight = ref('')
const userGender = ref('中性')
const stylePreference = ref('')
const userFile = ref<File | null>(null)
const userPhotoPreview = ref<string | null>(null)
const selectedCloth = ref<Cloth | null>(null)
const tryOnResult = ref<string | null>(null)
const loading = ref(false)
const isValidating = ref(false)
const recommending = ref(false)
const recommendedOutfits = ref<Cloth[][]>([])

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

const compressImage = async (file: File): Promise<File> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target?.result as string;
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        
        // Resize to max 1280px (Safe for VTON & Vercel Limit)
        const MAX_SIZE = 1280;
        if (width > height) {
          if (width > MAX_SIZE) {
            height *= MAX_SIZE / width;
            width = MAX_SIZE;
          }
        } else {
          if (height > MAX_SIZE) {
            width *= MAX_SIZE / height;
            height = MAX_SIZE;
          }
        }
        
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => {
          if (blob) {
            // Create new file with same name but jpg
            const newFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + ".jpg", {
              type: 'image/jpeg',
              lastModified: Date.now(),
            });
            console.log(`Compressed: ${(file.size/1024/1024).toFixed(2)}MB -> ${(newFile.size/1024/1024).toFixed(2)}MB`);
            resolve(newFile);
          } else {
            reject(new Error("Canvas to Blob failed"));
          }
        }, 'image/jpeg', 0.85); // 85% Quality
      };
      img.onerror = (err) => reject(err);
    };
    reader.onerror = (err) => reject(err);
  });
}

const onUserFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    let rawFile = target.files[0]
    
    // Resize before anything
    try {
        console.log("Compressing image...");
        rawFile = await compressImage(rawFile);
    } catch (e) {
        console.error("Compression failed, using raw:", e);
    }
    
    // Show raw preview first
    userPhotoPreview.value = URL.createObjectURL(rawFile)
    
    // Call Backend
    const formData = new FormData()
    formData.append('file', rawFile)
    
    isValidating.value = true
    
    try {
        const res = await axios.post('/api/validate-avatar', formData, {
            responseType: 'blob'
        })
        
        // Success: AI says OK and returns cropped image
        const processedBlob = res.data
        const processedFile = new File([processedBlob], rawFile.name, { type: "image/jpeg" })
        
        userFile.value = processedFile
        userPhotoPreview.value = URL.createObjectURL(processedBlob)
        
    } catch (err: any) {
        console.error(err)
        // Failure: AI says Rejection
        if (err.response && err.response.status === 400) {
            const errorBlob = err.response.data
            const reader = new FileReader()
            reader.onload = () => {
                try {
                     const parser = JSON.parse(reader.result as string)
                     alert(`照片不符合試穿規格：\n${parser.message}\n\n請重新上傳單人、正面、清晰的全身照。`)
                     // Clear preview
                     userFile.value = null
                     userPhotoPreview.value = null
                     target.value = '' // Clear input
                } catch {
                     alert("照片不符合規格 (無法讀取原因)")
                     userFile.value = null
                     userPhotoPreview.value = null
                     target.value = ''
                }
            }
            reader.readAsText(errorBlob)
        } else {
             // If 403 or 500, likely Vercel blocking or Timeout.
             // But we just resized, so chance is lower.
             // Fallback to original (resized) file.
             alert('照片分析連線失敗 (可能因網路問題)，將直接使用此照片試穿。')
             userFile.value = rawFile
        }
    } finally {
        isValidating.value = false
        // Reset file input so checking same file again works if needed
        target.value = ''
    }
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
  } catch (err: any) {
    console.error(err)
    
    // Extract detailed error from backend
    let errorMsg = "試穿失敗，請稍後再試。";
    if (err.response) {
         errorMsg += `\n(狀態碼: ${err.response.status})`;
         
         if (err.response.data) {
             if (typeof err.response.data === 'object' && err.response.data.detail) {
                 errorMsg += `\n內容: ${err.response.data.detail}`;
             } else {
                 // Likely HTML or raw string
                 const rawData = String(err.response.data).substring(0, 200); // truncated
                 errorMsg += `\n內容: ${rawData}...`;
             }
         }
    } else if (err.message) {
         errorMsg += `\n(${err.message})`;
    }
    
    alert(errorMsg);
  } finally {
    loading.value = false
  }
}

const switchMode = (newMode: Mode) => {
  mode.value = newMode
  if (newMode === 'try-on') {
    recommendedOutfits.value = []
  } else {
    tryOnResult.value = null
    selectedCloth.value = null
  }
}

const recommendOutfit = async () => {
  if (!userHeight.value || !userWeight.value) {
    alert('請輸入身高和體重')
    return
  }
  
  recommending.value = true
  recommendedOutfits.value = []
  
  try {
    const params = new URLSearchParams()
    params.append('height', userHeight.value)
    params.append('weight', userWeight.value)
    params.append('gender', userGender.value)
    if (stylePreference.value.trim()) {
      params.append('style_preference', stylePreference.value.trim())
    }
    
    const res = await axios.get('/api/recommend-outfit', { params })
    recommendedOutfits.value = res.data.outfits || []
    
    if (recommendedOutfits.value.length === 0) {
      alert('抱歉，目前沒有符合條件的服裝組合。請嘗試調整您的條件。')
    }
  } catch (err: any) {
    console.error(err)
    let errorMsg = "推薦失敗，請稍後再試。"
    if (err.response?.data?.detail) {
      errorMsg = err.response.data.detail
    }
    alert(errorMsg)
  } finally {
    recommending.value = false
  }
}

onMounted(() => {
  fetchClothes()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Mode Selector -->
    <section class="glass-panel p-4 rounded-2xl">
      <div class="flex space-x-4 bg-slate-800/50 p-1 rounded-xl border border-white/5">
        <button 
          @click="switchMode('try-on')"
          class="flex-1 px-6 py-3 rounded-lg text-sm font-medium transition-all duration-300"
          :class="mode === 'try-on' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-white/5'"
        >
          📷 全身照試穿
        </button>
        <button 
          @click="switchMode('recommend')"
          class="flex-1 px-6 py-3 rounded-lg text-sm font-medium transition-all duration-300"
          :class="mode === 'recommend' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-white/5'"
        >
          ✨ 風格建議
        </button>
      </div>
    </section>

    <!-- Try-On Mode -->
    <div v-if="mode === 'try-on'">
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
                
                <!-- Validation Loading Overlay -->
                <div v-if="isValidating" class="absolute inset-0 z-10 bg-slate-900/80 backdrop-blur flex flex-col items-center justify-center">
                     <div class="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                     <span class="text-green-400 text-sm font-bold animate-pulse">Analyzing & Cropping...</span>
                </div>
                
                <div class="absolute top-3 left-3 bg-black/50 backdrop-blur px-3 py-1 rounded-full text-xs text-white">Your Photo</div>
            </div>

            <!-- Right: Try-On Result -->
            <div class="relative aspect-[3/4] bg-slate-900/50 rounded-2xl border border-dashed border-slate-700 flex items-center justify-center overflow-hidden">
                <!-- Placeholder / Loading / Result -->
                
                <!-- State 1: Loading -->
                <div v-if="loading" class="absolute inset-0 z-10 bg-slate-900/80 backdrop-blur flex flex-col items-center justify-center">
                     <div class="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                     <span class="text-indigo-400 font-bold animate-pulse">Loading... 目前排隊人數較多</span>
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

    <!-- Recommend Mode -->
    <div v-if="mode === 'recommend'">
      <section class="glass-panel p-6 rounded-2xl relative overflow-hidden">
        <div class="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>

        <div class="space-y-6">
          <h2 class="text-2xl font-bold text-white flex items-center">
            <span class="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center text-sm mr-3">1</span>
            個人資訊與風格偏好
          </h2>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Height -->
            <div>
              <label class="block text-sm font-medium text-slate-400 mb-2">身高 (cm) *</label>
              <input v-model="userHeight" type="number" class="input-tech w-full px-4 py-3" placeholder="例如: 165" min="100" max="250">
            </div>
            
            <!-- Weight -->
            <div>
              <label class="block text-sm font-medium text-slate-400 mb-2">體重 (kg) *</label>
              <input v-model="userWeight" type="number" class="input-tech w-full px-4 py-3" placeholder="例如: 55" min="30" max="200">
            </div>
            
            <!-- Gender -->
            <div>
              <label class="block text-sm font-medium text-slate-400 mb-2">性別偏好</label>
              <select v-model="userGender" class="input-tech w-full px-4 py-3 appearance-none">
                <option class="bg-slate-800">中性</option>
                <option class="bg-slate-800">女性</option>
                <option class="bg-slate-800">男性</option>
              </select>
            </div>
          </div>

          <!-- Style Preference -->
          <div>
            <label class="block text-sm font-medium text-slate-400 mb-2">喜歡的風格要求</label>
            <textarea 
              v-model="stylePreference" 
              class="input-tech w-full px-4 py-3 h-24 resize-none" 
              placeholder="例如：休閒風格、正式場合、甜美可愛、簡約時尚、運動風格、學院風格、度假休閒等..."
            ></textarea>
          </div>

          <!-- Recommend Button -->
          <button 
            @click="recommendOutfit" 
            :disabled="recommending || !userHeight || !userWeight"
            class="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-bold py-4 rounded-xl transition-all duration-300 shadow-lg shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            <span v-if="recommending" class="flex items-center">
              <div class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              正在分析並推薦中...
            </span>
            <span v-else>✨ 獲取風格建議</span>
          </button>
        </div>
      </section>

      <!-- Recommended Outfits -->
      <section v-if="recommendedOutfits.length > 0" class="space-y-6">
        <h2 class="text-2xl font-bold mb-6 text-white flex items-center">
          <span class="w-8 h-8 rounded-full bg-pink-500 flex items-center justify-center text-sm mr-3">2</span>
          推薦穿搭組合
        </h2>
        
        <div v-for="(outfit, index) in recommendedOutfits" :key="index" class="glass-panel p-6 rounded-2xl">
          <h3 class="text-lg font-bold text-white mb-4 flex items-center">
            <span class="w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center text-xs mr-2">{{ index + 1 }}</span>
            組合 {{ index + 1 }}
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            <div v-for="cloth in outfit" :key="cloth.id" class="group relative bg-slate-800/40 rounded-2xl overflow-hidden border border-white/5 hover:border-purple-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/20">
              <div class="aspect-[3/4] w-full overflow-hidden bg-slate-900 relative">
                <img :src="cloth.image_url" :alt="cloth.name" class="h-full w-full object-cover object-center transition-transform duration-700 group-hover:scale-110">
              </div>
              <div class="p-4">
                <h4 class="text-sm font-bold text-white mb-1">{{ cloth.name }}</h4>
                <p class="text-xs text-slate-400">{{ cloth.style }}</p>
                <p class="text-xs text-slate-500 mt-1">{{ cloth.category }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Empty State -->
      <section v-else-if="!recommending" class="glass-panel p-12 rounded-2xl text-center">
        <div class="text-slate-500 flex flex-col items-center">
          <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <p class="text-lg mb-2">請輸入您的個人資訊和風格偏好</p>
          <p class="text-sm text-slate-600">然後點擊「獲取風格建議」來獲得推薦的服裝組合</p>
        </div>
      </section>
    </div>
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
