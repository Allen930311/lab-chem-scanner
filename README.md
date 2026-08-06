# lab-chem-scanner 🧪📦

Webcam-based chemical inventory scanner for research labs. Point a camera at a reagent bottle, OCR the **CAS number** off the label, match it against your inventory CSV, and get an automatic missing-items report when you finish.

Built to replace the annual "two people, one clipboard, four hours" chemical stocktake in a synthetic chemistry lab.

> 中文說明見下方 [中文](#中文說明)

---

## Why CAS numbers

Lab chemical stocktakes are done by reading labels out loud and ticking a printed list. It is slow, error-prone, and nobody wants to do it. Bottle labels vary wildly in font and condition, but almost all of them carry a **CAS Registry Number** — a short, structured, checksum-verifiable identifier. That makes CAS the one field you can reliably OCR off a battered bottle.

This tool scans for CAS numbers, validates them with the official CAS check-digit algorithm (so OCR noise gets rejected instead of silently corrupting your count), and reconciles against your inventory.

## Features

- **Live scanning** — reads CAS numbers off bottle labels through any webcam
- **CAS check-digit validation** — rejects misread digits before they reach your data
- **Smart freeze** — result box holds on screen for 3 s so you can confirm without a steady hand
- **History sidebar** — last 8 scans stay visible, so you notice what you missed
- **GUI file picker** — choose your inventory CSV at launch, no code editing
- **Bilingual CSV headers** — accepts English (`CAS,Name,Location,Stock`) or Chinese (`CAS,上層藥品名稱,廠牌,數量`); UTF-8-sig handled
- **Missing-items report** — exports `missing_report_<timestamp>.csv` on exit
- **Phone as camera** — `run_mobile.py` launcher for DroidCam, so you can walk the shelves

## Requirements

**1. Python 3.9+**

**2. Tesseract OCR** (must be installed separately)

- Windows: [Tesseract-OCR installer (UB Mannheim)](https://github.com/UB-Mannheim/tesseract/wiki) — default path `C:\Program Files\Tesseract-OCR`
- macOS: `brew install tesseract`
- Debian/Ubuntu: `sudo apt install tesseract-ocr`

If Tesseract is not at the Windows default path, set the env var:

```bash
# Windows
set TESSERACT_PATH=D:\Tesseract-OCR\tesseract.exe
# macOS / Linux
export TESSERACT_PATH=tesseract
```

**3. Python packages**

```bash
pip install -r requirements.txt
```

## Usage

```bash
python cas_scanner.py
```

A file dialog opens — pick an inventory CSV (start with [`data/sample_inventory.csv`](data/sample_inventory.csv)). Hold a bottle up to the camera. Press **Q** to quit; a missing-items report is written next to your CSV.

Using a phone as the camera (via DroidCam):

```bash
python run_mobile.py
```

Or set the camera index directly:

```bash
CAMERA_INDEX=1 python cas_scanner.py
```

## Inventory CSV format

| Column | Chinese header | Meaning |
|---|---|---|
| `CAS` | `CAS` | CAS Registry Number, e.g. `67-56-1` |
| `Name` | `上層藥品名稱` | Chemical name |
| `Location` | `廠牌` | Shelf location or supplier |
| `Stock` | `數量` | Quantity, free text (`4 L`, `25 G*2`) |

Two ready-made samples are in [`data/`](data/) — one English-header, one Chinese-header, to show the mapping. **Replace them with your own inventory; do not commit real lab inventory to a public repo.**

## Config

All in the `CONFIGURATION` block at the top of `cas_scanner.py`:

| Setting | Default | Notes |
|---|---|---|
| `TESSERACT_PATH` | Windows default install path | env var `TESSERACT_PATH` |
| `CAMERA_INDEX` | `0` | env var `CAMERA_INDEX`; `1`/`2` for external or DroidCam |
| `OCR_FRAME_INTERVAL` | `10` | run OCR every N frames — raise it if your machine lags |
| `RESULT_PERSISTENCE_SECONDS` | `3.0` | how long a hit stays frozen on screen |

## Known limitations

- Handwritten and heavily damaged labels do not OCR reliably; those still need manual entry.
- Name-based fuzzy matching is stubbed — matching is CAS-driven by design, since chemical names OCR far worse than digit strings.
- Tested on Windows with a USB webcam and DroidCam. Should work anywhere OpenCV + Tesseract do, but that is untested.

## License

MIT — see [LICENSE](LICENSE).

---

## 中文說明

實驗室藥品盤點掃描器。用鏡頭對準藥罐，OCR 讀取標籤上的 **CAS 號碼**，即時比對庫存清單，盤點結束自動產出缺漏報告。

原本是為了解決合成化學實驗室每年「兩個人拿夾板對四小時」的藥品盤點而做的。

**為什麼是掃 CAS 號**：藥罐標籤字體、破損程度千差萬別，但幾乎都印有 CAS 號——短、結構固定、而且**有檢查碼可驗證**。所以 CAS 是唯一能在爛標籤上穩定辨識的欄位。程式會用官方 CAS 檢查碼演算法驗證，OCR 讀錯的直接擋掉，不會默默汙染盤點資料。

**主要功能**：即時掃描｜CAS 檢查碼驗證｜掃到後畫面凍結 3 秒方便確認｜右側顯示最近 8 筆掃描紀錄｜啟動時 GUI 選檔｜中英文 CSV 標題都吃（UTF-8-sig）｜自動匯出缺漏報告｜可用手機當鏡頭（DroidCam）

**安裝**：需另外裝 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)，然後 `pip install -r requirements.txt`。Tesseract 不在預設路徑的話設環境變數 `TESSERACT_PATH`。

**執行**：`python cas_scanner.py` → 跳出視窗選 CSV（可先用 `data/sample_inventory.csv` 試）→ 拿藥罐對鏡頭 → 按 **Q** 結束並產出缺漏報告。

**CSV 欄位**：`CAS, 上層藥品名稱, 廠牌, 數量`（英文標題 `CAS, Name, Location, Stock` 也可）。

⚠️ `data/` 裡是示範用的公開常見試劑資料，請換成你自己的清單，**不要把實驗室真實庫存 commit 到公開 repo**。
