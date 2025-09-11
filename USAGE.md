# 0. 初始化项目 (一次性设置)
chatcoder init

# 1. 启动新特性 (流程起点)
#    - 生成 feature_id
#    - 创建第一个工作流实例 (e.g., analyze phase task)
chatcoder feature start -d "实现用户登录功能" [-w workflow_name]

# 2. 生成提示词 (针对特性当前的活动任务)
#    - 获取特性当前阶段的活动任务 ID (由 chatflow 根据 feature_id 查找)
#    - 调用服务生成并渲染提示词
chatcoder task prompt <feature_id>

# 3. 确认任务并推进 (流程核心驱动)
#    - 标记特性当前阶段的活动任务为完成 (confirmed/completed)
#    - 调用 chatflow 推进工作流，可能自动创建下一个任务实例
#    - 输出下一个任务的信息或提示流程结束
chatcoder task confirm <feature_id>

# 4. 查询状态 (监控流程)
# 4.1 查看所有特性概览
chatcoder feature list
# 4.2 查看单个特性的详细状态和任务列表
chatcoder feature status <feature_id>

# 5. 辅助命令
# 5.1 列出可用的工作流模板
chatcoder workflow list
# 5.2 (可选) 预览特定阶段为特定特性生成的提示词 (调试用)
#     phase_name 指定要预览的阶段，即使它不是当前阶段
chatcoder task preview <phase_name> <feature_id>
# 5.3 (可选) 查看项目上下文快照 (调试用)
# chatcoder context
# 5.4 (可选) 验证项目配置
# chatcoder validate
