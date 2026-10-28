# 超星学习通自动化 Web 前端技术规范与接口文档

## 概述与设计理念

超星学习通 Web 控制台作为本地桌面辅助界面的轻量化实现，核心目标在于脱离沉重的 Node 编译链工具，以标准原生的现代 Web 标准构建高响应、高可用且直观易用的运维大屏。

界面整体遵循深色工业工程运维调性，以视口充满、双栏独立滚动通道、平滑无缝过渡、实时事件流驱动为基石。在满足多账号隔离管理、课程可视挑选、动态并发监控的同时，深度适配章节测验手动答题流程与全量参数可视化配置。

## 前端源码分层结构

前端源码完全剥离独立存放，位于根目录下的 web 目录中：

```
web/
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        ├── api.js
        └── app.js
```

### 结构层

web/templates/index.html 文件定义语义化文档骨架。页面划分为顶部系统导航栏与主体双列工作区，外加模态弹窗挂载层与右下角全局通知浮层容器。

### 表现层

web/static/css/style.css 集中声明 CSS 自定义属性变量，划分背景阶梯灰度、边框对比度、主题色与语义状态色。建立双列等高自适应流体布局，各子容器设置独立的纵向自定义滚动条样式，定义模态弹窗淡入缩放动效与自右向左滑动堆叠的通知队列动画。

### 交互与通信层

web/static/js/api.js 封装基于 fetch 的 RESTful 请求适配器与 SSE 长连接事件监听，统一处理 HTTP 状态码转换与接口异常捕获。

web/static/js/app.js 负责 DOM 节点缓存、视图状态响应式同步、多账号下拉切换、课程列表勾选联动、倍速滑动节流下发、工作线程动态卡片增删、实时日志置底滚动、手动答题弹窗调度与全量设置表单双向绑定。

## 布局与微交互规范

### 视口高度与双栏独立滚动

全局高度固定为窗口可视高度，溢出隐藏。主体工作区分为左侧课程选课区与右侧实时大屏监控区。

左栏与右栏设置独立的内容纵向溢出滚动，两栏滚动互不影响，用户在右侧观察日志或线程进度的同时可自由在左侧浏览长篇课程列表。

### 等宽数字排版

所有涉及任务完成百分比、章节编号、时间戳、已播放秒数、总秒数以及日志行号的文本，均应用等宽字体系统，并配置表格数字等宽排版特性，消除数值跳动导致的界面横向抖动。

### 智能朝向微型倍速弹窗

工作线程卡片上的倍速调节按钮采用自适应悬浮弹窗。在点击展开时，脚本根据触发按钮相对于视口顶部的物理距离动态计算弹出方向。当顶部剩余空间不足时，自动切换为向下弹出，规避视口截断问题。

### 队列堆叠通知动效

全局通知容器挂载于屏幕右下角。新通知以平滑动效从屏幕右侧边缘滑入，旧通知平滑上移让出空间。通知保持时间到达后，淡出并向右滑出视口，自动释放 DOM 节点。

## 手动答题模式 Web 交互机制

### 流程交互时序

章节测验任务点在执行过程中，若题库未搜到答案且回退至手动输入，或首选项即配置为手动题库时，后端工作线程向状态总线注册答题会话，并将线程挂起进入等待状态。

前端通过持久化事件流监听接收到作答事件广播，立即唤起手动答题模态窗口。

答题窗口展示当前作答的课程名称、章节标题、题目类型、题干内容及结构化选项。用户作答完成后点击提交，前端将答案通过异步接口回传给后端，工作线程被唤醒并继续后续章节处理。

若用户未找到正确答案或放弃该题，可点击跳过按钮，后台将以空答案继续执行后续流程。

### 题型适配形态

单选题：展示单选按钮列表，支持点击选项文本整行选中。

多选题：展示复选框列表，支持选择多个选项字母或内容，自动拼接为标准答案格式。

判断题：提供醒目的正确与错误两枚快捷卡片按钮，单次点击即完成选项选定。

填空题与主观题：提供文本输入框，支持直接输入文字内容。

批量模式支持：窗口右上角提供模式切换开关，用户可自由切换为多行文本框批量输入，配合自定义分隔符快速提交整套测验。

## 全量可视化设置中心规范

设置中心通过顶栏设置入口触发，以模态对话框形态集中管理程序的所有配置字段，并以选项卡分类组织。

### 基础运行配置

