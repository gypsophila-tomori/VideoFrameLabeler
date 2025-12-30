"""
文件操作工具 - 配置管理和标注保存
"""
import os
import json
import cv2
from datetime import datetime


class ConfigManager:
    """配置管理器"""
    
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "last_video_dir": "./video",
        "labels": {
            "疏除": "#FF4444",
            "保留": "#44FF44"
        }
    }
    
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"加载配置失败: {e}")
                
        return self.DEFAULT_CONFIG.copy()
        
    def save_config(self):
        """保存配置"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
            
    def get_labels(self):
        """获取标签配置"""
        return self.config.get("labels", self.DEFAULT_CONFIG["labels"])
        
    def set_labels(self, labels):
        """设置标签配置"""
        self.config["labels"] = labels
        self.save_config()
        
    def get_last_video_dir(self):
        """获取上次的视频目录"""
        return self.config.get("last_video_dir", "./video")
        
    def set_last_video_dir(self, path):
        """设置视频目录"""
        self.config["last_video_dir"] = path
        self.save_config()


class AnnotationManager:
    """标注数据管理器"""
    
    ANNOTATIONS_FILE = "saved_images/annotations.json"
    ANNOTATION_DIR = "saved_images/Annotation"
    REFERENCE_DIR = "saved_images/Reference"
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self.ANNOTATION_DIR, exist_ok=True)
        os.makedirs(self.REFERENCE_DIR, exist_ok=True)
        
    def load_annotations(self):
        """加载所有标注元数据"""
        if os.path.exists(self.ANNOTATIONS_FILE):
            try:
                with open(self.ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载标注数据失败: {e}")
        return {}
        
    def save_annotations(self, annotations):
        """保存所有标注元数据"""
        try:
            with open(self.ANNOTATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(annotations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存标注数据失败: {e}")
            
    def save_annotation(self, data):
        """保存单个标注"""
        try:
            image_id = data["image_id"]
            
            # 保存原始ROI图像（无标记）
            ann_path = os.path.join(self.ANNOTATION_DIR, f"{image_id}.png")
            cv2.imwrite(ann_path, data["roi_image"])
            
            # 保存带标记的ROI图像
            ref_path = os.path.join(self.REFERENCE_DIR, f"{image_id}.png")
            cv2.imwrite(ref_path, data["roi_image_with_points"])
            
            # 更新元数据
            annotations = self.load_annotations()
            annotations[image_id] = {
                "source_video": data["source_video"],
                "frame_number": data["frame_number"],
                "roi_coords": data["roi_coords"],
                "comment": data["comment"],
                "points": data["points"],
                "remove_count": sum(1 for p in data["points"] if p["type"] == "remove"),
                "keep_count": sum(1 for p in data["points"] if p["type"] == "keep"),
                "created_at": datetime.now().isoformat()
            }
            self.save_annotations(annotations)
            
            print(f"已保存: {image_id}")
            return True
            
        except Exception as e:
            print(f"保存标注失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def delete_annotation(self, image_id):
        """删除标注"""
        try:
            annotations = self.load_annotations()
            if image_id in annotations:
                del annotations[image_id]
                self.save_annotations(annotations)
            return True
        except Exception as e:
            print(f"删除标注失败: {e}")
            return False