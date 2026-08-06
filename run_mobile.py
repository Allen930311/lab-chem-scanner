"""
Chemical Bottle Scanner - Mobile Launcher
=========================================
透過手機當作鏡頭（DroidCam）來執行掃描程式。
"""

# 正確 import 主程式模組
import cas_scanner

# =========================================================
# 修改攝影機設定為手機鏡頭
# =========================================================

print("[Launcher] 正在切換至手機鏡頭模式...")
print("[Launcher] 請確認 DroidCam 已開啟並連線。")

# 將攝影機索引從 0 (電腦內建) 改成 1 (DroidCam)
# 如果 1 沒畫面，可以試試 2
cas_scanner.CAMERA_INDEX = 1

# =========================================================
# 執行主程式 (含例外處理)
# =========================================================
if __name__ == "__main__":
    try:
        cas_scanner.main()
    except Exception as e:
        print(f"\n[Launcher Error] 發生錯誤: {e}")
        print("=" * 50)
        print("可能原因:")
        print("  1. DroidCam 軟體未開啟")
        print("  2. 電腦端 DroidCam Client 未連線")
        print("  3. 攝影機索引錯誤 (請嘗試改成 0 或 2)")
        print("=" * 50)
        input("按 Enter 鍵結束...")
