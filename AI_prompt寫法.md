# AI Prompt 指令指南：如何從零打造 ClothingApp

這份文件提供了一套 **循序漸進 (Step-by-step)** 的 Prompt 指令，即使是從零開始，也能讓 AI 協助你重建這個虛擬試穿 (Virtual Try-On) 專案。

建議依照順序將 Prompt 貼給 AI (如 ChatGPT, Claude, Gemini 或 Cursor)。

---

## 階段 1：專案初始化與架構設定 (Setup)

**目標**：建立專案資料夾結構、安裝依賴，並確認技術堆疊。

> **Prompt 1 (初始化):**
>
> 請幫我建立一個全端的 Web 應用程式專案，名稱為 `ClothingApp`。
>
> **技術堆疊需求：**
> 1.  **後端**：使用 Python **FastAPI**。
> 2.  **前端**：使用 **Vue 3** (Composition API) + **Vite** + **TypeScript**。
> 3.  **樣式**：使用 **Tailwind CSS**，請幫我配置好深色模式 (Dark Mode) 的基礎設定。
> 4.  **專案結構**：請採用 Monorepo 風格，根目錄下分別有 `backend/` 和 `frontend/` 資料夾，以及一個 `api/` 資料夾用於 Vercel Serverless Function 配置。
>
> 請告訴我如何使用終端機指令初始化這個專案結構，並提供根目錄的 `requirements.txt` (後端依賴) 與 `frontend/package.json` 的建議內容。後端需要安裝 `fastapi`, `uvicorn`, `python-multipart`, `google-generativeai`, `gradio_client`。

---

## 階段 2：後端開發 (Backend Development)

**目標**：實作核心 API、AI 服務整合。

> **Prompt 2 (資料管理模組):**
>
> 請在 `backend/` 下建立一個 `clothes_manager.py`。
> 需求：
> 1.  使用一個本地的 JSON 檔案 (`model/clothes.json`) 來當作簡易資料庫。
> 2.  實作 `ClothesManager` 類別。
> 3.  功能包含：
>     - `get_all_clothes()`: 讀取所有衣服。
>     - `add_clothing_item(name, height_range, gender, style)`: 新增衣服並自動產生 ID (如 001, 002)。
>     - `get_cloth_by_id(id)`: 透過 ID 取得衣服資訊。
> 4.  請注意處理檔案不存在時的初始化邏輯。

> **Prompt 3 (AI 服務 - Gemini 整合):**
>
> 請建立 `backend/ai_service.py`，並實作 `AIService` 類別。我們需要整合 Google Gemini API。
>
> **功能 1：分析衣服風格 (`analyze_image_style`)**
> - 輸入：圖片的 bytes。
> - 動作：呼叫 Gemini API 分析這張圖片。
> - 輸出：回傳 JSON，包含 `name` (衣服名稱) 與 `style` (風格描述)。若 API 失敗請回傳 Mock 資料。
>
> **功能 2：驗證使用者照片 (`validate_and_crop_user_photo`)**
> - 輸入：圖片 bytes。
> - Prompt 指令：請 Gemini 檢查這張照片是否為「全身照」、「單人」、「正面」。
> - 輸出：回傳 `valid` (布林值) 與 `reason` (失敗原因)。如果不符合標準，回傳 False。
>
> 請記得從環境變數讀取 `GEMINI_API_KEY`。

> **Prompt 4 (AI 服務 - 虛擬試穿 VTON):**
>
> 延續 `backend/ai_service.py`，請加入虛擬試穿功能 `virtual_try_on`。
>
> **實作細節：**
> 1.  使用 `gradio_client` 連接 HuggingFace 上的 `levihsu/OOTDiffusion` Space (或其他類似的 OOTD Space)。
> 2.  **關鍵邏輯 (Smart Padding)**：由於 OOTDiffusion 模型對 3:4 比例 (0.75) 的圖片效果最好，請寫一個輔助函式，在呼叫 API 前將使用者上傳的照片「補白邊」至 3:4 比例，收到結果後再「裁切」回原始比例。
> 3.  針對「下半身 (Lower-body)」試穿，加入邏輯防止寬褲變形。