并发章节数量：控制后台同时执行的章节工作线程并发上限。

关闭任务点处理动作：遇到未开启或已关闭的任务章节时的策略，支持重试与继续。

失败重试等待间隔：任务遇到网络异常或未开放章节时的重试休眠秒数。

章节测验自动重做开关：开启后在章节检测提交得分不达标时自动重做。

测验最大重做轮次：自动重做的最大尝试次数上限。

增加章节学习次数开关与目标总次数：是否在完成课程后循环访问章节以刷取学习频次。

### 题库通用与提交配置

题库提供方排序与组合：可配置单个或多个题库回退顺序。

是否提交答题：控制测验是直接提交答案还是仅保存搜题结果供手动核验。

最低题库覆盖率：自动提交答题时搜题命中率需达到的最低浮点阈值。

题目搜索请求间隔：连续搜题时的延迟秒数，避免触发远端题库流控。

大模型连接连通性测试：程序启动时是否主动发起模型端点连通性测试。

### 扩展与 AI 题库配置

言溪题库配置：配置接口凭证 Tokens 序列。

LIKE 知识库配置：配置调用凭证、模型名称、是否开启联网搜索与视觉识别能力、最大重试次数。

TikuAdapter 适配器配置：配置自建或第三方题库适配器服务端接口地址。

GO 题库配置：配置公众号解除限流凭证、最小请求间隔、重试次数与退避指数。

自定义大模型配置：支持兼容 OpenAI 协议的自定义服务地址、API 密钥、模型标识、最小请求间隔与网络代理地址。

硅基流动专属配置：配置硅基流动接口密钥、预设模型标识及自定义接入点。

### 手动答题与通知配置

手动模式默认流程：配置单题逐步交互或批量一次性录入。

批量模式分隔符：配置分隔答案所使用的符号，如分号、逗号、空格或换行符。

判断题判定表：自定义匹配为正确与错误的关键词列表。

通知推送渠道配置：选择使用的推送平台，如 Server酱、Qmsg酱、Bark 或 Telegram。

通知接收地址与参数：配置推送 Webhook 完整地址及 Telegram 目标会话标识。

### 配置存储机制

在多账号模式下，设置界面的读取与保存严格作用于当前选中的账号独立 INI 配置文件，确保不同账号间的凭证、题库选择及并发配置彼此隔离互不干扰。

## 接口通信全量参考

### 账号体系接口

获取账号列表

请求方式：GET /api/accounts

返回格式：
```json
{
  "accounts": [
    {
      "id": "13800000000",
      "username": "13800000000",
      "file": "13800000000.ini",
      "active": true
    }
  ],
  "active_account": "13800000000"
}
```

切换当前活动账号

请求方式：POST /api/accounts/switch

请求参数：
```json
{
  "account_id": "13800000000"
}
```

返回格式：
```json
{
  "status": "success",
  "active_account": "13800000000"
}
```

### 认证体系接口

生成扫码登录会话

请求方式：POST /api/auth/qr/create

返回格式：
```json
{
  "session_id": "uuid-string",
  "qr_image": "data:image/png;base64,..."
}
```

轮询扫码登录状态

请求方式：GET /api/auth/qr/status/<session_id>

返回格式：
```json
{
  "status": "PENDING"
}
```
状态取值包括 PENDING 待扫描、CONFIRMED 已扫码待确认、SUCCESS 登录成功、EXPIRED 二维码过期失效。

密码直接认证

请求方式：POST /api/auth/login

请求参数：
```json
{
  "username": "13800000000",
  "password": "mypassword"
}
```

返回格式：
```json
{
  "status": "success",
  "account_id": "13800000000"
}
```

### 课程管理接口

获取课程列表

请求方式：GET /api/courses

返回格式：
```json
{
  "courses": [
    {
      "courseId": "205938120",
      "clazzId": "58392014",
      "cpi": "18293041",
      "title": "计算机网络",
      "teacher": "张教授",
      "progress": 68,
      "selected": true
    }
  ]
}
```

保存所选课程列表

请求方式：POST /api/config/course_list

请求参数：
```json
{
  "course_list": ["205938120", "205938121"]
}
```

返回格式：
```json
{
  "status": "success"
}
```

### 运行与倍速控制接口

更新全局播放倍速

请求方式：POST /api/speed/global

请求参数：
```json
{
  "speed": 1.5
}
```

