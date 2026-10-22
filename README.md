# Ti60F225 FPGA 实时图像边缘检测

**当前冻结日期：2026-10-22。最新是“保边中值 v1 A”待上板候选，尚未通过实机验收。**

Ti60F225 DemoBoard V4 + SC431HAI（J4）+ DDR3 + HDMI。Efinity **2026.1.132**。KEY3 按顺序切换五种全屏实时画面：彩色 → 灰度 → 中值 → Sobel → 红边叠加；长按一次只切换一次。当前入口已从早期五分区/七模式候选更新为五全屏工程。

- **[完整交接文档](docs/HANDOFF_2026-10-22.md)**：状态、已知问题、最新 bit、验证边界和优化顺序。
- [当前状态](docs/CURRENT_STATUS.md) · [导入与烧录](docs/GETTING_STARTED.md) · [未解决问题](docs/OPEN_ISSUES.md) · [内容与归档](docs/REPOSITORY_CONTENTS.md)
- **[最新 Efinity 工程](_fpga_edge_agent/work/active/track4_v7_median_detail_001_20261022/ti60f225_oob.xml)**
- **[本次下载与完整归档](https://github.com/William19-creator-wq/ti60f225-fpga-edge-detection/releases/tag/handoff-2026-10-22)**：最新 `median_detail_v1_A_20261022.bit`，回退 `edge_thin_v1_1_20261022.bit`，更早 `v7_lowlight_edge_004_v4_1_20261021.bit`。链接在发布成功后可用。

用户反馈细化 v1.1 比前版更精细，但普通光照弱边漏检、断点和近距离中值丢细节仍存在。最新保边中值 A 尝试恢复窄线：软件仿真与构建已完成，用户接受可能少量增噪后上板对比；不能据此宣称低光问题已解决。详见 [质量取舍](_fpga_edge_agent/reports/TRACK4-V7-MEDIAN-DETAIL-001/accepted-noise-tradeoff.md) 和 [bit 哈希登记](_fpga_edge_agent/reports/PROJECT-HANDOFF-20261022/burn-files.json)。

本轮按用户要求暂停继续调参并交接。历史报告/失败案例保留；10 月 19 日及更早文档仅作为历史记录。HDMI 60 Hz 不等于相机采集 60 FPS；最新 bit 的实际帧率和图像质量仍需实测。当前实时链不等于完整 Canny 或形状识别系统。

原厂 HDK、保护 IP、资料与本项目代码分别遵从原有权利声明，见 [第三方说明](docs/THIRD_PARTY.md)。不包含个人工具许可、账号凭据和 Git 本地工作数据库。