> **Prompt 5 (主要 API 路由):**
>
> 請實作 `backend/main.py`，整合 FastAPI。
>
> **API Endpoints:**
> 1.  `GET /api/clothes`: 回傳衣服列表，支援 `gender` URL 參數篩選。
> 2.  `POST /api/upload`: 接收圖片與表單資料 -> 呼叫 AI 分析風格 -> 儲存圖片到 `model/` 資料夾 -> 寫入 `clothes.json`。
> 3.  `POST /api/validate-avatar`: 接收使用者照片 -> 呼叫 AI 驗證 -> 回傳結果。
> 4.  `POST /api/try-on`: 接收使用者照片與衣服 ID -> 呼叫 AI 試穿 -> 回傳生成的圖片 (image/jpeg)。
>
> 請設定好 CORS 與 Static Files mount (掛載 `model/` 目錄以存取圖片)。

---

## 階段 3：前端開發 (Frontend Development)

**目標**：打造現代化、深色風格的 UI。

> **Prompt 6 (UI 框架與共用元件):**
>
> 請切換到前端部分。我要一個深色系、充滿科技感的 UI 風格 (Dark Mode)。
>
> 請修改 `frontend/src/App.vue`：
> 1.  背景使用深色背景 (slate-900)。
> 2.  上方有一個玻璃擬態 (Glassmorphism) 的 Navbar。
> 3.  Navbar 右側有切換按鈕，可以在「使用者模式 (User)」與「管理員模式 (Admin)」之間切換 (`v-if`)。

> **Prompt 7 (管理員後台):**
>
> 請建立元件 `src/components/AdminPanel.vue`。
>
> **功能：**
> 1.  一個上傳區塊，包含「選擇圖片」、「身高範圍輸入框」、「性別下拉選單」。
> 2.  按下上傳後，打 API 到 `/api/upload`。
> 3.  上傳成功後，顯示回傳的 AI 分析結果 (衣服名稱、風格)。
>
> **樣式：** 使用 Tailwind CSS 的卡片樣式，搭配紫色系的按鈕。

> **Prompt 8 (使用者試穿介面):**
>
> 請建立元件 `src/components/UserPanel.vue`。
>
> **功能：**
> 1.  **左側/上方**：顯示衣服列表卡片 (Grid Layout)，從 `/api/clothes` 抓取資料。每張卡片顯示圖片與名稱。
> 2.  **右側/下方**：試穿區塊。
>     - 步驟 1：點選一件衣服 (Highlight 選擇狀態)。
>     - 步驟 2：上傳自己的全身照。
>     - 步驟 3：前端先呼叫 `/api/validate-avatar` 檢查照片。
>     - 步驟 4：若通過，呼叫 `/api/try-on` 並顯示 Loading 動畫。
>     - 步驟 5：顯示試穿後的結果大圖。

---

## 階段 4：部署設定 (Deployment)

**目標**：配置 Vercel 部署設定檔。

> **Prompt 9 (Vercel 部署設定):**
>
> 我想將這個專案部署到 Vercel。請幫我建立 `vercel.json` 與 `api/index.py`。
>
> **需求：**
> 1.  `vercel.json`：設定 Rewrites，將 `/api/*` 的請求導向 `api/index.py`，其餘請求導向前端靜態頁面。
> 2.  `api/index.py`：這是一個 Serverless Function 的進入點，請 import 我們在 `backend/main.py` 寫好的 FastAPI `app` 實例。
>
> 請提醒我部署時需要在 Vercel 設定哪些環境變數 (如 `GEMINI_API_KEY`, `REPLICATE_API_TOKEN` 等)。

---

## 總結提示 (Tips for Success)

*   **分段執行**：不要一次把所有 Prompt 貼給 AI，它可能會遺漏細節。建議一個階段完成並測試後，再進行下一個階段。
*   **提供錯誤訊息**：如果在執行過程中遇到 Bug (例如 `ModuleNotFound` 或 API 報錯)，直接把錯誤訊息貼給 AI，讓它修正程式碼。
*   **客製化**：你可以要求 AI 修改 UI配色 (例如：「把紫色系改成藍綠色系 Cyberpunk 風格」)。
