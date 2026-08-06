"""
Chemical Bottle Scanner - UX Enhanced Edition
===================================================================
Features:
1. GUI File Selection (Supports Chinese Headers)
2. Result Persistence (Holds result for 3 seconds) [NEW]
3. Scanned History Sidebar (Shows last 8 items) [NEW]
4. Missing Items Report Generation
5. Robust CSV Handling (utf-8-sig)
"""

import cv2
import pytesseract
import pandas as pd
import numpy as np
import re
import os
import time
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Set
from thefuzz import fuzz, process

# =============================================================================
# CONFIGURATION (設定)
# =============================================================================

# Tesseract 執行檔路徑
# 可用環境變數覆寫：set TESSERACT_PATH=D:\Tesseract-OCR\tesseract.exe
# Linux / macOS 已在 PATH 中的話，設成 'tesseract' 即可
TESSERACT_PATH = os.environ.get(
    'TESSERACT_PATH',
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

# 攝影機索引（0 = 內建鏡頭；外接 / DroidCam 通常是 1 或 2）
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))

# 掃描頻率
OCR_FRAME_INTERVAL = 10

# [新增] 結果停留時間 (秒) - 您可以在這裡調整時間
RESULT_PERSISTENCE_SECONDS = 3.0

# 顯示設定
MAIN_WINDOW_NAME = 'Chemical Scanner - Press Q to Quit'
FONT = cv2.FONT_HERSHEY_SIMPLEX

# 顏色定義 (BGR)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_CYAN = (255, 255, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (50, 50, 50)
COLOR_PANEL_BG = (40, 40, 40) # 右側面板背景色

# =============================================================================
# GUI 檔案選擇
# =============================================================================

# 資料夾路徑
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def select_inventory_file() -> Optional[str]:
    """跳出視窗讓使用者選擇 CSV 檔案"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # 預設開啟 data 資料夾
    default_dir = DATA_FOLDER if os.path.isdir(DATA_FOLDER) else os.getcwd()
    
    file_path = filedialog.askopenfilename(
        title="請選擇藥品庫存清單 (Select Inventory CSV)",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialdir=default_dir
    )
    
    root.destroy()
    return file_path

# =============================================================================
# 核心邏輯 (OCR & 驗證)
# =============================================================================

def validate_cas_checksum(cas_number: str) -> bool:
    """CAS 校驗碼驗證"""
    try:
        digits_only = cas_number.replace('-', '')
        if not digits_only.isdigit() or len(digits_only) < 5:
            return False
        
        check_digit = int(digits_only[-1])
        digits_to_check = digits_only[:-1]
        
        checksum = 0
        position = 1
        
        for digit in reversed(digits_to_check):
            checksum += int(digit) * position
            position += 1
            
        return (checksum % 10) == check_digit
    except:
        return False

def extract_cas_numbers(text: str) -> List[str]:
    """從文字中提取有效的 CAS 號碼"""
    cas_pattern = r'\b(\d{2,7}-\d{2}-\d)\b'
    potential_cas = re.findall(cas_pattern, text)
    valid_cas = [cas for cas in potential_cas if validate_cas_checksum(cas)]
    return valid_cas

def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """影像前處理"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

# =============================================================================
# 庫存管理類別 (Inventory Manager)
# =============================================================================

