# 專案總覽

本儲存庫整合了 Python 演算法/伺服器端與 Unreal Engine 客戶端/模擬環境。

---

## 目錄結構與架構說明

```text
.
├── AI-Town-main/      # Python 後端與演算法模組（WebSocket / UDP 通訊、AI 邏輯）
├── sourceProject/     # Unreal Engine 專案主體（客戶端模擬、場景資產與相機控制）
├── .gitattributes     # Git LFS 大檔追蹤配置
└── .gitignore          # 忽略編譯暫存與快取檔案
