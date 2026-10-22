# 仓库与完整归档（2026-10-22）

当前说明见 [交接](HANDOFF_2026-10-22.md)。源码仓库供浏览和版本管理，大型二进制与完整快照通过 [Release](https://github.com/William19-creator-wq/ti60f225-fpga-edge-detection/releases/tag/handoff-2026-10-22) 分发。

| 位置/附件 | 内容 |
|---|---|
| README、docs/HANDOFF_2026-10-22.md | 当前状态、烧录、问题、优化与验收路线 |
| _fpga_edge_agent/work/active | 独立历史工程、最新五全屏保边中值工程和回退工程 |
| reports / planning / observations / runtime | 设计、批准引用、失败/成功报告、照片和本地审计 |
| 三个独立 .bit 附件 | 保边中值 A、细化 v1.1、v4.1，哈希见 burn-files.json |
| FPGA-current-project-20261022.zip | 便携最新工程（包含冻结 162 输入和必要工程附件）、最新报告、三版 bit、交接文档；省略可再生成的仿真缓存 |
| FPGA-project-full-20261022.zip | 当前项目、历次副本、编译/仿真输入结果、报告与观察的完整内容快照；原厂大目录/原始包分在下面两个附件 |
| FPGA-vendor-expanded-20261022.zip | 本地原厂资料展开目录，目录名和内容保留 |
| FPGA-vendor-original-20261022.zip | 本地原厂原始 zip 的逐字节副本 |
| project-files.csv / archive-policy.json / SHA256SUMS.txt | 全快照逐文件 SHA256、明确排除项、附件校验和 |

完整归档的三个大附件合在一起恢复本地项目内容；原始 zip 按 archive-policy.json 中的 original_vendor_zip 路径放回。Git 仓库不重复纳入原厂安装包、bit、大型仿真向量/波形、生成缓存或网表；原有历史已跟踪文件保持历史，新文件选择在 repository-selection.json 逐项记录。完整归档仍保存这些构建与测试证据。

分发排除 `.git`、本次 publish 输出、个人凭据/许可及 Office 临时锁文件；源码版权/原厂保护 IP 保持原有声明，不附加统一开源许可。历史文档中的个人机器绝对路径仅作原记录，当前入口均使用项目内相对路径。

仅下载 GitHub 自动生成的 Source code.zip 不包含 Release 大附件；需要完整项目请下载本次 Release 所列文件。发布记录中的远端校验结果用于判断是否真正上传，不能仅凭本地链接判定发布完成。
