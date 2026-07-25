# 安装必要的库（如果还没有安装）
# pip install pandas numpy scipy statsmodels matplotlib seaborn

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.diagnostic import het_breuschpagan
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文显示（可选）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用于显示中文
plt.rcParams['axes.unicode_minus'] = False
# 方法1：从seaborn内置数据加载（推荐）
penguins = sns.load_dataset('penguins')

# 方法2：如果没有网络，手动创建模拟数据（见附录）

# 查看数据基本信息
print(penguins.head())
print(penguins.info())

# 删除缺失值（简化处理）
penguins_clean = penguins.dropna()
print(f"清洗后样本量: {len(penguins_clean)}")
# 查看分组统计
group_stats = penguins_clean.groupby('species')['bill_length_mm'].agg(['mean', 'std', 'count'])
print("各品种企鹅喙长描述统计：")
print(group_stats)

# 箱线图可视化
plt.figure(figsize=(10, 6))
sns.boxplot(data=penguins_clean, x='species', y='bill_length_mm')
plt.title('不同品种企鹅喙长分布')
plt.xlabel('品种')
plt.ylabel('喙长 (mm)')
plt.show()

# 小提琴图（显示分布形状）
plt.figure(figsize=(10, 6))
sns.violinplot(data=penguins_clean, x='species', y='bill_length_mm')
plt.title('不同品种企鹅喙长分布（小提琴图）')
plt.show()