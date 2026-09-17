import os
import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as T
from PIL import Image
from ultralytics import YOLO

class ReIDDatabase:
    """載入原始 ROI 矩陣，並透過模型轉換為固定長度的 L2 正規化特徵矩陣"""
    # 注意：這裡新增了 reid_model 參數
    def __init__(self, clean_db_folder: str, reid_model: torch.nn.Module, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.names = []
        features_list = []
        
        # 建立前處理管線 (確保所有長寬不一的圖，都變成 256x128)
        self.transform = T.Compose([
            T.Resize((256, 128)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        print(f"⚡ 正在提取 Re-ID 特徵資料庫: {clean_db_folder}...")
        
        # 將模型設為推論模式並移至 GPU
        reid_model.eval()
        reid_model.to(self.device)
        
        if os.path.exists(clean_db_folder):
            for file in os.listdir(clean_db_folder):
                if file.endswith(".npy"):
                    name = file.split('_')[0] 
                    file_path = os.path.join(clean_db_folder, file)
                    
                    try:
                        # 1. 載入原始 BGR 影像矩陣
                        roi_bgr = np.load(file_path)
                        if roi_bgr.size == 0: continue
                        
                        # 2. 轉換為 RGB 與 PIL 格式
                        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
                        img_pil = Image.fromarray(roi_rgb)
                        
                        # 3. 縮放、標準化並擴充 Batch 維度 -> [1, 3, 256, 128]
                        input_tensor = self.transform(img_pil).unsqueeze(0).to(self.device)
                        
                        # 4. 送入模型提取特徵
                        with torch.no_grad():
                            feature = reid_model(input_tensor)
                            # 將輸出確保展平為 1D，並進行 L2 正規化
                            feature_norm = F.normalize(feature.view(1, -1), p=2, dim=1)
                            
                        self.names.append(name)
                        features_list.append(feature_norm)
                    except Exception as e:
                        print(f"處理 {file} 失敗: {e}")
        else:
            print(f"❌ 找不到特徵資料庫目錄: {clean_db_folder}")
                
        if features_list:
            # 此時所有的 feature_norm 維度皆絕對一致，torch.cat 即可成功執行
            self.gallery_matrix = torch.cat(features_list, dim=0).to(self.device)
            print(f"✅ 資料庫初始化完成，共 {len(self.names)} 筆向量。矩陣維度: {self.gallery_matrix.shape}")
        else:
            self.gallery_matrix = None
            print("⚠️ 警告：資料庫為空！")

class MOTReIDPipeline:
    """整合 YOLO + ByteTrack + Re-ID 的單一資料流管線"""
    def __init__(self, db: ReIDDatabase, reid_model: torch.nn.Module, threshold: float = 0.65):
        # 1. 載入物件偵測與追蹤模型
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_yolo = os.path.join(script_dir, "yolov8n.pt")
        yolo_path = local_yolo if os.path.exists(local_yolo) else "yolov8n.pt"
        self.yolo = YOLO(yolo_path)
        
        # 2. 注入資料庫與 Re-ID 模型
        self.db = db
        self.reid_model = reid_model
        self.reid_model.eval()
        self.device = db.device
        self.threshold = threshold
        
        # 狀態字典：ByteTrack ID -> 綁定的資料庫人名
        self.track_identities = {} 
        
        # Re-ID 前處理管線 (依照 OSNet 標準)
        self.transform = T.Compose([
            T.Resize((256, 128)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def extract_feature(self, img_bgr, box) -> torch.Tensor:
        """擷取 ROI 並輸出 L2 正規化特徵"""
        x1, y1, x2, y2 = map(int, box)
        h, w = img_bgr.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        roi_bgr = img_bgr[y1:y2, x1:x2]
        if roi_bgr.size == 0:
            return None
            
        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(roi_rgb)
        
        input_tensor = self.transform(img_pil).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feature = self.reid_model(input_tensor)
            feature_norm = F.normalize(feature, p=2, dim=1) # 查詢端 A 的 L2 正規化
        return feature_norm

    def process_frame(self, frame: np.ndarray):
        """執行完整管線，回傳 (繪製好的影像, detected_people)"""
        detected_people = []

        if self.db.gallery_matrix is None:
            return frame, detected_people

        results = self.yolo.track(
            frame,
            tracker="bytetrack.yaml",
            classes=[0],
            persist=True,
            verbose=False
        )

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                if track_id not in self.track_identities:
                    query_feat = self.extract_feature(frame, box)

                    if query_feat is not None:
                        similarities = torch.mm(
                            query_feat,
                            self.db.gallery_matrix.t()
                        ).squeeze(0)

                        max_sim, max_idx = torch.max(similarities, dim=0)

                        if max_sim.item() > self.threshold:
                            self.track_identities[track_id] = self.db.names[max_idx.item()]
                        else:
                            self.track_identities[track_id] = f"Unknown_{track_id}"

                person_name = self.track_identities.get(track_id, "Unknown")
                detected_people.append(person_name)

                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    person_name,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

        return frame, detected_people