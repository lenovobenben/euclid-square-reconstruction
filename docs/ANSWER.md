# 唯一解情形的十字架尺规作图

## 1. 输入与输出

给定四点，已由 [CLASSIFICATION](CLASSIFICATION.md) 判定存在唯一合法正方形。四点按凸包逆时针次序记为 $A,B,C,D$，每点均要求在相应边的严格内部。

本阶段将“一般情形”固定为这个唯一解输入域。根据已有分类，在已知有解的前提下，它等价于两条对角线 $AC,BD$ 不垂直。

输出目标正方形的四个顶点 $P,Q,R,S$ 及四条边段 $PQ,QR,RS,SP$，使 $A,B,C,D$ 依次位于这四条边的内部。

以下使用无刻度直尺和塌圆规。中点、垂线、平行线及长度转移采用经典有限尺规宏，展开见 [CONSTRUCTION](CONSTRUCTION.md)。

## 2. 作出十字架辅助点

1. 连接 $A,C$。
2. 过 $B$ 作直线 $AC$ 的垂线 $\ell$。
3. 将长度 $AC$ 转移到 $B$，作以 $B$ 为圆心、$AC$ 为半径的圆 $\omega$。
4. 取 $\ell$ 与 $\omega$ 的两个交点。从中选取与 $B$ 位于直线 $AC$ 异侧的交点，记为 $E$。

这一步满足

$$BE=AC,\qquad BE\perp AC.$$

逆时针编号下，所选方向还满足

$$\overrightarrow{BE}=J\overrightarrow{AC},$$

其中 $J$ 为逆时针旋转 $90^\circ$。在全部合法输入中，异侧交点始终存在且唯一。[选点证明](PROOF.md#2-异侧交点存在且唯一)

## 3. 恢复四条边线

1. 连接 $D,E$，记所得直线为 $d$。
2. 过 $A$ 作 $d$ 的垂线 $a$。
3. 过 $C$ 作 $d$ 的垂线 $c$。
4. 过 $B$ 作 $d$ 的平行线 $b$。

唯一解输入保证 $D\ne E$。直线 $d$ 就是目标正方形经过 $D$ 的边线。

## 4. 取得全部顶点与边段

取四个交点

$$P=a\cap d,\qquad Q=a\cap b,$$

$$R=c\cap b,\qquad S=c\cap d.$$

所得正方形为 $PQRS$，四条边依次为

$$PQ\subset a,\qquad QR\subset b,\qquad
RS\subset c,\qquad SP\subset d.$$

给定点分别满足

$$A\in\operatorname{relint}(PQ),\quad
B\in\operatorname{relint}(QR),$$

$$C\in\operatorname{relint}(RS),\quad
D\in\operatorname{relint}(SP).$$

四个交点存在且不同，边长为正。正确性和唯一性的一般证明见 [PROOF](PROOF.md)。

## 5. 一个完整精确案例

取

$$A=(0,1),\quad B=(3,0),\quad C=(4,2),\quad D=(1,4).$$

作图取得

$$E=(2,4),\qquad d:\ y=4,$$

$$a:\ x=0,\qquad b:\ y=0,\qquad c:\ x=4.$$

因此

$$P=(0,4),\quad Q=(0,0),\quad R=(4,0),\quad S=(4,4).$$

这四条边的内部依次包含 $A,B,C,D$，目标边长为 $4$。

## 6. 辅助点的位置

辅助点 $E$ 可以落在目标 $D$ 边段的内部、目标顶点上或该边的延长部分。作图始终使用支撑直线 $DE$。给定四点的合法性继续采用严格边内部约束。

连续解族对应 $E=D$，由 [CLASSIFICATION](CLASSIFICATION.md#6-等长且垂直的对角线产生连续解族) 单独描述。本次构造覆盖全部唯一解输入，包括辅助点在目标顶点上、辅助点在边段之外及 $D,E$ 距离极小的情形。

## 7. 精确重放

[square_reconstruction.py](../experiments/square_reconstruction.py) 按上述顺序记录点、线、圆和交点，$E$ 实际由直线圆求交及异侧判断选取。重放接口为 `construct_square(coordinates)`，接收四个实代数坐标点，内部按凸包逆时针编号。

[verify_construction.py](../experiments/verify_construction.py) 核对每个动作的父对象、垂直和平行关系、圆交点、异侧选择、最终四条边的严格内部成员关系，以及四边等长与相邻垂直。运行方式见 [PROOF](PROOF.md#7-精确核验)。