返回格式：
```json
{
  "status": "success",
  "global_speed": 1.5
}
```

更新指定线程播放倍速

请求方式：POST /api/speed/worker

请求参数：
```json
{
  "worker_id": "worker_1",
  "speed": 2.0
}
```

返回格式：
```json
{
  "status": "success",
  "worker_id": "worker_1",
  "speed": 2.0
}
```

任务启停控制

请求方式：POST /api/task/start 与 POST /api/task/stop

返回格式：
```json
{
  "status": "success"
}
```

### 手动答题接口

获取待作答题目列表

请求方式：GET /api/manual/pending

返回格式：
```json
{
  "questions": [
    {
      "prompt_id": "prompt-uuid",
      "course_title": "高等数学",
      "chapter_title": "微分方程的概念",
      "type": "single",
      "title": "下列属于一阶微分方程的是？",
      "options": ["A. y' + y = 0", "B. y'' = 0", "C. x + y = 1", "D. y = x^2"],
      "created_at": 1729839200
    }
  ]
}
```

提交单题或批量答案

请求方式：POST /api/manual/answer

请求参数：
```json
{
  "prompt_id": "prompt-uuid",
  "answer": "A"
}
```

返回格式：
```json
{
  "status": "success"
}
```

跳过当前题目

请求方式：POST /api/manual/skip

请求参数：
```json
{
  "prompt_id": "prompt-uuid"
}
```

返回格式：
```json
{
  "status": "success"
}
```

### 全量配置读写接口

获取当前完整配置字典

请求方式：GET /api/config/full

返回格式：
```json
{
  "common": {
    "jobs": 4,
    "speed": 1.0,
    "notopen_action": "retry",
    "retry_interval": 1.0,
    "work_redo_enabled": false,
    "work_max_retries": 3,
    "add_learning_count": false,
    "target_count": 100
  },
  "tiku": {
    "provider": "TikuYanxi",
    "submit": false,
    "cover_rate": 0.9,
    "delay": 1.0,
    "check_llm_connection": true,
    "tokens": "",
    "likeapi_search": false,
    "likeapi_vision": true,
    "likeapi_model": "glm-4.5-air",
    "likeapi_retry": true,
    "likeapi_retry_times": 3,
    "url": "",
    "go_authorization": "",
    "go_min_interval": 1.0,
    "go_retry_times": 3,
    "go_retry_backoff": 1.2,
    "endpoint": "",
    "key": "",
    "model": "",
    "min_interval_seconds": 3,
    "http_proxy": "",
    "siliconflow_key": "",
    "siliconflow_model": "deepseek-ai/DeepSeek-R1",
    "siliconflow_endpoint": "https://api.siliconflow.cn/v1/chat/completions",
    "manual_mode_default": "batch",
    "manual_mode_separator": ";",
    "true_list": "正确,对,√,是",
    "false_list": "错误,错,×,否,不对,不正确"
  },
  "notification": {
    "provider": "ServerChan",
    "url": "",
    "tg_chat_id": ""
  }
}
```

更新完整配置

请求方式：POST /api/config/full

请求参数：包含 common、tiku、notification 结构体的数据对象

返回格式：
```json
{
  "status": "success"
}
```

### SSE 实时事件流规格

客户端通过建立向 GET /api/events 的 EventSource 长连接接收服务端主动推送。

事件格式遵循标准 text/event-stream 编码：

```
event: STATUS_UPDATE
data: {"overall_progress": 45.2, "completed_jobs": 18, "total_jobs": 40, "passed_tests": 5, "elapsed_seconds": 320, "workers": [{"id": "worker_1", "status": "PLAYING", "chapter": "1.2 极限存在准则", "speed": 1.5, "position": 124, "duration": 480}]}

event: LOG_APPEND
data: {"timestamp": "20:30:15", "level": "INFO", "message": "任务点 1.2 视频播放完成，正在回传进度"}

event: SPEED_CHANGE
data: {"type": "GLOBAL", "speed": 1.5}

event: MANUAL_QUESTION_REQUEST
data: {"prompt_id": "prompt-uuid", "course": "计算机网络", "chapter": "3.1 数据链路层概述", "type": "single", "title": "以太网帧的目的地址长度为？", "options": ["A. 48位", "B. 32位", "C. 64位", "D. 128位"]}

event: MANUAL_QUESTION_RESOLVED
data: {"prompt_id": "prompt-uuid", "status": "ANSWERED"}
```