class InventoryManager:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.csv_dir = os.path.dirname(csv_path)
        self.found_cas: Set[str] = set()
        self.found_names: Set[str] = set()
        
        # [新增] 歷史紀錄清單 (用於右側面板顯示)
        self.scan_history: List[Dict] = []
        
        try:
            # 1. 讀取 CSV
            self.df = pd.read_csv(csv_path, dtype={'CAS': str}, encoding='utf-8-sig')
            
            # 2. 清除標題空白
            self.df.columns = self.df.columns.str.strip()
            
            # 3. 欄位對應
            header_mapping = {
                'CAS': 'CAS',
                '上層藥品名稱': 'Name',
                '廠牌': 'Location',
                '數量': 'Stock'
            }
            self.df.rename(columns=header_mapping, inplace=True)
            
            # 4. 資料清理
            if 'CAS' in self.df.columns:
                self.df['CAS'] = self.df['CAS'].str.strip()
            if 'Name' in self.df.columns:
                self.df['Name'] = self.df['Name'].str.strip()
                
            self._name_list = self.df['Name'].tolist() if 'Name' in self.df.columns else []
            self._name_to_cas = dict(zip(self.df['Name'].str.lower(), self.df['CAS'])) if 'Name' in self.df.columns else {}
            self._cas_set = set(self.df['CAS'].tolist()) if 'CAS' in self.df.columns else set()
            
            print(f"[OK] 成功載入 {len(self.df)} 筆藥品資料。")
            
        except Exception as e:
            print(f"[ERROR] 讀取 CSV 失敗: {e}")
            self.df = pd.DataFrame()
            self._name_list = []
            self._cas_set = set()

    @property
    def total_count(self) -> int:
        return len(self.df)
    
    @property
    def scanned_count(self) -> int:
        all_found = self.found_cas.copy()
        for name in self.found_names:
            cas = self._name_to_cas.get(name.lower())
            if cas: all_found.add(cas)
        return len(all_found & self._cas_set)

    def _add_to_history(self, info: dict):
        """[新增] 將掃描到的物品加入歷史清單"""
        # 防止重複：如果最新的一筆跟現在這筆一樣，就不加
        if not self.scan_history or self.scan_history[-1]['CAS'] != info['CAS']:
            display_item = {
                'CAS': info['CAS'],
                'Brand': info.get('Location', 'N/A'), # 顯示廠牌比較不會亂碼
                'Time': datetime.now().strftime("%H:%M:%S")
            }
            self.scan_history.append(display_item)
            # 只保留最後 8 筆
            if len(self.scan_history) > 8:
                self.scan_history.pop(0)

    def lookup(self, cas_number: str) -> Optional[dict]:
        """查詢藥品並加入歷史"""
        if self.df.empty: return None
        result = self.df[self.df['CAS'] == cas_number]
        
        if len(result) > 0:
            self.found_cas.add(cas_number)
            row = result.iloc[0]
            info = {
                'CAS': row['CAS'],
                'Name': row['Name'],
                'Location': row.get('Location', 'N/A'),
                'Stock': row.get('Stock', 'N/A'),
                'match_type': 'cas'
            }
            self._add_to_history(info) # 加入歷史
            return info
        return None

    def fuzzy_match_name(self, text: str, threshold: int = 80) -> Optional[Dict]:
        # (簡化的模糊比對邏輯，為了保持程式碼簡潔，這裡主要依賴 CAS)
        # 如果需要名字比對功能，可以保留原本的邏輯
        if not self._name_list or not text.strip(): return None
        # 這裡為了流暢度先略過複雜的名字比對，專注於 CAS 掃描
        return None

    def generate_report(self) -> str:
        all_found = self.found_cas.copy()
        for name in self.found_names:
            cas = self._name_to_cas.get(name.lower())
            if cas: all_found.add(cas)
            
        missing = self.df[~self.df['CAS'].isin(all_found)]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"missing_report_{timestamp}.csv"
        # 報告存到 data 資料夾
        path = os.path.join(DATA_FOLDER, filename)
        missing.to_csv(path, index=False, encoding='utf-8-sig')
        return path

# =============================================================================
# OCR ENGINE
# =============================================================================

def perform_ocr(image: np.ndarray) -> str:
    """執行 OCR (寬鬆模式，移除白名單以增加辨識率)"""
    config = '--oem 3 --psm 6'
    try:
        return pytesseract.image_to_string(image, config=config)
    except:
        return ""

# =============================================================================
# DISPLAY OVERLAY (畫面繪製)
# =============================================================================

