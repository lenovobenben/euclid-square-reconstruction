# Euclid-Square-Reconstruction · 四个边内点恢复正方形

给定四点，要求它们分别位于正方形四条边的严格内部，研究存在条件、全部解数及尺规构造。本项目是 Euclid 几何研究系列的第 7 题。

## 主要结果

解数只能为 **零个、一个或无穷多个**。四点必须组成严格凸四边形。两条对角线等长且垂直时有无穷多解，其余输入用几何极值判据或等价坐标判据确定零解或唯一解。

对唯一解输入，十字架法先作 $BE=AC$ 且 $BE\perp AC$，取 $B,E$ 位于直线 $AC$ 异侧，再以 $DE$ 确定一条边，通过平行线和垂线恢复四个顶点。

在单位正方形内独立均匀取四点，唯一解概率为

$$q=\frac47\ln2-\frac{16}{63}-\frac{\sqrt3\pi}{270}-\frac{41\pi}{6720}
\approx0.1027950677614.$$

唯一解概率约 **10.2795068%**，无解概率合计约 **89.7204932%**，无穷多解概率为零。以严格凸为条件，唯一解概率为 $36q/25$，约 **14.8024898%**。

## 文档

| 内容 | 入口 |
|---|---|
| 输入、严格边段约束与工具 | [DESIGN](docs/DESIGN.md) |
| 两种判据、一般证明、连续解族与案例 | [CLASSIFICATION](docs/CLASSIFICATION.md) |
| 十字架作图、正确性与尺规宏 | [ANSWER](docs/ANSWER.md)、[PROOF](docs/PROOF.md)、[CONSTRUCTION](docs/CONSTRUCTION.md) |
| 完整概率表与蒙特卡洛核对 | [PROBABILITY](docs/PROBABILITY.md) |
| 概率闭式的解析证明与精确证书 | [PROBABILITY_PROOF](docs/PROBABILITY_PROOF.md) |

## 运行与核验

在项目根目录使用 SageMath 10.7。

```sh
sage -python experiments/verify_classification.py
sage -python experiments/verify_linear_system.py
sage -python experiments/verify_construction.py
```

分类检查包含 $1,820$ 组有理网格输入。独立线性方程复核了 $51,696$ 种点边对应。十字架构造完成 $441$ 次精确重放。概率解析核验与一亿组抽样命令见 [概率复现](docs/PROBABILITY.md#5-复现)。

Windows PowerShell 可使用固定 Docker 镜像，替换命令末尾的脚本路径和参数运行其他入口。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -e OPENBLAS_NUM_THREADS=1 -v "${PWD}:/workspace" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/verify_classification.py
```

## 来源

题目及十字架作法来自作者的 `ai-math-notes`。项目补充完整分类、严格边内部证明、有限尺规展开、精确重放及随机输入概率分析。[原始问答](https://github.com/lenovobenben/ai-math-notes/blob/main/chatgpt/经典数学题100例-4/001_尺规作图-十字架__691d671c-4bd4-832a-8020-6d1040b2fd4a/001_尺规作图-十字架__691d671c-4bd4-832a-8020-6d1040b2fd4a.md)
