import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout, QSizePolicy, QCheckBox, QAction,
    QSlider, QSpinBox, QScrollArea, QFileDialog
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QKeySequence,
    QRegion, QBitmap
)
from PyQt5.QtCore import Qt, QPoint

class ImageLabel(QLabel):
    def __init__(self, parent=None, scroll_area=None, main_window=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)  # 允许控件在被点击时获得焦点
        self.zoom_factor = 1.0
        self.drawing = False
        self.last_point = None
        self.brush_size = 5
        self.brush_color = QColor(255, 255, 255)
        self.eraser_color = QColor(0, 0, 0)
        self.erase_mode = False
        self.mask = None
        self.image = None
        self.display_image = None
        self.show_mask = True
        self.scroll_area = scroll_area
        self.main_window = main_window  # 保存对主窗口的引用

    def set_mask(self, mask):
        self.mask = mask

    def set_image(self, image):
        self.image = image

    def set_brush_size(self, size):
        self.brush_size = size

    def set_brush_color(self, color):
        self.brush_color = color

    def set_eraser_color(self, color):
        self.eraser_color = color

    def set_erase_mode(self, mode):
        self.erase_mode = mode

    def set_show_mask(self, show):
        self.show_mask = show

    def wheelEvent(self, event):
        if self.image is None:
            return  # 添加检查

        # 获取鼠标指针在 ImageLabel 中的位置
        cursor_pos = event.pos()

        # 获取当前缩放因子
        zoom_factor_before = self.zoom_factor

        # 获取当前滚动条位置
        h_scroll_before = self.scroll_area.horizontalScrollBar().value()
        v_scroll_before = self.scroll_area.verticalScrollBar().value()

        # 计算鼠标指针下的图像坐标（缩放前）
        image_x_before = (h_scroll_before + cursor_pos.x()) / zoom_factor_before
        image_y_before = (v_scroll_before + cursor_pos.y()) / zoom_factor_before

        # 调整缩放因子
        if event.angleDelta().y() > 0:
            zoom_factor_new = self.zoom_factor * 1.1
        else:
            zoom_factor_new = self.zoom_factor / 1.1
        zoom_factor_new = max(0.1, min(zoom_factor_new, 10))

        # 更新缩放因子
        self.zoom_factor = zoom_factor_new

        # 更新图像显示
        self.update_display()

        # 计算鼠标指针下的图像坐标（缩放后）
        image_x_after = image_x_before * self.zoom_factor
        image_y_after = image_y_before * self.zoom_factor

        # 计算新的滚动条位置，使得图像坐标保持在鼠标指针的位置
        new_scroll_x = int(image_x_after - cursor_pos.x())
        new_scroll_y = int(image_y_after - cursor_pos.y())

        # 获取滚动条
        h_scroll_bar = self.scroll_area.horizontalScrollBar()
        v_scroll_bar = self.scroll_area.verticalScrollBar()

        # 确保新的滚动条位置在有效范围内
        new_scroll_x = max(0, min(new_scroll_x, h_scroll_bar.maximum()))
        new_scroll_y = max(0, min(new_scroll_y, v_scroll_bar.maximum()))

        # 设置新的滚动条位置
        h_scroll_bar.setValue(new_scroll_x)
        v_scroll_bar.setValue(new_scroll_y)

    def update_display(self):
        if self.image:
            # 创建用于显示的图像
            self.display_image = self.image.copy()
            if self.show_mask and self.mask:
                # 创建半透明红色叠加层
                red_overlay = QImage(self.image.size(), QImage.Format_ARGB32)
                red_overlay.fill(Qt.transparent)

                # 使用蒙版创建剪切区域
                mask_image = self.mask.convertToFormat(QImage.Format_Mono)
                mask_image.invertPixels()
                mask_region = QRegion(QBitmap.fromImage(mask_image))

                # 在红色叠加层上绘制半透明红色
                painter = QPainter(red_overlay)
                painter.setClipRegion(mask_region)
                painter.fillRect(self.mask.rect(), QColor(255, 0, 0, 128))
                painter.end()

                # 将红色叠加层绘制到显示图像上
                painter = QPainter(self.display_image)
                painter.drawImage(0, 0, red_overlay)
                painter.end()

            # 根据缩放因子调整图像大小
            zoom_factor = self.zoom_factor
            scaled_width = int(self.display_image.width() * zoom_factor)
            scaled_height = int(self.display_image.height() * zoom_factor)
            scaled_image = self.display_image.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            # 设置图像并调整标签大小
            self.setPixmap(QPixmap.fromImage(scaled_image))
            self.setFixedSize(scaled_image.size())

    def mousePressEvent(self, event):
        if self.image is None:
            return  # 添加检查
        if event.button() == Qt.LeftButton:
            self.setFocus()  # 将焦点设置到 ImageLabel
            self.drawing = True
            self.last_point = self.get_image_coordinates(event.pos())
            if self.main_window:
                self.main_window.save_mask_state()  # 保存当前状态以用于撤销

    def mouseMoveEvent(self, event):
        if self.image is None:
            return  # 添加检查
        if self.drawing:
            current_point = self.get_image_coordinates(event.pos())
            if current_point and self.last_point:
                painter = QPainter(self.mask)
                if self.erase_mode:
                    pen = QPen(self.eraser_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                else:
                    pen = QPen(self.brush_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(self.last_point, current_point)
                painter.end()
                self.last_point = current_point
                self.update_display()

    def mouseReleaseEvent(self, event):
        if self.image is None:
            return  # 添加检查
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def get_image_coordinates(self, pos):
        if self.image is None:
            return None  # 添加检查
        # 计算图像坐标，不考虑滚动条
        image_x = pos.x() / self.zoom_factor
        image_y = pos.y() / self.zoom_factor

        # 确保坐标在图像范围内
        image_x = max(0, min(image_x, self.image.width() - 1))
        image_y = max(0, min(image_y, self.image.height() - 1))

        return QPoint(int(image_x), int(image_y))


class SegmentationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Segmentation Annotation Tool")
        self.setGeometry(100, 100, 800, 600)

        # 创建滚动区域和图像标签
        self.scroll_area = QScrollArea()
        self.image_label = ImageLabel(self, self.scroll_area, main_window=self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.load_button = QPushButton("Load Images", self)
        self.load_button.clicked.connect(self.load_images)

        self.prev_button = QPushButton("Previous Image", self)
        self.prev_button.clicked.connect(self.load_previous_image)
        self.prev_button.setEnabled(False)  # 在加载图像前不可用

        self.next_button = QPushButton("Next Image", self)
        self.next_button.clicked.connect(self.load_next_image)
        self.next_button.setEnabled(False)  # 在加载图像前不可用

        self.delete_button = QPushButton("Delete Image", self)
        self.delete_button.clicked.connect(self.delete_current_image)
        self.delete_button.setEnabled(False)  # 在加载图像前不可用

        self.auto_save_checkbox = QCheckBox("Auto Save", self)
        self.auto_save_checkbox.setChecked(True)

        self.show_mask_checkbox = QCheckBox("Show Annotations", self)
        self.show_mask_checkbox.setChecked(True)
        self.show_mask_checkbox.stateChanged.connect(self.show_mask_checkbox_state_changed)

        self.erase_mode = False
        self.brush_button = QPushButton("Brush", self)
        self.brush_button.setCheckable(True)
        self.brush_button.setChecked(True)
        self.brush_button.clicked.connect(self.set_brush_mode)

        self.eraser_button = QPushButton("Eraser", self)
        self.eraser_button.setCheckable(True)
        self.eraser_button.clicked.connect(self.set_eraser_mode)

        self.brush_size_label = QLabel("Brush Size:")
        self.brush_size_spinbox = QSpinBox()
        self.brush_size_spinbox.setRange(1, 50)
        self.brush_size_spinbox.setValue(5)
        self.brush_size_spinbox.valueChanged.connect(self.change_brush_size)

        # 添加计数和图片名称标签
        self.count_label = QLabel("Annotated samples: 0", self)
        self.image_name_label = QLabel("Image: None", self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.delete_button)  # 添加删除按钮
        button_layout.addWidget(self.auto_save_checkbox)
        button_layout.addWidget(self.show_mask_checkbox)
        button_layout.addWidget(self.brush_button)
        button_layout.addWidget(self.eraser_button)
        button_layout.addWidget(self.brush_size_label)
        button_layout.addWidget(self.brush_size_spinbox)

        # 创建一个布局来放置计数和图片名称标签
        label_layout = QHBoxLayout()
        label_layout.addWidget(self.count_label)
        label_layout.addWidget(self.image_name_label)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addLayout(label_layout)  # 添加标签布局
        layout.addWidget(self.scroll_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 初始化文件夹路径为 None
        self.main_folder = None
        self.image_folder = None
        self.mask_folder = None
        self.save_folder = None

        self.image_list = []
        self.current_index = -1

        self.image = None
        self.mask = None
        self.display_image = None  # 用于显示的图像
        self.drawing = False
        self.last_point = None
        self.brush_size = 5
        self.brush_color = QColor(255, 255, 255)  # 白色，用于绘制蒙版
        self.eraser_color = QColor(0, 0, 0)       # 黑色，用于擦除蒙版

        # 添加历史栈用于撤销操作
        self.mask_history = []

        # 设置快捷键
        undo_shortcut = QKeySequence("Ctrl+Z")
        self.undo_action = QAction(self)
        self.undo_action.setShortcut(undo_shortcut)
        self.undo_action.triggered.connect(self.undo)
        self.addAction(self.undo_action)

        # 初始化已标记样本计数
        self.annotated_count = 0

        # 初始化 ImageLabel 的参数
        self.image_label.set_brush_size(self.brush_size)
        self.image_label.set_brush_color(self.brush_color)
        self.image_label.set_eraser_color(self.eraser_color)
        self.image_label.set_erase_mode(self.erase_mode)

    def load_images(self):
        # 选择主文件夹
        main_folder = QFileDialog.getExistingDirectory(
            self, "Select Main Folder", ""
        )
        if not main_folder:
            print("No main folder selected.")
            return

        # 设置文件夹路径
        self.main_folder = main_folder
        self.image_folder = os.path.join(self.main_folder, 'images')
        self.mask_folder = os.path.join(self.main_folder, 'masks')
        self.save_folder = self.mask_folder  # 保存蒙版的文件夹，与 mask_folder 相同

        # 检查 images 文件夹是否存在
        if not os.path.exists(self.image_folder):
            print(f"Image folder does not exist: {self.image_folder}")
            return

        # 如果 masks 文件夹不存在，则自动创建
        if not os.path.exists(self.mask_folder):
            try:
                os.makedirs(self.mask_folder)
                print(f"Created mask folder: {self.mask_folder}")
            except Exception as e:
                print(f"Failed to create mask folder: {e}")
                return

        # 获取图像列表
        self.image_list = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(".png") or f.lower().endswith(".jpg")
        ]
        self.image_list.sort()  # 排序以确保顺序一致

        if not self.image_list:
            print("No images found in the selected folder.")
            return

        self.current_index = 0
        self.load_current_image()
        self.next_button.setEnabled(len(self.image_list) > 1)
        self.prev_button.setEnabled(False)
        self.delete_button.setEnabled(True)
        self.annotated_count = self.current_index + 1
        self.update_count_label()

    def load_current_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_list):
            print("Current index out of range.")
            self.image_label.clear()
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.image_name_label.setText("Image: None")  # 更新图片名称
            return

        filename = self.image_list[self.current_index]
        image_path = os.path.join(self.image_folder, filename)
        mask_path = os.path.join(self.mask_folder, filename)
        print("Image path:", image_path)
        print("Mask path:", mask_path)
        self.image = QImage(image_path).convertToFormat(QImage.Format_RGB32)
        if os.path.exists(mask_path):
            self.mask = QImage(mask_path).convertToFormat(QImage.Format_Grayscale8)
            # 如果蒙版尺寸与图像尺寸不一致，调整蒙版尺寸
            if self.mask.size() != self.image.size():
                self.mask = self.mask.scaled(self.image.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            # 如果蒙版不存在，创建一个黑色的蒙版
            self.mask = QImage(self.image.size(), QImage.Format_Grayscale8)
            self.mask.fill(0)
        if not self.image.isNull() and not self.mask.isNull():
            print("Successfully loaded image and mask.")
            # 设置图像和蒙版到 ImageLabel
            self.image_label.set_image(self.image)
            self.image_label.set_mask(self.mask)

            # 计算适当的缩放因子以适应视口
            viewport_size = self.scroll_area.viewport().size()
            image_size = self.image.size()
            width_ratio = viewport_size.width() / self.image.width()
            height_ratio = viewport_size.height() / self.image.height()
            zoom_factor = min(width_ratio, height_ratio)
            self.image_label.zoom_factor = zoom_factor

            self.image_label.update_display()
            self.mask_history.clear()  # 清空历史栈
            self.save_mask_state()     # 保存初始状态
        else:
            print("Failed to load image or mask.")

        # 更新按钮的启用状态
        self.next_button.setEnabled(self.current_index < len(self.image_list) - 1)
        self.prev_button.setEnabled(self.current_index > 0)
        self.delete_button.setEnabled(True)

        # 更新图片名称和计数
        self.image_name_label.setText(f"Image: {filename}")
        self.annotated_count = self.current_index + 1
        self.update_count_label()

    def load_next_image(self):
        # 自动保存当前蒙版（如果选中）
        if self.auto_save_checkbox.isChecked():
            self.save_mask()
        # 加载下一张图片
        if self.current_index + 1 < len(self.image_list):
            self.current_index += 1
            self.load_current_image()
        else:
            print("No more images.")
            self.next_button.setEnabled(False)

    def load_previous_image(self):
        # 自动保存当前蒙版（如果选中）
        if self.auto_save_checkbox.isChecked():
            self.save_mask()
        # 加载上一张图片
        if self.current_index - 1 >= 0:
            self.current_index -= 1
            self.load_current_image()
        else:
            print("This is the first image.")
            self.prev_button.setEnabled(False)

    def delete_current_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_list):
            print("No image to delete.")
            return

        filename = self.image_list[self.current_index]
        image_path = os.path.join(self.image_folder, filename)
        mask_path = os.path.join(self.mask_folder, filename)
        save_path = os.path.join(self.save_folder, filename)

        # 删除图像文件
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"Deleted image: {image_path}")
            else:
                print(f"Image file does not exist: {image_path}")
        except Exception as e:
            print(f"Failed to delete image: {e}")

        # 删除蒙版文件
        try:
            if os.path.exists(mask_path):
                os.remove(mask_path)
                print(f"Deleted mask: {mask_path}")
            elif os.path.exists(save_path):
                os.remove(save_path)
                print(f"Deleted processed mask: {save_path}")
            else:
                print(f"Mask file does not exist: {mask_path} or {save_path}")
        except Exception as e:
            print(f"Failed to delete mask: {e}")

        # 从列表中移除
        del self.image_list[self.current_index]

        # 再次检查是否有图像剩余
        if not self.image_list:
            print("All images have been deleted.")
            self.image_label.clear()
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.current_index = -1
            self.image_name_label.setText("Image: None")
            self.annotated_count = 0
            self.update_count_label()
        else:
            # 调整当前索引并自动切换到下一张或上一张图像
            if self.current_index >= len(self.image_list):
                self.current_index = len(self.image_list) - 1
            self.load_current_image()

    def save_mask(self):
        if self.mask is not None:
            filename = self.image_list[self.current_index]
            save_path = os.path.join(self.save_folder, filename)
            self.mask.save(save_path)
            print(f"Mask saved to {save_path}")

    def save_mask_state(self):
        # 将当前蒙版的副本保存到历史栈
        if self.mask is not None:
            mask_copy = self.mask.copy()
            self.mask_history.append(mask_copy)
            # 可选：限制历史栈大小
            if len(self.mask_history) > 20:
                self.mask_history.pop(0)

    def undo(self):
        if len(self.mask_history) > 1:
            # 弹出当前的状态（因为当前状态已经在mask中）
            self.mask_history.pop()
            # 获取上一个状态
            self.mask = self.mask_history[-1].copy()
            # 更新 ImageLabel 中的蒙版并刷新显示
            self.image_label.set_mask(self.mask)
            self.image_label.update_display()
        else:
            print("No more actions to undo.")

    def show_mask_checkbox_state_changed(self, state):
        self.image_label.set_show_mask(self.show_mask_checkbox.isChecked())
        self.image_label.update_display()

    def set_brush_mode(self):
        self.erase_mode = False
        self.image_label.set_erase_mode(False)
        self.brush_button.setChecked(True)
        self.eraser_button.setChecked(False)

    def set_eraser_mode(self):
        self.erase_mode = True
        self.image_label.set_erase_mode(True)
        self.brush_button.setChecked(False)
        self.eraser_button.setChecked(True)

    def change_brush_size(self, value):
        self.brush_size = value
        self.image_label.set_brush_size(value)

    def keyPressEvent(self, event):
        # 处理Ctrl+Z快捷键
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo()
        else:
            super().keyPressEvent(event)

    def update_count_label(self):
        self.count_label.setText(f"Annotated samples: {self.annotated_count}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SegmentationTool()
    window.show()
    sys.exit(app.exec_())