def draw_overlay(frame: np.ndarray, 
                 display_info: Optional[dict], # 這是要顯示在中間的資訊
                 inventory: InventoryManager,
                 fps: float) -> np.ndarray:
    
    display = frame.copy()
    h, w = display.shape[:2]
    
    # --- 1. 頂部狀態列 ---
    cv2.rectangle(display, (0, 0), (w, 60), COLOR_BLACK, -1)
    cv2.putText(display, f"FPS: {fps:.1f}", (10, 25), FONT, 0.6, COLOR_WHITE, 1)
    
    # 盤點進度
    scanned = inventory.scanned_count
    total = inventory.total_count
    prog_text = f"Scanned: {scanned} / {total}"
    cv2.putText(display, prog_text, (w - 320, 35), FONT, 0.8, COLOR_CYAN, 2)
    
    # --- 2. [新增] 右側歷史面板 ---
    panel_width = 300
    overlay = display.copy()
    # 畫一個半透明背景
    cv2.rectangle(overlay, (w - panel_width, 60), (w, h), COLOR_PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.8, display, 0.2, 0, display)
    
    # 歷史標題
    cv2.putText(display, "--- History (Last 8) ---", (w - panel_width + 10, 90), FONT, 0.6, COLOR_YELLOW, 1)
    
    # 畫出最近的項目 (倒序排列，最新的在上面)
    y_pos = 130
    for item in reversed(inventory.scan_history):
        # 顯示 CAS
        cv2.putText(display, f"{item['CAS']}", (w - panel_width + 10, y_pos), FONT, 0.6, COLOR_GREEN, 2)
        
        # 顯示 廠牌 與 時間 (避免顯示中文 Name 以防亂碼)
        sub_text = f"@{item['Brand']} ({item['Time']})"
        cv2.putText(display, sub_text, (w - panel_width + 10, y_pos + 25), FONT, 0.5, COLOR_WHITE, 1)
        
        # 分隔線
        cv2.line(display, (w - panel_width + 5, y_pos + 35), (w - 5, y_pos + 35), COLOR_GRAY, 1)
        
        y_pos += 60
        if y_pos > h - 50: break

    # --- 3. [新增] 中央掃描結果 (具備視覺暫留功能) ---
    if display_info:
        info = display_info
        
        # 定義框框位置 (避開右側面板)
        box_w_start = 50
        box_w_end = w - panel_width - 50
        box_h_start = h - 220
        box_h_end = h - 50
        
        # 綠色背景框
        cv2.rectangle(display, (box_w_start, box_h_start), (box_w_end, box_h_end), (0, 100, 0), -1)
        cv2.rectangle(display, (box_w_start, box_h_start), (box_w_end, box_h_end), COLOR_GREEN, 3)
        
        # 顯示文字
        cv2.putText(display, "MATCH FOUND!", (box_w_start + 20, box_h_start + 40), FONT, 1.0, COLOR_WHITE, 3)
        
        text_cas = f"CAS: {info['CAS']}"
        text_brand = f"Brand: {info['Location']}"
        text_stock = f"Stock: {info['Stock']}"
        
        cv2.putText(display, text_cas, (box_w_start + 20, box_h_start + 90), FONT, 0.9, COLOR_YELLOW, 2)
        cv2.putText(display, text_brand, (box_w_start + 20, box_h_start + 130), FONT, 0.7, COLOR_WHITE, 2)
        cv2.putText(display, text_stock, (box_w_start + 300, box_h_start + 130), FONT, 0.7, COLOR_WHITE, 1)

    else:
        # 掃描中提示
        cv2.putText(display, "Scanning...", (50, h - 50), FONT, 0.8, (200, 200, 200), 1)

    return display

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("      Chemical Bottle Scanner - UX Enhanced")
    print("=" * 60)
    
    # 1. 選擇檔案
    print("[INFO] Please select your inventory CSV file...")
    inventory_path = select_inventory_file()
    if not inventory_path: return
    print(f"[OK] Selected: {inventory_path}")
    
    # 2. 設定 Tesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    
    # 3. 載入庫存
    inventory = InventoryManager(inventory_path)
    if inventory.total_count == 0:
        print("[ERROR] Inventory empty or load failed.")
        return
    
    # 4. 初始化鏡頭
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return
        
    print("[INFO] Scanner started. Press 'Q' to quit.")
    cv2.namedWindow(MAIN_WINDOW_NAME, cv2.WINDOW_NORMAL)
    
    # 變數初始化
    frame_count = 0
    fps_timer = cv2.getTickCount()
    fps_counter = 0
    fps = 0
    
    # [新增] 視覺暫留控制變數
    last_valid_info = None  # 儲存上一次找到的藥品資訊
    last_valid_time = 0     # 儲存找到的時間點
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # FPS 計算
        fps_counter += 1
        if fps_counter >= 30:
            current_time = cv2.getTickCount()
            fps = fps_counter / ((current_time - fps_timer) / cv2.getTickFrequency())
            fps_timer = current_time
            fps_counter = 0
        
        preprocessed = preprocess_frame(frame)
        current_frame_info = None # 這一幀是否有找到東西
        
        # --- OCR 辨識 ---
        if frame_count % OCR_FRAME_INTERVAL == 0:
            ocr_text = perform_ocr(preprocessed)
            valid_cas_numbers = extract_cas_numbers(ocr_text)
            
            # 比對庫存
            for cas in valid_cas_numbers:
                info = inventory.lookup(cas)
                if info:
                    current_frame_info = info
                    # [更新] 只要找到，就更新「最後有效資訊」與「時間」
                    last_valid_info = info
                    last_valid_time = time.time()
                    print(f"[FOUND] {info['CAS']} @ {info['Location']}")
                    break # 一次鎖定一個
        
        # --- [新增] 決定顯示內容 (核心邏輯) ---
        display_info = None
        
        # 情況 1: 這一幀剛好掃到 -> 直接顯示
        if current_frame_info:
            display_info = current_frame_info
            
        # 情況 2: 這一幀沒掃到，但距離上次掃到還在 3 秒內 -> 繼續顯示舊的 (視覺暫留)
        elif last_valid_info and (time.time() - last_valid_time < RESULT_PERSISTENCE_SECONDS):
            display_info = last_valid_info
            
        # 繪製畫面
        display_frame = draw_overlay(frame, display_info, inventory, fps)
        
        cv2.imshow(MAIN_WINDOW_NAME, display_frame)
        # cv2.imshow("Debug", cv2.resize(preprocessed, (400, 300))) # 如果想看黑白畫面可打開
        
        frame_count += 1
        if (cv2.waitKey(1) & 0xFF) in [ord('q'), ord('Q')]:
            break
            
    cap.release()
    cv2.destroyAllWindows()
    
    # 產生報告
    print("\n[INFO] Generating report...")
    report_path = inventory.generate_report()
    print(f"[OK] Report saved to: {report_path}")

if __name__ == "__main__":
    main()
