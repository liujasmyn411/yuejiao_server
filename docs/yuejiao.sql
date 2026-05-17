-- =============================================
-- 粤教服务AI Agent系统 · MySQL 完整版
-- 包含：15张表建表语句 + 真实测试数据
-- 字符集：utf8mb4  存储引擎：InnoDB
-- 版本：v2.1 · 可直接 source 执行
-- 用法：mysql -u root -p < yuejiao.sql
-- 生成日期：2026-05-16
-- =============================================

CREATE DATABASE IF NOT EXISTS yuejiao
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE yuejiao;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
-- 1. 统一用户表（学生/员工）
DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
    password_hash VARCHAR(255) NOT NULL COMMENT '加密密码',
    real_name VARCHAR(30) NOT NULL COMMENT '真实姓名',
    user_type VARCHAR(20) NOT NULL COMMENT 'ADMIN/STUDENT/EMPLOYEE',
    employee_role VARCHAR(50) DEFAULT NULL COMMENT '员工角色',
    head_teacher_id BIGINT DEFAULT NULL COMMENT '班主任ID（STUDENT必填，关联sys_user.id且该用户须为EMPLOYEE+班主任角色）',
    department VARCHAR(100) DEFAULT NULL COMMENT '部门/院系',
    contact_info VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    id_card VARCHAR(30) DEFAULT NULL COMMENT '身份证',
    avatar VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
    country_region VARCHAR(30) DEFAULT '中国' COMMENT '国家/地区',
    status VARCHAR(20) DEFAULT '正常' COMMENT '账号状态',
    last_login_time DATETIME DEFAULT NULL COMMENT '最后登录时间',
    last_login_ip VARCHAR(50) DEFAULT NULL COMMENT '最后登录IP',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除 0=正常 1=删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_user_type (user_type),
    INDEX idx_head_teacher_id (head_teacher_id),
    INDEX idx_delete_flag (delete_flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统一用户表';

-- 1. 统一用户表（学生/员工） 测试数据
-- 密码说明：
--   admin     → admin123
--   员工1~员工5  → 123456
--   学生4~学生5  → 123456
INSERT INTO sys_user (id, username, password_hash, real_name, user_type, employee_role, head_teacher_id, department, contact_info, email, id_card, avatar, country_region, status, last_login_time, last_login_ip, create_time, update_time, delete_flag, remark) VALUES
(1, 'admin', '$2b$12$HylE4rJWlR4njwnrajvl0.X6EkxZeox/qrhGpsyx3RWh75lIEMyye', '管理员', 'ADMIN', '系统管理员', NULL, '粤教服务', '13800000000', 'admin@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, '系统超级管理员'),
(2, '员工1', '$2b$12$ij87MXqaqzXrNOgkBBijsOnMABupVMW5BqEEJVhT3go9nXHAyYBQW', '张建国', 'EMPLOYEE', '班主任', NULL, '销售部', '13800000001', 'zhangjg@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(3, '员工2', '$2b$12$y9BVHTkd3gFQi8vehAPzxeTfAzTjUW4TjgYwaHekBX6BiaTsJZr6O', '李明', 'EMPLOYEE', '市场专员', NULL, '市场部', '13800000002', 'liming@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(4, '员工3', '$2b$12$KEIWSTjNz1NU.37sndIZeO3GYBK3dQzsoBG7ILdVhrHOfe/pxn/2S', '王芳', 'EMPLOYEE', '教务主管', NULL, '教务部', '13800000003', 'wangfang@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(5, '员工4', '$2b$12$5D9aZyoeY13ZcmX7XKOqqe/LJ931Q2MX5xRL/odi26amvmCgfbZn6', '王强', 'EMPLOYEE', '留学顾问', NULL, '留学服务部', '13800000004', 'wangqiang@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(6, '员工5', '$2b$12$O/mjzWSBHx68ipqjjU/x1eV9IS0BMHd0Na.ImoW54Fb3VBFKLJzL.', '陈美玲', 'EMPLOYEE', '客服专员', NULL, '客服部', '13800000005', 'chenml@yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(7, '学生4', '$2b$12$.j7ra5ccYvF9OT0cvw.r6eFBUfpCuVKGPpNw2RflCgYPtmdemSt.S', '赵小明', 'STUDENT', NULL, 2, '计算机系', '13900000004', 'zhaoxm@stu.yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL),
(8, '学生5', '$2b$12$3VbcrwaUDCr2wa.XDXMILuTgg3kPXw2q2xW0Mf6wwczqBTC.uRuG2', '钱小红', 'STUDENT', NULL, 2, '商学院', '13900000005', 'qianxh@stu.yuejiao.edu', NULL, NULL, '中国', '正常', NULL, NULL, NOW(), NOW(), 0, NULL);




-- 2.学生行政服务（请假/考务）
DROP TABLE IF EXISTS student_admin_service;
CREATE TABLE student_admin_service (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    service_type VARCHAR(30) NOT NULL COMMENT '请假/考务',
    leave_type VARCHAR(30) DEFAULT NULL COMMENT '病假/事假',
    start_time DATETIME DEFAULT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',
    reason TEXT DEFAULT NULL COMMENT '申请原因',
    status VARCHAR(20) DEFAULT '待审批' COMMENT '待审批/已通过/已驳回',
    reject_reason TEXT DEFAULT NULL COMMENT '驳回原因',
    approver_id BIGINT DEFAULT NULL COMMENT '审批人ID',
    related_academic_id BIGINT DEFAULT NULL COMMENT '关联教务ID',
    notify_status TINYINT DEFAULT 0 COMMENT '通知状态 0=未通知 1=已通知',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生行政服务表';

-- 2. 学生行政服务表（请假/考务） 测试数据
INSERT INTO student_admin_service (id, student_id, service_type, leave_type, start_time, end_time, reason, status, reject_reason, approver_id, related_academic_id, notify_status, create_time, update_time, delete_flag, remark) VALUES
(1, 4, '请假', '病假', '2026-05-10 08:00:00', '2026-05-12 18:00:00', '急性肠胃炎，需住院治疗两天', '已通过', NULL, 2, NULL, 1, '2026-05-09 09:15:00', '2026-05-09 14:30:00', 0, '已通知家长'),
(2, 5, '请假', '事假', '2026-05-15 08:00:00', '2026-05-16 18:00:00', '家中长辈八十大寿，需返乡参加', '待审批', NULL, NULL, NULL, 0, '2026-05-13 10:20:00', '2026-05-13 10:20:00', 0, '等待辅导员审批'),
(3, 6, '考务', NULL, '2026-06-20 09:00:00', '2026-06-20 11:00:00', '申请缓考《宏观经济学》，因参加雅思考试冲突', '已通过', NULL, 2, 101, 1, '2026-05-08 16:45:00', '2026-05-09 11:00:00', 0, '教务处已备案'),
(4, 4, '请假', '病假', '2026-04-20 08:00:00', '2026-04-22 18:00:00', '流感发热，体温39度，医生建议休息', '已通过', NULL, 2, NULL, 1, '2026-04-19 20:10:00', '2026-04-20 08:30:00', 0, NULL),
(5, 8, '请假', '事假', '2026-05-20 08:00:00', '2026-05-22 18:00:00', '参加广东省大学生设计大赛决赛', '待审批', NULL, NULL, NULL, 0, '2026-05-12 14:00:00', '2026-05-12 14:00:00', 0, '已附参赛邀请函'),
(6, 5, '考务', NULL, '2026-06-15 14:00:00', '2026-06-15 16:00:00', '申请补考《高等数学》，上学期期末缺考', '已驳回', '补考申请已过期，需走重修流程', 2, 102, 1, '2026-05-05 09:00:00', '2026-05-06 10:00:00', 0, '已通知学生重修安排');



-- 3.学生心理健康画像
DROP TABLE IF EXISTS student_psych_profile;
CREATE TABLE student_psych_profile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL UNIQUE COMMENT '学生ID',
    latest_emotion_tag VARCHAR(100) DEFAULT NULL COMMENT '最新情绪标签',
    emotion_score INT DEFAULT NULL COMMENT '情绪分数 0-100',
    risk_level VARCHAR(20) DEFAULT 'none' COMMENT 'high/medium/low/none',
    total_risk_count INT DEFAULT 0 COMMENT '累计预警次数',
    teacher_follow_up_status VARCHAR(20) DEFAULT '未跟进' COMMENT '老师跟进状态',
    last_interaction_time DATETIME DEFAULT NULL COMMENT '最后交互时间',
    emotion_history TEXT DEFAULT NULL COMMENT '情绪历史JSON',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生心理健康画像表';

-- 3. 学生心理健康画像表 测试数据
INSERT INTO student_psych_profile (id, student_id, latest_emotion_tag, emotion_score, risk_level, total_risk_count, teacher_follow_up_status, last_interaction_time, emotion_history, update_time, delete_flag, remark) VALUES
(1, 4, '积极开朗', 85, 'none', 0, '无需跟进', '2026-05-12 15:30:00', '[{"date":"2026-05-12","emotion":"开心","score":85}]', '2026-05-12 15:30:00', 0, '心理健康状况良好'),
(2, 5, '轻度焦虑', 62, 'low', 1, '已跟进', '2026-05-11 10:00:00', '[{"date":"2026-05-11","emotion":"焦虑","score":62}]', '2026-05-11 10:00:00', 0, '因雅思考试压力产生轻度焦虑'),
(3, 6, '情绪低落', 45, 'medium', 2, '跟进中', '2026-05-10 09:20:00', '[{"date":"2026-05-10","emotion":"低落","score":45}]', '2026-05-10 09:20:00', 0, '近期多次提及学业压力大'),
(4, 8, '稳定平和', 78, 'none', 0, '无需跟进', '2026-05-13 11:00:00', '[{"date":"2026-05-13","emotion":"平和","score":78}]', '2026-05-13 11:00:00', 0, '心理状态稳定');




-- 4.心理预警记录表
DROP TABLE IF EXISTS student_psych_alert;
CREATE TABLE student_psych_alert (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    trigger_reason TEXT NOT NULL COMMENT '触发原因',
    risk_level VARCHAR(20) NOT NULL COMMENT 'high/medium/low/none',
    alert_source VARCHAR(50) DEFAULT '聊天对话' COMMENT '预警来源',
    status VARCHAR(20) DEFAULT '未处理' COMMENT '处理状态',
    teacher_id BIGINT DEFAULT NULL COMMENT '负责老师ID',
    handle_time DATETIME DEFAULT NULL COMMENT '处理时间',
    handle_content TEXT DEFAULT NULL COMMENT '处理记录',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='心理预警记录表';

-- 4. 心理预警记录表 测试数据
INSERT INTO student_psych_alert (id, student_id, trigger_reason, risk_level, alert_source, status, teacher_id, handle_time, handle_content, create_time, delete_flag, remark) VALUES
(1, 6, '连续3次对话中出现"不想活了""活着没意思"等消极表述', 'high', '聊天对话', '处理中', 2, NULL, '已安排一对一心理辅导，预约下周二下午', '2026-05-10 09:25:00', 0, '需持续关注'),
(2, 5, '对话中频繁提及"失眠""紧张""害怕考不好"', 'medium', '聊天对话', '已处理', 2, '2026-05-11 14:00:00', '已进行心理疏导，建议调整作息，推荐放松训练', '2026-05-11 10:05:00', 0, '学生反馈有所改善'),
(3, 6, '凌晨2点发送消息"睡不着，一直在想事情"', 'medium', '聊天对话', '未处理', NULL, NULL, NULL, '2026-05-12 02:15:00', 0, '需次日跟进'),
(4, 4, '情绪波动较大，从兴奋突然转为低落', 'low', '聊天对话', '已处理', 2, '2026-05-12 16:00:00', '常规情绪疏导，建议记录情绪日记', '2026-05-12 15:35:00', 0, '偶发情绪波动');



-- 5.学生反馈工单
DROP TABLE IF EXISTS student_feedback_ticket;
CREATE TABLE student_feedback_ticket (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    feedback_type VARCHAR(30) DEFAULT NULL COMMENT '投诉/建议/咨询',
    content VARCHAR(255) NOT NULL COMMENT '反馈摘要',
    detail TEXT DEFAULT NULL COMMENT '反馈详情',
    urgency_level VARCHAR(10) DEFAULT '中' COMMENT '紧急程度',
    status VARCHAR(20) DEFAULT '待处理' COMMENT '处理状态',
    solution TEXT DEFAULT NULL COMMENT '解决方案',
    handle_user_id BIGINT DEFAULT NULL COMMENT '处理人ID',
    handle_time DATETIME DEFAULT NULL COMMENT '处理完成时间',
    is_notified TINYINT DEFAULT 0 COMMENT '是否通知学生',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生反馈工单表';

-- 5. 学生反馈工单表 测试数据
INSERT INTO student_feedback_ticket (id, student_id, feedback_type, content, detail, urgency_level, status, solution, handle_user_id, handle_time, is_notified, create_time, update_time, delete_flag, remark) VALUES
(1, 4, '建议', '建议图书馆延长周末开放时间', '目前图书馆周末下午5点就关门，对于考研和备考雅思的同学来说时间不够，建议延长至晚上9点', '中', '待处理', NULL, NULL, NULL, 0, '2026-05-08 10:30:00', '2026-05-08 10:30:00', 0, '已转交后勤处'),
(2, 5, '咨询', '咨询暑期游学项目报名流程', '想了解学校暑期英国游学项目的具体报名时间和费用，以及是否需要雅思成绩', '低', '已处理', '已发送详细项目手册至学生邮箱，报名截止6月15日', 3, '2026-05-10 16:00:00', 1, '2026-05-09 14:20:00', '2026-05-10 16:00:00', 0, '学生已确认收到'),
(3, 6, '投诉', '投诉宿舍热水供应不稳定', '宿舍楼3层最近一周晚上9点后经常没有热水，严重影响生活，请尽快维修', '高', '处理中', '已联系后勤维修部门，预计5月15日前完成检修', 1, '2026-05-13 09:00:00', 0, '2026-05-12 21:00:00', '2026-05-13 09:00:00', 0, '维修中'),
(4, 8, '建议', '建议增设设计软件培训课程', '作为设计专业学生，希望学校能开设Figma、Blender等软件的免费培训课程', '中', '待处理', NULL, NULL, NULL, 0, '2026-05-11 11:00:00', '2026-05-11 11:00:00', 0, '已转交艺术学院'),
(5, 4, '投诉', '食堂二楼饭菜质量下降', '最近食堂二楼的菜品口味明显变差，且出现过一次异物，希望加强监管', '中', '已处理', '已约谈食堂承包商，要求限期整改并加强卫生检查', 1, '2026-05-10 10:00:00', 1, '2026-05-07 12:30:00', '2026-05-10 10:00:00', 0, '学生表示满意'),
(6, 6, '咨询', '咨询转专业相关政策和流程', '目前就读国际贸易，想转到计算机专业，想了解具体要求和申请时间', '低', '已处理', '已发送转专业指南，GPA需达3.5以上，申请窗口为每学期第3-4周', 2, '2026-05-09 15:00:00', 1, '2026-05-08 09:00:00', '2026-05-09 15:00:00', 0, NULL);


-- 6.意向客户表（CRM核心）
DROP TABLE IF EXISTS crm_lead;
CREATE TABLE crm_lead (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    customer_name VARCHAR(30) NOT NULL COMMENT '客户姓名',
    contact_info VARCHAR(20) DEFAULT NULL COMMENT '电话/微信',
    age INT DEFAULT NULL COMMENT '年龄',
    education VARCHAR(50) DEFAULT NULL COMMENT '学历',
    intended_country VARCHAR(50) DEFAULT NULL COMMENT '意向国家',
    intended_major VARCHAR(100) DEFAULT NULL COMMENT '意向专业',
    family_finance VARCHAR(50) DEFAULT NULL COMMENT '家庭经济水平',
    language_level VARCHAR(50) DEFAULT NULL COMMENT '语言等级',
    background_info TEXT DEFAULT NULL COMMENT '背景信息',
    follow_up_history TEXT DEFAULT NULL COMMENT '跟进记录JSON',
    status VARCHAR(30) DEFAULT '新增意向' COMMENT '客户状态',
    source_channel VARCHAR(50) DEFAULT NULL COMMENT '获客渠道',
    next_follow_time DATETIME DEFAULT NULL COMMENT '下次跟进时间',
    score INT DEFAULT 0 COMMENT '意向评分 0-100',
    owner_employee_id BIGINT NOT NULL COMMENT '归属员工ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_employee_id (owner_employee_id),
    INDEX idx_status (status),
    INDEX idx_delete_flag (delete_flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意向客户表';

-- 6. 意向客户表（CRM核心） 测试数据
INSERT INTO crm_lead (id, customer_name, contact_info, age, education, intended_country, intended_major, family_finance, language_level, background_info, follow_up_history, status, source_channel, next_follow_time, score, owner_employee_id, create_time, update_time, delete_flag, remark) VALUES
(1, '刘浩然', '13800138002', 19, '高中在读', '英国', '计算机科学', '中产', '雅思6.0（备考中）', '对AI和机器学习方向感兴趣，参加过信息学奥赛省级二等奖', '[{"date":"2026-05-08","content":"初次电话沟通，家长陪同，意向明确"}]', '高意向', '校园开放日', '2026-05-20 10:00:00', 78, 3, '2026-05-08 14:00:00', '2026-05-12 16:30:00', 0, '家长重视就业前景'),
(2, '苏婉清', '13912345679', 18, '高中在读', '澳大利亚', '护理学', '富裕', '雅思5.5', '母亲是三甲医院护士，家庭支持留学，对澳洲移民政策有一定了解', '[{"date":"2026-05-10","content":"微信咨询，关注学费和生活费"}]', '中意向', '小红书推广', '2026-05-18 15:00:00', 65, 3, '2026-05-10 09:30:00', '2026-05-10 09:30:00', 0, '需推荐奖学金项目'),
(3, '郑文博', '13798765433', 20, '大专在读', '加拿大', '酒店管理', '中产', '暂无语言成绩', '目前就读酒店管理专科，希望专升本后去加拿大读硕士，对Co-op项目感兴趣', '[{"date":"2026-05-11","content":"到店咨询，携带成绩单"}]', '新增意向', '朋友推荐', '2026-05-25 11:00:00', 45, 7, '2026-05-11 11:00:00', '2026-05-11 11:00:00', 0, '需先解决语言成绩'),
(4, '何静怡', '13500135002', 17, '高中在读', '美国', '心理学', '富裕', '托福95', '对心理学有浓厚兴趣，曾参加暑期心理学科研项目，家庭可承担每年50万费用', '[{"date":"2026-05-09","content":"家长致电，要求推荐Top50院校"}]', '高意向', '教育展', '2026-05-16 14:00:00', 88, 3, '2026-05-09 16:00:00', '2026-05-12 10:00:00', 0, '目标院校：NYU、UCLA'),
(5, '谢天宇', '18620240004', 21, '本科在读', '德国', '机械工程', '中产', '德语B1', '本科机械工程专业，希望去德国TU9院校读研，已开始APS审核准备', '[{"date":"2026-05-12","content":"邮件咨询APS流程和院校匹配"}]', '中意向', '官网咨询', '2026-05-19 09:00:00', 72, 7, '2026-05-12 13:00:00', '2026-05-12 13:00:00', 0, 'APS审核周期较长，需提前规划'),
(6, '黄嘉欣', '13800138003', 16, '高中在读', '新加坡', '商科', '富裕', '雅思6.5', '成绩优异，年级前10%，对新加坡国立大学和南洋理工大学感兴趣', '[{"date":"2026-05-07","content":"校园宣讲会现场登记，当场提问多个专业问题"}]', '高意向', '校园宣讲', '2026-05-15 10:00:00', 85, 3, '2026-05-07 15:00:00', '2026-05-12 11:00:00', 0, '计划参加7月夏校'),
(7, '吴志强', '13912345680', 22, '本科毕业', '日本', '动漫设计', '中产', '日语N2', '本科视觉传达专业毕业，作品集已准备80%，希望明年4月入学', '[{"date":"2026-05-06","content":"微信沟通，发送作品集初稿"}]', '中意向', 'B站推广', '2026-05-21 16:00:00', 68, 7, '2026-05-06 10:00:00', '2026-05-13 09:00:00', 0, '作品集需进一步完善');


-- 7.员工日报表
DROP TABLE IF EXISTS employee_daily_report;
CREATE TABLE employee_daily_report (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    employee_id BIGINT NOT NULL COMMENT '员工ID',
    report_date DATE NOT NULL COMMENT '日报日期',
    work_type VARCHAR(50) DEFAULT NULL COMMENT '工作类型',
    content TEXT NOT NULL COMMENT '日报内容',
    summary TEXT DEFAULT NULL COMMENT 'AI自动摘要',
    report_status VARCHAR(20) DEFAULT '已提交' COMMENT '提交状态',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_employee_id (employee_id),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工日报表';

-- 7. 员工日报表 测试数据
INSERT INTO employee_daily_report (id, employee_id, report_date, work_type, content, summary, report_status, create_time, delete_flag, remark) VALUES
(1, 3, '2026-05-12', '客户接待', '今日接待意向客户3组：刘浩然（英国计算机）、何静怡（美国心理学）、黄嘉欣（新加坡商科）。刘浩然家长对就业数据很关注，已发送往届就业报告；何静怡要求推荐Top50院校，已整理NYU和UCLA申请要求；黄嘉欣计划参加夏校，已推送报名链接。', '今日完成3组高意向客户深度咨询，重点跟进刘浩然和何静怡的院校匹配方案', '已提交', '2026-05-12 18:30:00', 0, NULL),
(2, 2, '2026-05-12', '心理辅导', '今日心理辅导预约4人：赵子轩（情绪疏导，学业压力）、周思琪（人际关系咨询）、2名匿名线上咨询。赵子轩状态较上周有所改善，建议继续每周一次面谈；周思琪主要咨询宿舍矛盾，已提供沟通技巧指导。', '完成4人次心理辅导，赵子轩风险等级由medium降至low', '已提交', '2026-05-12 17:45:00', 0, '赵子轩需持续关注'),
(3, 7, '2026-05-12', '市场拓展', '今日拨打外呼电话45通，接通28通，有效沟通15通，新增意向客户2人：谢天宇（德国机械工程）、吴志强（日本动漫设计）。整理华南地区高中名单50所，筛选出重点合作学校10所。', '外呼转化率53%，新增2名中意向客户，重点学校名单已更新', '已提交', '2026-05-12 19:00:00', 0, NULL),
(4, 3, '2026-05-11', '方案制作', '为刘浩然制作英国计算机科学申请方案（含G5院校冲刺策略和保底院校清单），为何静怡整理美国心理学Top20院校对比表（含学费、录取率、课程设置）。', '完成2份高意向客户申请方案', '已提交', '2026-05-11 18:00:00', 0, NULL),
(5, 2, '2026-05-11', '危机干预', '接到赵子轩心理预警后，立即进行一对一危机干预面谈，持续2小时。评估当前风险等级为medium，已建立每周跟进机制，并通知其辅导员和家长。', '完成赵子轩危机干预，风险可控，已建立跟进机制', '已提交', '2026-05-11 20:00:00', 0, '已同步家长'),
(6, 1, '2026-05-12', '系统维护', '完成学生管理系统v2.1版本部署，修复了心理预警推送延迟问题。优化了CRM客户分配算法，提升匹配准确率15%。处理日常IT工单8件。', '系统升级完成，预警推送和CRM匹配优化上线', '已提交', '2026-05-12 18:00:00', 0, NULL);


-- 8.学生成绩表
DROP TABLE IF EXISTS student_score;
CREATE TABLE student_score (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    course_name VARCHAR(100) NOT NULL COMMENT '课程名称',
    score DECIMAL(5,2) NOT NULL COMMENT '得分',
    total_score DECIMAL(5,2) DEFAULT NULL COMMENT '总分',
    pass_score DECIMAL(5,2) DEFAULT 60 COMMENT '及格线',
    exam_type VARCHAR(30) DEFAULT NULL COMMENT '期中/期末/语言考试',
    exam_time DATETIME DEFAULT NULL COMMENT '考试时间',
    semester VARCHAR(30) DEFAULT NULL COMMENT '学期',
    teacher_id BIGINT DEFAULT NULL COMMENT '录入老师ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生成绩表';

-- 8. 学生成绩表 测试数据
INSERT INTO student_score (id, student_id, course_name, score, total_score, pass_score, exam_type, exam_time, semester, teacher_id, create_time, delete_flag, remark) VALUES
(1, 4, '高等数学（上）', 88.5, 100.0, 60.0, '期末', '2026-01-15 09:00:00', '2025-2026第一学期', 2, '2026-01-20 10:00:00', 0, NULL),
(2, 4, '大学英语', 92.0, 100.0, 60.0, '期末', '2026-01-16 14:00:00', '2025-2026第一学期', 2, '2026-01-20 10:00:00', 0, NULL),
(3, 4, 'Python程序设计', 95.5, 100.0, 60.0, '期末', '2026-01-17 09:00:00', '2025-2026第一学期', 2, '2026-01-20 10:00:00', 0, '专业第一名'),
(4, 5, '综合英语', 85.0, 100.0, 60.0, '期末', '2026-01-15 09:00:00', '2025-2026第一学期', 2, '2026-01-20 10:00:00', 0, NULL),
(5, 5, '英语听力', 78.5, 100.0, 60.0, '期末', '2026-01-16 10:00:00', '2025-2026第一学期', 2, '2026-01-20 10:00:00', 0, NULL),
(6, 5, '雅思模拟测试', 6.5, 9.0, 5.5, '语言考试', '2026-05-10 09:00:00', '2025-2026第二学期', 3, '2026-05-12 10:00:00', 0, '目标7.0，需加强写作'),
(7, 6, '宏观经济学', 72.0, 100.0, 60.0, '期中', '2026-04-20 14:00:00', '2025-2026第二学期', 2, '2026-04-25 10:00:00', 0, '缓考已通过'),
(8, 6, '国际贸易实务', 80.5, 100.0, 60.0, '期中', '2026-04-22 09:00:00', '2025-2026第二学期', 2, '2026-04-25 10:00:00', 0, NULL),
(9, 8, '设计素描', 90.0, 100.0, 60.0, '期末', '2026-01-18 09:00:00', '2025-2026第一学期', 2, '2026-01-22 10:00:00', 0, '作品入选院展'),
(10, 8, '色彩构成', 87.5, 100.0, 60.0, '期末', '2026-01-19 14:00:00', '2025-2026第一学期', 2, '2026-01-22 10:00:00', 0, NULL);




-- 9.课程项目表（留学项目）
DROP TABLE IF EXISTS course_project;
CREATE TABLE course_project (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    category VARCHAR(50) DEFAULT NULL COMMENT '项目类别',
    country VARCHAR(50) DEFAULT NULL COMMENT '所属国家',
    tuition_fee VARCHAR(100) DEFAULT NULL COMMENT '学费',
    duration VARCHAR(50) DEFAULT NULL COMMENT '学制',
    description TEXT DEFAULT NULL COMMENT '项目介绍',
    target_audience VARCHAR(255) DEFAULT NULL COMMENT '适合人群',
    age_min INT DEFAULT NULL COMMENT '最低年龄要求',
    age_max INT DEFAULT NULL COMMENT '最高年龄要求',
    application_require TEXT DEFAULT NULL COMMENT '申请要求',
    is_recommended TINYINT DEFAULT 0 COMMENT '是否推荐 0=否 1=是',
    sort_order INT DEFAULT 0 COMMENT '排序序号',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程项目表';

-- 9. 课程项目表（留学项目） 测试数据
INSERT INTO course_project (id, project_name, category, country, tuition_fee, duration, description, target_audience, age_min, age_max, application_require, is_recommended, sort_order, delete_flag, remark) VALUES
(1, '英国G5名校计算机硕士直通车', '硕士', '英国', '£35,000-£45,000/年', '1年', '针对985/211及优秀双非院校学生，提供牛津、剑桥、帝国理工、UCL、LSE计算机及相关专业硕士申请全流程服务，含文书指导、面试培训、签证办理。', '计算机、软件工程、人工智能等相关专业本科生，GPA3.5+，雅思6.5+', NULL, NULL, '本科相关专业，GPA3.5/4.0以上，雅思总分6.5（单项不低于6.0），需提交个人陈述和推荐信', 1, 1, 0, '热门项目，每年限招30人'),
(2, '澳洲八大护理学本科', '本科', '澳大利亚', 'AUD 35,000-42,000/年', '3年', '与悉尼大学、墨尔本大学、蒙纳士大学等澳洲顶尖院校合作，提供护理学本科申请服务，课程含临床实习，毕业后可申请澳洲注册护士资格。', '高中毕业生或大专在读生，对护理行业有热情，英语基础良好', NULL, NULL, '高中毕业，雅思总分7.0（单项不低于7.0）或PTE65+，需通过面试', 1, 2, 0, '移民优势专业'),
(3, '加拿大Co-op酒店管理专升硕', '专升硕', '加拿大', 'CAD 25,000-30,000/年', '2.5年', '针对大专毕业生设计的专升硕路径，前1.5年完成本科课程（含Co-op带薪实习），后1年攻读硕士学位，毕业后可申请加拿大PGWP工签。', '酒店管理、旅游管理等相关专业大专毕业生，有实习或工作经验优先', NULL, NULL, '大专毕业，GPA2.8+，雅思6.0或托福80+，需提交简历和实习证明', 0, 3, 0, '性价比高的移民路径'),
(4, '美国Top50心理学硕士', '硕士', '美国', '$45,000-65,000/年', '2年', '涵盖临床心理学、咨询心理学、工业组织心理学等方向，合作院校包括NYU、UCLA、密歇根大学等，提供GRE备考指导和科研背景提升。', '心理学、教育学、社会学等相关专业本科生，有科研或志愿者经历', NULL, NULL, '本科相关专业，GPA3.3+，GRE310+，雅思7.0或托福100+，需提交Writing Sample', 1, 4, 0, '需提前1.5年准备'),
(5, '德国TU9机械工程硕士', '硕士', '德国', '免学费（仅注册费€300/学期）', '2年', '与德国TU9联盟院校（慕尼黑工大、亚琛工大、柏林工大等）合作，德语授课为主，部分英授项目可选，提供APS审核辅导和德语培训。', '机械工程、车辆工程、自动化等相关专业本科生', NULL, NULL, '本科相关专业，APS审核通过，德语B2或雅思6.5（英授项目），需课程描述和动机信', 1, 5, 0, '免学费，性价比极高'),
(6, '新加坡国立大学商科硕士', '硕士', '新加坡', 'SGD 50,000-60,000/年', '1年', '与NUS、NTU商学院合作，提供金融、会计、市场营销等热门方向申请服务，课程紧凑，毕业后可留新就业，平均起薪高。', '商科、经济学、管理学等相关专业本科生，有GMAT/GRE成绩', NULL, NULL, '本科相关专业，GPA3.5+，GMAT650+或GRE315+，雅思7.0或托福100+，需面试', 1, 6, 0, '亚洲顶尖商学院'),
(7, '日本动漫设计本科', '本科', '日本', '¥80-120万日元/年', '4年', '与京都艺术大学、东京工艺大学、大阪艺术大学等合作，提供动漫、游戏设计、角色设计等专业申请，含日语培训和作品集辅导。', '美术、设计类高中生或同等学历，有绘画基础，热爱动漫文化', NULL, NULL, '高中毕业，日语N2或EJU日语220+，需提交作品集（8-12件），需面试', 0, 7, 0, '作品集准备周期6-12个月');



-- 10.活动讲座表
DROP TABLE IF EXISTS event_lecture;
CREATE TABLE event_lecture (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    event_name VARCHAR(100) NOT NULL COMMENT '活动名称',
    event_type VARCHAR(20) DEFAULT NULL COMMENT '线上/线下',
    speaker VARCHAR(50) DEFAULT NULL COMMENT '主讲人',
    cover_image VARCHAR(255) DEFAULT NULL COMMENT '封面图',
    start_time DATETIME NOT NULL COMMENT '活动开始时间',
    location VARCHAR(255) DEFAULT NULL COMMENT '地点/直播链接',
    registration_end_time DATETIME DEFAULT NULL COMMENT '报名截止时间',
    max_participants INT DEFAULT NULL COMMENT '最大参与人数',
    current_participants INT DEFAULT 0 COMMENT '当前报名人数',
    event_status VARCHAR(20) DEFAULT '未开始' COMMENT '活动状态',
    creator_id BIGINT DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_creator_id (creator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='活动讲座表';

-- 10. 活动讲座表 测试数据
INSERT INTO event_lecture (id, event_name, event_type, speaker, cover_image, start_time, location, registration_end_time, max_participants, current_participants, event_status, creator_id, create_time, delete_flag, remark) VALUES
(1, '2026秋季英国留学申请全攻略', '线上', '王强', 'https://cdn.yuejiao.edu/events/uk-fall-2026.jpg', '2026-05-18 19:00:00', '腾讯会议：123-456-789', '2026-05-17 18:00:00', 200, 156, '报名中', 3, '2026-05-10 10:00:00', 0, '面向计划2026年秋季入学的学生'),
(2, '雅思口语7分突破工作坊', '线下', '外教Mark Johnson', 'https://cdn.yuejiao.edu/events/ielts-speaking.jpg', '2026-05-20 14:00:00', '粤教服务中心3楼报告厅', '2026-05-19 12:00:00', 50, 42, '报名中', 3, '2026-05-08 09:00:00', 0, '小班制，限50人'),
(3, '家长专场：如何支持孩子海外留学', '线上', '李芳', 'https://cdn.yuejiao.edu/events/parents-guide.jpg', '2026-05-22 20:00:00', '微信视频号直播', '2026-05-21 20:00:00', 500, 328, '报名中', 2, '2026-05-11 14:00:00', 0, '针对留学生家长的心理建设和沟通技巧'),
(4, '德国留学APS审核经验分享会', '线下', '谢天宇（在读学员）', 'https://cdn.yuejiao.edu/events/aps-germany.jpg', '2026-05-25 15:00:00', '粤教服务中心2楼会议室', '2026-05-24 18:00:00', 30, 18, '报名中', 3, '2026-05-12 11:00:00', 0, 'APS审核亲历者分享'),
(5, 'AI时代：计算机专业留学与职业规划', '线上', '张伟', 'https://cdn.yuejiao.edu/events/ai-cs-career.jpg', '2026-05-28 19:30:00', 'B站直播间', '2026-05-27 18:00:00', 1000, 567, '报名中', 1, '2026-05-13 09:00:00', 0, '联合校友会共同举办'),
(6, '日本动漫设计专业校园开放日', '线下', '京都艺术大学招生官', 'https://cdn.yuejiao.edu/events/japan-art-open.jpg', '2026-06-05 09:00:00', '粤教服务中心1楼大厅', '2026-06-03 18:00:00', 80, 35, '报名中', 3, '2026-05-13 15:00:00', 0, '可现场提交作品集预审');



-- 11.活动报名表
DROP TABLE IF EXISTS event_registration;
CREATE TABLE event_registration (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    event_id BIGINT NOT NULL COMMENT '活动ID',
    customer_id BIGINT NOT NULL COMMENT '客户ID',
    customer_name VARCHAR(30) DEFAULT NULL COMMENT '客户姓名',
    contact VARCHAR(20) DEFAULT NULL COMMENT '联系方式',
    status VARCHAR(20) DEFAULT '已报名' COMMENT '报名状态',
    check_in_status TINYINT DEFAULT 0 COMMENT '签到状态 0=未签到 1=已签到',
    check_in_time DATETIME DEFAULT NULL COMMENT '签到时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_event_id (event_id),
    INDEX idx_customer_id (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='活动报名表';

-- 11. 活动报名表 测试数据
INSERT INTO event_registration (id, event_id, customer_id, customer_name, contact, status, check_in_status, check_in_time, create_time, delete_flag, remark) VALUES
(1, 1, 1, '刘浩然', '13800138002', '已报名', 0, NULL, '2026-05-10 11:00:00', 0, '家长将陪同观看'),
(2, 1, 4, '何静怡', '13500135002', '已报名', 0, NULL, '2026-05-11 09:30:00', 0, NULL),
(3, 1, 6, '黄嘉欣', '13800138003', '已报名', 0, NULL, '2026-05-12 10:00:00', 0, '已加入答疑群'),
(4, 2, 5, '林雨桐', '18620240002', '已报名', 1, '2026-05-20 13:45:00', '2026-05-15 16:00:00', 0, '提前15分钟到场'),
(5, 2, 4, '何静怡', '13500135002', '已报名', 0, NULL, '2026-05-18 14:00:00', 0, NULL),
(6, 3, 4, '何静怡', '13500135002', '已报名', 0, NULL, '2026-05-12 08:00:00', 0, '推荐给家长群'),
(7, 4, 3, '谢天宇', '18620240004', '已报名', 0, NULL, '2026-05-13 09:00:00', 0, '将作为分享嘉宾参与'),
(8, 5, 4, '何静怡', '13500135002', '已报名', 0, NULL, '2026-05-14 10:00:00', 0, NULL),
(9, 6, 7, '吴志强', '13912345680', '已报名', 0, NULL, '2026-05-14 11:00:00', 0, '携带作品集原件'),
(10, 6, 1, '刘浩然', '13800138002', '已报名', 0, NULL, '2026-05-14 12:00:00', 0, '对动漫设计也有兴趣');



-- =============================================
-- 12.学生教务信息表（论文DDL / 考试时间等）
-- =============================================
DROP TABLE IF EXISTS student_academic;
CREATE TABLE student_academic (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    course_name VARCHAR(100) NOT NULL COMMENT '课程名称',
    academic_type VARCHAR(30) NOT NULL COMMENT '类型：考试/论文/作业/项目',
    title VARCHAR(200) NOT NULL COMMENT '考试/作业标题',
    description TEXT DEFAULT NULL COMMENT '详细描述',
    exam_location VARCHAR(200) DEFAULT NULL COMMENT '考试地点（仅考试类）',
    deadline DATETIME NOT NULL COMMENT '考试时间/截止日期',
    duration_minutes INT DEFAULT NULL COMMENT '考试时长（分钟，仅考试类）',
    semester VARCHAR(30) DEFAULT NULL COMMENT '学期',
    ddl_status VARCHAR(20) DEFAULT '未完成' COMMENT '完成状态：未完成/已完成/已逾期',
    remind_enabled TINYINT DEFAULT 1 COMMENT '是否开启提醒 0=否 1=是',
    remind_days_before VARCHAR(30) DEFAULT '7,1' COMMENT '提前提醒天数，逗号分隔',
    last_remind_time DATETIME DEFAULT NULL COMMENT '最近一次提醒时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id),
    INDEX idx_deadline (deadline),
    INDEX idx_ddl_status (ddl_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生教务信息表';

-- 12. 学生教务信息表 测试数据
INSERT INTO student_academic (id, student_id, course_name, academic_type, title, description, exam_location, deadline, duration_minutes, semester, ddl_status, remind_enabled, remind_days_before, last_remind_time, create_time, update_time, delete_flag, remark) VALUES
(1, 4, '高等数学（下）', '考试', '高等数学（下）期末考试', '涵盖微积分、线性代数，闭卷笔试', '教学楼A301', '2026-06-20 09:00:00', 120, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-03-01 08:00:00', '2026-03-01 08:00:00', 0, '占期末总评60%'),
(2, 4, 'Python程序设计', '项目', '图书管理系统大作业', '独立完成一个带GUI的图书管理系统，含增删改查、借阅功能', NULL, '2026-06-10 23:59:00', NULL, '2025-2026第二学期', '未完成', 1, '14,3', NULL, '2026-04-15 10:00:00', '2026-04-15 10:00:00', 0, '允许组队，最多3人'),
(3, 4, '大学英语', '论文', '跨文化交际课程论文', '3000词英文论文，主题自选，格式APA，查重率<20%', NULL, '2026-06-05 23:59:00', NULL, '2025-2026第二学期', '未完成', 1, '14,3,1', '2026-05-22 09:00:00', '2026-03-20 14:00:00', '2026-05-22 09:00:00', 0, '已提醒1次'),
(4, 5, '综合英语', '考试', '综合英语期末考试', '听力+阅读+写作+翻译，闭卷', '教学楼B102', '2026-06-18 14:00:00', 150, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-03-01 08:00:00', '2026-03-01 08:00:00', 0, '占期末总评50%'),
(5, 5, '英语听力', '考试', '英语听力期末考试', '包括对话理解、讲座笔记、听写，机考', '语音室C201', '2026-06-22 10:00:00', 90, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-03-05 09:00:00', '2026-03-05 09:00:00', 0, '需携带耳机'),
(6, 5, '英美文学', '论文', '英美文学期末论文', '2000词英文论文，分析一部指定小说', NULL, '2026-06-12 23:59:00', NULL, '2025-2026第二学期', '未完成', 1, '14,3', '2026-05-29 09:00:00', '2026-03-15 11:00:00', '2026-05-29 09:00:00', 0, '已提醒1次'),
(7, 6, '宏观经济学', '考试', '宏观经济学缓考', '因与雅思考试冲突，申请缓考', '教学楼A201', '2026-06-25 09:00:00', 120, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-05-09 11:00:00', '2026-05-09 11:00:00', 0, '缓考已批准'),
(8, 6, '国际贸易实务', '项目', '国际贸易模拟谈判', '分组模拟国际贸易谈判，提交谈判记录与分析报告', NULL, '2026-06-08 18:00:00', NULL, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-04-10 09:00:00', '2026-04-10 09:00:00', 0, '4人一组'),
(9, 6, '计量经济学', '论文', '计量经济学实证论文', '运用Stata进行数据分析，撰写实证论文5000字', NULL, '2026-06-15 23:59:00', NULL, '2025-2026第二学期', '未完成', 1, '14,3,1', NULL, '2026-04-05 14:00:00', '2026-04-05 14:00:00', 0, '需提交数据和代码'),
(10, 8, '设计素描', '作业', '期末作品集提交', '提交本学期10幅素描作品电子版+纸质版', NULL, '2026-06-08 17:00:00', NULL, '2025-2026第二学期', '未完成', 1, '7,3,1', '2026-06-01 10:00:00', '2026-03-10 10:00:00', '2026-06-01 10:00:00', 0, '纸质版交至艺术学院办公室'),
(11, 8, '色彩构成', '考试', '色彩构成期末考核', '现场命题创作，水粉/水彩/丙烯任选', '美术楼D101', '2026-06-20 09:00:00', 180, '2025-2026第二学期', '未完成', 1, '7,1', NULL, '2026-03-10 10:00:00', '2026-03-10 10:00:00', 0, '自备画材'),
(12, 4, '软件工程概论', '考试', '软件工程概论期末考', '选择题+简答题+案例分析', '教学楼A303', '2026-04-15 09:00:00', 120, '2025-2026第二学期', '已完成', 1, '7,1', '2026-04-08 09:00:00', '2026-02-20 08:00:00', '2026-04-15 11:00:00', 0, '成绩已公布：88分');


-- =============================================
-- 13.留学业务进度追踪表（文书/申请/签证）
-- =============================================
DROP TABLE IF EXISTS student_study_abroad_progress;
CREATE TABLE student_study_abroad_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    student_id BIGINT NOT NULL COMMENT '学生ID',
    target_country VARCHAR(50) NOT NULL COMMENT '目标国家',
    target_school VARCHAR(200) NOT NULL COMMENT '目标院校',
    target_major VARCHAR(200) DEFAULT NULL COMMENT '目标专业',
    degree_level VARCHAR(30) DEFAULT NULL COMMENT '学位：本科/硕士/博士',
    stage VARCHAR(50) NOT NULL COMMENT '当前阶段：文书准备/文书审核/院校申请/院校反馈/录取结果/签证办理/行前准备',
    stage_order INT NOT NULL COMMENT '阶段序号 1-7',
    stage_status VARCHAR(30) DEFAULT '待开始' COMMENT '阶段状态：待开始/进行中/已完成',
    stage_detail TEXT DEFAULT NULL COMMENT '阶段详情/备注',
    handler_name VARCHAR(30) DEFAULT NULL COMMENT '负责人姓名',
    handler_contact VARCHAR(50) DEFAULT NULL COMMENT '负责人联系方式',
    estimated_complete_date DATE DEFAULT NULL COMMENT '预计完成日期',
    actual_complete_date DATE DEFAULT NULL COMMENT '实际完成日期',
    is_current TINYINT DEFAULT 0 COMMENT '是否为当前进行中阶段 0=否 1=是',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注',
    INDEX idx_student_id (student_id),
    INDEX idx_stage (stage),
    INDEX idx_is_current (is_current)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='留学业务进度追踪表';

-- 13. 留学业务进度追踪表 测试数据
INSERT INTO student_study_abroad_progress (id, student_id, target_country, target_school, target_major, degree_level, stage, stage_order, stage_status, stage_detail, handler_name, handler_contact, estimated_complete_date, actual_complete_date, is_current, create_time, update_time, delete_flag, remark) VALUES
(1, 7, '英国', '帝国理工学院', '计算机科学', '硕士', '文书准备', 1, '已完成', '个人陈述初稿已完成，推荐信已联系2位教授，简历已更新至最新版本', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-05-10', '2026-05-08', 0, '2026-04-01 10:00:00', '2026-05-08 16:00:00', 0, '文书质量较高'),
(2, 7, '英国', '帝国理工学院', '计算机科学', '硕士', '文书审核', 2, '已完成', '文书老师已完成一审，修改建议：PS需加强研究经历的描述，推荐信已确认内容无误', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-05-15', '2026-05-14', 0, '2026-05-09 09:00:00', '2026-05-14 14:00:00', 0, '二审通过'),
(3, 7, '英国', '帝国理工学院', '计算机科学', '硕士', '院校申请', 3, '进行中', '已提交帝国理工学院在线申请表，申请费已缴纳，材料完整待审核', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-05-30', NULL, 1, '2026-05-15 10:00:00', '2026-05-15 10:00:00', 0, '申请编号：ICL-2026-CS-0042'),
(4, 5, '新加坡', '新加坡国立大学', '商科', '本科', '文书准备', 1, '已完成', '个人陈述初稿完成，推荐信1封已到位（英语老师），另一封待提交（班主任）', '陈美玲', 'chenml@yuejiao.edu / 13500135001', '2026-05-20', '2026-05-18', 0, '2026-05-01 14:00:00', '2026-05-18 11:00:00', 0, '第二封推荐信需跟进'),
(5, 5, '新加坡', '新加坡国立大学', '商科', '本科', '文书审核', 2, '进行中', '文书老师已反馈初稿意见：需补充课外活动经历，突出领导力和团队协作能力', '陈美玲', 'chenml@yuejiao.edu / 13500135001', '2026-05-25', NULL, 1, '2026-05-19 09:00:00', '2026-05-19 16:00:00', 0, '修改中'),
(6, 6, '德国', '慕尼黑工业大学', '机械工程', '硕士', '文书准备', 1, '已完成', '德文简历和动机信已定稿，APS审核材料已提交至审核部', '陈美玲', 'chenml@yuejiao.edu / 13500135001', '2026-05-05', '2026-05-04', 0, '2026-03-15 10:00:00', '2026-05-04 15:00:00', 0, 'APS审核周期约3个月'),
(7, 6, '德国', '慕尼黑工业大学', '机械工程', '硕士', '文书审核', 2, '已完成', '文书终审通过，德文翻译已确认无误', '陈美玲', 'chenml@yuejiao.edu / 13500135001', '2026-05-12', '2026-05-10', 0, '2026-05-05 09:00:00', '2026-05-10 17:00:00', 0, NULL),
(8, 6, '德国', '慕尼黑工业大学', '机械工程', '硕士', '院校申请', 3, '进行中', '等待APS审核证书（预计7月中旬出结果），拿到后立即提交大学申请', '陈美玲', 'chenml@yuejiao.edu / 13500135001', '2026-07-20', NULL, 1, '2026-05-11 10:00:00', '2026-05-11 10:00:00', 0, 'APS证书是关键节点'),
(9, 8, '日本', '京都艺术大学', '视觉传达', '本科', '文书准备', 1, '进行中', '日文个人陈述初稿撰写中，作品集已整理6件（目标8-12件），还需补充2件', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-06-15', NULL, 1, '2026-05-10 14:00:00', '2026-05-13 10:00:00', 0, '作品集准备周期较长'),
(10, 4, '英国', '帝国理工学院', '计算机科学', '硕士', '院校反馈', 4, '待开始', '等待院校审核反馈，预计审核周期4-8周', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-07-15', NULL, 0, '2026-05-15 10:00:00', '2026-05-15 10:00:00', 0, '参考往届反馈周期'),
(11, 4, '英国', '帝国理工学院', '计算机科学', '硕士', '录取结果', 5, '待开始', '等待录取结果发布', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-08-15', NULL, 0, '2026-05-15 10:00:00', '2026-05-15 10:00:00', 0, NULL),
(12, 4, '英国', '帝国理工学院', '计算机科学', '硕士', '签证办理', 6, '待开始', '待收到录取通知后启动签证流程，准备资金证明、体检等材料', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-09-01', NULL, 0, '2026-05-15 10:00:00', '2026-05-15 10:00:00', 0, '英国学生签证Tier 4'),
(13, 4, '英国', '帝国理工学院', '计算机科学', '硕士', '行前准备', 7, '待开始', '机票预订、住宿安排、行前培训、换汇等', '王强', 'wangqiang@yuejiao.edu / 13798765432', '2026-09-15', NULL, 0, '2026-05-15 10:00:00', '2026-05-15 10:00:00', 0, NULL);


-- =============================================
-- 14.站内通知表
-- =============================================
DROP TABLE IF EXISTS notification;
CREATE TABLE notification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    recipient_id BIGINT NOT NULL COMMENT '接收人ID',
    title VARCHAR(100) NOT NULL COMMENT '通知标题',
    content TEXT DEFAULT NULL COMMENT '通知内容',
    notification_type VARCHAR(30) DEFAULT NULL COMMENT 'leave_approved/leave_rejected/feedback_resolved/system',
    related_id BIGINT DEFAULT NULL COMMENT '关联业务ID',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站内通知表';


-- =============================================
-- 15.组织架构表
-- =============================================
DROP TABLE IF EXISTS org_department;
CREATE TABLE org_department (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    dept_name VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id BIGINT DEFAULT 0 COMMENT '上级部门ID，0=顶级',
    dept_level SMALLINT DEFAULT 1 COMMENT '层级 1=公司 2=部门 3=小组',
    sort_order INT DEFAULT 0 COMMENT '排序序号',
    dept_desc TEXT DEFAULT NULL COMMENT '部门职能描述',
    manager_id BIGINT DEFAULT NULL COMMENT '部门负责人ID',
    contact_phone VARCHAR(20) DEFAULT NULL COMMENT '部门联系电话',
    contact_email VARCHAR(100) DEFAULT NULL COMMENT '部门邮箱',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    delete_flag TINYINT DEFAULT 0 COMMENT '软删除',
    remark TEXT DEFAULT NULL COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组织架构表';

-- 15. 组织架构表 测试数据
INSERT INTO org_department (id, dept_name, parent_id, dept_level, sort_order, dept_desc, manager_id, contact_phone, contact_email, create_time, delete_flag, remark) VALUES
(1, '粤教服务', 0, 1, 1, '广东省教育服务有限公司总部', NULL, '020-37628058', 'info@yuejiao.edu', NOW(), 0, NULL),
(2, '市场部', 1, 2, 1, '负责线上线下获客、品牌推广、渠道合作', 2, '020-37628059', 'marketing@yuejiao.edu', NOW(), 0, NULL),
(3, '销售部', 1, 2, 2, '负责意向客户跟进、签约转化、客户关系维护', 1, '020-37628060', 'sales@yuejiao.edu', NOW(), 0, NULL),
(4, '教务部', 1, 2, 3, '负责课程安排、考试管理、学籍管理、班主任工作', 3, '020-37628061', 'academic@yuejiao.edu', NOW(), 0, NULL),
(5, '留学服务部', 1, 2, 4, '负责留学规划、文书辅导、院校申请、签证服务', 4, '020-37628062', 'abroad@yuejiao.edu', NOW(), 0, NULL),
(6, '客服部', 1, 2, 5, '负责客户咨询、投诉处理、满意度回访', 5, '020-37628063', 'cs@yuejiao.edu', NOW(), 0, NULL),
(7, '线上咨询组', 2, 3, 1, '抖音/公众号/官网等线上渠道咨询转化', NULL, NULL, NULL, NOW(), 0, NULL),
(8, '线下活动组', 2, 3, 2, '线下说明会/校园讲座/展会等活动策划与执行', NULL, NULL, NULL, NOW(), 0, NULL),
(9, '新加坡项目组', 3, 3, 1, '专注新加坡留学项目的销售转化', NULL, NULL, NULL, NOW(), 0, NULL),
(10, '德国项目组', 3, 3, 2, '专注德国双元制项目的销售转化', NULL, NULL, NULL, NOW(), 0, NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================
-- 初始化完成！共创建 15 张表 + 测试数据
-- =============================================
