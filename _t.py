import numpy as np
import cv2
from automation.image_finder import ImageFinder

f = ImageFinder()
# 构造 400x300 屏幕图（渐变背景），左上 (80,60) 放一个多色"小图标"
yy, xx = np.mgrid[0:300, 0:400]
screen = np.dstack([(30 + xx // 3).astype(np.uint8),
                     (30 + yy // 3).astype(np.uint8),
                     (40 + (xx + yy) // 5).astype(np.uint8)])
# 画一个 30x40 的彩色图案，避免纯色模板的匹配退化
for i in range(30):
    for j in range(40):
        screen[62 + j, 82 + i] = (i * 7 % 255, j * 5 % 255, (i + j) * 3 % 255)
template = screen[62:100, 82:110].copy()
# 模板左上 (82,62)，宽 28 高 38 -> center=(96,81)

# 1) 数组匹配
res = f.match_from_array(screen, template, 0.8)
assert res, '模板匹配失败'
b = res[0]
print('数组匹配 center:', b['center'], 'max_val=%.2f' % b['max_val'])
assert abs(b['center'][0] - 96) <= 2 and abs(b['center'][1] - 81) <= 2, b['center']
assert b['max_val'] > 0.95, b['max_val']

# 2) base64 往返（JPEG 压缩）与读取
b64 = f.ndarray_to_base64(template, compress_jpeg=True)
re = f.read_template_source(None, b64)
assert re is not None and re.shape == template.shape[:2] and re.shape[2] == 3, 'base64 解码失败'
print('base64 模板恢复 OK 形状', re.shape)

# 3) 颜色定位：单独画一个红色块（不影响模板图案），用 3 个相对点定位
cv2.rectangle(screen, (200, 150), (230, 180), (0, 0, 255), -1)  # 红色块
pts = [
    {'dx': 0, 'dy': 0, 'r': 255, 'g': 0, 'b': 0},     # 基准=块内
    {'dx': 5, 'dy': 8, 'r': 255, 'g': 0, 'b': 0},
    {'dx': -5, 'dy': 8, 'r': 255, 'g': 0, 'b': 0},
]
hits = f.find_color_points(pts, tolerance=20, screen_img=screen)
assert hits, '颜色定位失败'
print('颜色定位 base:', hits[0]['base_pt'], 'dev=%.1f' % hits[0]['max_dev'])
assert 205 <= hits[0]['base_pt'][0] <= 220, hits[0]['base_pt'][0]
assert 155 <= hits[0]['base_pt'][1] <= 170, hits[0]['base_pt'][1]

print('ALL PASS')
f2 = ImageFinder()
print('threshold default', f2.confidence)