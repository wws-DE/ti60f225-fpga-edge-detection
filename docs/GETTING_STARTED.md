# 导入与烧录（2026-10-22）

先读 [交接文档](HANDOFF_2026-10-22.md)，从 [Release](https://github.com/William19-creator-wq/ti60f225-fpga-edge-detection/releases/tag/handoff-2026-10-22) 下载 bit、便携工程或完整项目，核对 SHA256SUMS.txt。最新候选尚待实机对比；已有细化 v1.1 回退。

1. 建议解压到短路径（例如 C:/FPGA），准备已安装且有有效许可的 Efinity **2026.1.132**。
2. 在 Efinity 使用 File → Open Project，打开 `_fpga_edge_agent/work/active/track4_v7_median_detail_001_20261022/ti60f225_oob.xml`。便携工程包中相同相对位置即为入口。不要选择旧 bridge/control 工程，也不要把 track4_board.xml 约束文件当顶层工程。
3. 核对 Ti60F225 器件和源文件完整性；最新冻结清单共 162 个构建输入。若只需下载已有 bit，无需重新综合。
4. 开发板正确供电，数据 USB 接下载/JTAG 口。Programmer 选择已识别的 `(local) Quad RS232-HS`，加载最新 `median_detail_v1_A_20261022.bit`，模式 JTAG，Device Select `1 - 0x10660a79`，时钟 10 MHz。
5. 人工点击 Program FPGA，检查成功日志及显示。JTAG 下载断电失效，当前没有验证 Flash 固化。
6. KEY3 依次检查彩色、灰度、中值、Sobel、红边；普通光照同场景对比细化 v1.1，记录细线保留、断点、噪声以及近距离表现。验收前不继续改算法。

Windows 可用 `Get-FileHash -Algorithm SHA256 -LiteralPath 'C:/FPGA/median_detail_v1_A_20261022.bit'` 核对，期望为 `c3b313e58726b96ab3fe487cb06249f7cbfe7b14707950d46772a6b4a7b59d11`。`No backend available` 是 USB 后端/驱动排查入口；曾安装匹配的 efx_libusbk_amd64_i1.inf 后恢复识别，INF 是驱动信息而非应用程序。

跨机器重建前检查工程中的路径和厂商 IP/工具依赖；构建与硬件结果需重新记录，不能沿用旧 pass 标签。
