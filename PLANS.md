# PLANS

## 当前任务：金融投资研究智能体技术方案

- [x] 澄清真实需求与目标
- [x] 明确 MVP：主动型投资研究助理，优先投资机会筛选
- [x] 明确交互形态：Dashboard 优先，Chat 辅助追问
- [x] 明确技术方案深度：数据库 schema、API、页面、任务调度、Agent 工作流、评分因子、验证方案、迭代路线
- [x] 核验免费公开数据源候选
- [x] 撰写技术方案文档
- [x] 最终检查文档完整性

## 后续建议任务

- [x] 进行数据源验证 spike
- [x] 搭建 Python/FastAPI 项目骨架
- [x] 实现小 universe 的行情数据采集
- [x] 实现 MVP 因子计算与候选筛选
- [x] 实现后端内置 Dashboard 第一版
- [x] 将筛选结果持久化为正式 screening_runs / candidates 表
- [x] 实现 Dashboard 自动加载最近一次筛选结果
- [ ] 接入真实 2 卡 4090 本地 LLM API 并验证研究解释质量
- [x] 完善服务器从零使用 README
- [x] 增加环境变量模板

## Phase 0：数据源验证 spike

- [x] 创建候选 universe 配置
- [x] 实现 Yahoo chart prices 连通性与字段验证
- [x] 实现 SEC companyfacts 连通性与字段验证
- [x] 实现 Nasdaq stock RSS 连通性与字段验证
- [x] 保存原始快照
- [x] 建立本地 SQLite 验证表
- [x] 生成数据源验证报告
- [x] 增加离线单元测试

## Phase 1：MVP 骨架与首版筛选闭环

- [x] 创建 FastAPI 后端入口
- [x] 创建 FastAPI 内置静态 Dashboard
- [x] 将 spike 数据源升级为正式 connector 雏形
- [x] 实现 Momentum、Volume/Attention、Event/Catalyst、Quality 覆盖度因子
- [x] 实现 Top N 候选生成
- [x] 实现本地 LLM API 研究解释接口配置
- [x] 实现 LLM 不可用时的规则解释降级
- [x] 实现正式 SQLite repository
- [x] 实现 latest screening API
- [x] 实现 candidate chat API
- [x] 实现内置 Dashboard Chat 面板
- [x] 增加核心筛选测试
- [x] 增加服务器部署与使用说明
- [x] 移除 Node/npm/Vite 前端依赖
