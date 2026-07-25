import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# 设置中文字体支持（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
# 读取广东省Shapefile数据
# 请将路径替换为您的实际文件路径
gdf = gpd.read_file('C:\\Users\\lenovo\\Desktop\\output.shp')

# 创建颜色映射字典
color_mapping = {
    '佛山': 'yellow', '中山': 'yellow', '珠海': 'yellow', '江门': 'yellow',
    '湛江': 'yellow', '肇庆': 'yellow', '阳江': 'yellow', '云浮': 'yellow', '茂名': 'yellow',
    '东莞': 'green', '汕头': 'green', '揭阳': 'green', '潮州': 'green',
    '惠州': 'green', '清远': 'green', '河源': 'green', '韶关': 'green', '汕尾': 'green', '梅州': 'green',
    '广州': 'white', '深圳': 'white'
}

# 为每个地市添加颜色列
# 注意：这里假设您的shapefile中城市名称字段是'NAME'或'城市名称'，请根据实际情况调整
gdf['color'] = gdf['NAME'].map(color_mapping)  # 如果字段名不同，请替换'NAME'

# 创建图形
fig, ax = plt.subplots(1, 1, figsize=(12, 10))

# 绘制地图，按颜色分组
for color in ['yellow', 'green', 'white']:
    subset = gdf[gdf['color'] == color]
    subset.plot(ax=ax, color=color, edgecolor='black', linewidth=0.5)

# 添加城市名称标注
for idx, row in gdf.iterrows():
    # 获取每个多边形的中心点
    centroid = row.geometry.centroid
    ax.text(centroid.x, centroid.y, row['NAME'], 
            fontsize=10, color='black', ha='center', va='center',
            fontweight='bold')

# 设置标题
ax.set_title('广东省市级行政区划图', fontsize=16, fontweight='bold')

# 移除坐标轴
ax.set_axis_off()

# 添加图例
legend_elements = [
    Patch(facecolor='yellow', edgecolor='black', label='黄色组城市'),
    Patch(facecolor='green', edgecolor='black', label='绿色组城市'),
    Patch(facecolor='white', edgecolor='black', label='广深特区')
]
ax.legend(handles=legend_elements, loc='lower right')

# 调整布局
plt.tight_layout()

# 显示图片
plt.show()

# 保存图片（可选）
# plt.savefig('广东省地图.png', dpi=300, bbox_inches='tight')
