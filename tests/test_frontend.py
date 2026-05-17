"""
前端 E2E 测试 —— 验证三大 Agent 的意图在前端页面中的覆盖情况

测试策略：
1. 启动独立的后端进程（子进程），使用独立 SQLite 数据库
2. 用 Playwright 模拟真实浏览器操作
3. 分别验证客服Agent（8意图）、企业助手（10意图）、学生助手（7意图）的前端覆盖

运行方式（需先安装 pytest-playwright 和浏览器）：
    pip install pytest-playwright
    playwright install chromium
    python -m pytest tests/test_frontend.py -v --headed  # --headed 可选，显示浏览器窗口
"""

import os
import sys
import time
import subprocess
import signal
import urllib.request
import pytest

# ═══════════════════════════════════════════════
# Playwright 使用系统 Edge 浏览器（避免下载 Chromium）
# ═══════════════════════════════════════════════

@pytest.fixture(scope="session")
def browser(browser_type_launch_args, browser_type):
    """重写默认 browser fixture，使用系统已安装的 Edge（headless）。"""
    browser = browser_type.launch(channel="msedge", headless=True, **browser_type_launch_args)
    yield browser
    browser.close()


# ═══════════════════════════════════════════════
# 全局常量
# ═══════════════════════════════════════════════
E2E_DB_PATH = "test_frontend_e2e.db"
E2E_PORT = 18765  # 使用随机高位端口，避免冲突


# ═══════════════════════════════════════════════
# Session-scoped fixture: 启动真实后端服务
# ═══════════════════════════════════════════════
@pytest.fixture(scope="session")
def e2e_server():
    """在子进程中启动 FastAPI 服务，测试结束后自动销毁。"""
    env = os.environ.copy()
    env["DB_TYPE"] = "sqlite"
    env["SQLITE_URL"] = f"sqlite:///./{E2E_DB_PATH}"
    env["API_PORT"] = str(E2E_PORT)
    # 关闭 LLM 调用（避免测试时依赖外部 API Key）
    env["OPENAI_API_KEY"] = ""

    # 先删除旧测试数据库，保证数据干净
    if os.path.exists(E2E_DB_PATH):
        os.remove(E2E_DB_PATH)

    # stdout/stderr 不设为 PIPE，避免 Windows 管道缓冲区满导致子进程阻塞
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{E2E_PORT}"

    # 轮询等待服务就绪（最多 20 秒）
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base_url}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        out, err = proc.communicate(timeout=5)
        pytest.fail(f"E2E 后端服务启动失败\nSTDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}")

    yield base_url

    # 清理
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    if os.path.exists(E2E_DB_PATH):
        os.remove(E2E_DB_PATH)


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def _login(page, server: str, username: str, password: str):
    """在浏览器中完成登录。"""
    page.goto(f"{server}/#/login")
    page.wait_for_selector("#login-form", timeout=10000)
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("button[type=submit]")
    # 等待登录成功（localStorage 中出现 token）
    page.wait_for_function("() => localStorage.getItem('access_token') !== null", timeout=10000)
    # 再等待导航到 dashboard 并完成渲染
    page.wait_for_timeout(800)
    # 等待侧边栏出现
    page.wait_for_selector("#sidebar .sidebar__nav", timeout=10000)


def _navigate(page, server: str, path: str):
    """导航到指定 hash 路由并等待内容加载。"""
    page.goto(f"{server}/#{path}")
    # 等待 "加载中..." 消失或页面内容出现
    page.wait_for_timeout(500)


def _open_chat(page):
    """打开聊天浮窗。"""
    toggle = page.locator("#chat-toggle")
    if toggle.is_visible():
        toggle.click()
    page.wait_for_selector("#chat-widget:not(.hidden)", timeout=5000)


def _send_chat(page, text: str):
    """在聊天窗口中发送一条消息。"""
    _open_chat(page)
    page.fill("#chat-input", text)
    page.click("#chat-send")
    # 等待回复出现（移除 typing）
    page.wait_for_timeout(1500)


# ═══════════════════════════════════════════════
# 一、客服 Agent（对外）— 8 种意图前端覆盖
# ═══════════════════════════════════════════════

class TestCustomerAgentIntents:
    """
    客服 Agent 意图列表：
    company_info | business_query | policy_query | project_recommend |
    event_registration | faq | profile_match | chitchat
    """

    def test_chat_widget_default_title(self, page, e2e_server):
        """未登录时，聊天窗口默认标题应为「AI 助手」。"""
        page.goto(f"{e2e_server}/#/login")
        _open_chat(page)
        title = page.locator("#chat-title").inner_text()
        assert "AI" in title, f"期望聊天标题包含「AI」，实际为：{title}"

    def test_page_projects_visible(self, page, e2e_server):
        """意图 project_recommend：前端有「课程项目」页面，可展示项目列表。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/projects")
        page.wait_for_selector("#content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "新加坡" in content or "德国" in content or "本科" in content or "暂无" in content or "加载中" in content, "课程项目页面未正确渲染"

    def test_page_events_visible(self, page, e2e_server):
        """意图 event_registration：前端有「活动讲座」页面，支持查看活动和报名。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/events")
        page.wait_for_selector("#content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "活动" in content or "讲座" in content or "分享会" in content or "暂无" in content or "加载中" in content, "活动讲座页面未正确渲染"

    def test_page_profile_match_visible(self, page, e2e_server):
        """意图 profile_match：前端有「画像研判」页面，支持输入客户信息并匹配。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/profile-match")
        page.wait_for_selector("#content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "画像研判" in content, "画像研判页面未正确渲染"
        # 验证表单字段存在
        assert page.locator("#pm-age").count() == 1
        assert page.locator("#pm-edu").count() == 1
        assert page.locator("#pm-country").count() == 1
        assert page.locator("#btn-match").count() == 1

    def test_chat_company_info(self, page, e2e_server):
        """意图 company_info：聊天组件能调用 /api/customer/chat 并返回回复。"""
        page.goto(f"{e2e_server}/#/login")
        _send_chat(page, "你们公司叫什么名字")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "客服助手未返回任何回复"

    def test_chat_business_query(self, page, e2e_server):
        """意图 business_query：聊天组件能处理业务咨询。"""
        page.goto(f"{e2e_server}/#/login")
        _send_chat(page, "新加坡项目有哪些")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "客服助手未返回业务咨询回复"

    def test_chat_policy_query(self, page, e2e_server):
        """意图 policy_query：聊天组件能处理政策查询。"""
        page.goto(f"{e2e_server}/#/login")
        _send_chat(page, "新加坡留学政策")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "客服助手未返回政策查询回复"

    def test_chat_faq(self, page, e2e_server):
        """意图 faq：聊天组件能处理常见问题。"""
        page.goto(f"{e2e_server}/#/login")
        _send_chat(page, "怎么报名")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "客服助手未返回 FAQ 回复"

    def test_chat_chitchat(self, page, e2e_server):
        """意图 chitchat：聊天组件能处理日常闲聊。"""
        page.goto(f"{e2e_server}/#/login")
        _send_chat(page, "你好")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "客服助手未返回闲聊回复"


# ═══════════════════════════════════════════════
# 二、企业智能助手（对内）— 10 种意图前端覆盖
# ═══════════════════════════════════════════════

class TestEnterpriseAgentIntents:
    """
    企业助手意图列表：
    lead_create | lead_query | lead_update | daily_report | report_query |
    data_query | company_guide | approval | dashboard | chitchat
    """

    def test_login_employee(self, page, e2e_server):
        """员工账号能正常登录并进入仪表盘。"""
        _login(page, e2e_server, "员工1", "123456")
        # 验证侧边栏存在
        assert page.locator("#sidebar").is_visible()
        # 验证仪表盘出现
        page.wait_for_selector(".dashboard", timeout=10000)

    def test_dashboard_data(self, page, e2e_server):
        """意图 dashboard：员工仪表盘展示统计卡片。"""
        _login(page, e2e_server, "员工1", "123456")
        page.wait_for_selector(".stat-card", timeout=10000)
        cards = page.locator(".stat-card").count()
        assert cards >= 4, f"员工仪表盘应至少展示 4 张统计卡片，实际只有 {cards} 张"

    def test_page_leads_visible(self, page, e2e_server):
        """意图 lead_create / lead_query / lead_update：CRM 客户管理页面存在并可操作。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/leads")
        page.wait_for_selector("#lead-table", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "客户" in content or "CRM" in content or "暂无" in content, "CRM 页面未正确渲染"
        # 验证「新增客户」按钮存在（lead_create）
        assert page.locator("#btn-add-lead").count() == 1, "缺少「新增客户」按钮"

    def test_page_reports_visible(self, page, e2e_server):
        """意图 daily_report / report_query：员工日报页面存在并可提交/查询。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/reports")
        page.wait_for_selector("#reports-table", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "日报" in content, "员工日报页面未正确渲染"
        # 验证「写日报」和「语音转日报」按钮存在
        assert page.locator("#btn-new-report").count() == 1, "缺少「写日报」按钮"
        assert page.locator("#btn-voice-report").count() == 1, "缺少「语音转日报」按钮"

    def test_chat_widget_visible(self, page, e2e_server):
        """意图 data_query：AI 对话浮窗存在（NL2SQL 功能已整合至对话窗口）。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/dashboard")
        # 验证 AI 对话浮窗按钮和组件存在
        assert page.locator("#chat-toggle").count() == 1, "缺少 AI 对话浮窗按钮"
        assert page.locator("#chat-widget").count() == 1, "缺少 AI 对话浮窗"
        # 打开对话浮窗
        page.locator("#chat-toggle").click()
        page.wait_for_selector("#chat-widget:not(.hidden)", timeout=5000)
        assert page.locator("#chat-input").count() == 1, "缺少对话输入框"
        assert page.locator("#chat-send").count() == 1, "缺少发送按钮"

    def test_page_approvals_visible(self, page, e2e_server):
        """意图 approval：审批管理页面存在。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/approvals")
        page.wait_for_selector("#content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "审批" in content or "暂无" in content or "加载中" in content, "审批管理页面未正确渲染"

    def test_page_org_chart_visible(self, page, e2e_server):
        """意图 company_guide（辅助）：组织架构页面存在。"""
        _login(page, e2e_server, "员工1", "123456")
        _navigate(page, e2e_server, "/org-chart")
        page.wait_for_selector("#content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "组织" in content or "架构" in content or "部门" in content or "暂无" in content, "组织架构页面未正确渲染"

    def test_chat_enterprise_title(self, page, e2e_server):
        """意图 chitchat / company_guide：员工登录后，聊天标题应为「企业助手」。"""
        _login(page, e2e_server, "员工1", "123456")
        _open_chat(page)
        title = page.locator("#chat-title").inner_text()
        assert "企业" in title, f"期望聊天标题包含「企业」，实际为：{title}"

    def test_chat_enterprise_message(self, page, e2e_server):
        """企业助手聊天组件能发送消息并收到回复。"""
        _login(page, e2e_server, "员工1", "123456")
        _send_chat(page, "查一下今天的日报")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "企业助手未返回任何回复"


# ═══════════════════════════════════════════════
# 三、学生智能助手（对内）— 7 种意图前端覆盖
# ═══════════════════════════════════════════════

class TestStudentAgentIntents:
    """
    学生助手意图列表：
    admin_service | psych_care | feedback | academic_query |
    progress_track | life_support | upgrade_intent
    """

    def test_login_student(self, page, e2e_server):
        """学生账号能正常登录并进入仪表盘。"""
        _login(page, e2e_server, "学生4", "123456")
        assert page.locator("#sidebar").is_visible()
        page.wait_for_selector(".dashboard", timeout=10000)

    def test_dashboard_student(self, page, e2e_server):
        """学生仪表盘展示学业概览统计卡片。"""
        _login(page, e2e_server, "学生4", "123456")
        page.wait_for_selector(".stat-card", timeout=10000)
        cards = page.locator(".stat-card").count()
        assert cards >= 4, f"学生仪表盘应至少展示 4 张统计卡片，实际只有 {cards} 张"
        content = page.locator("#content").inner_text()
        assert "DDL" in content or "留学" in content or "成绩" in content, "学生仪表盘缺少关键学业信息"

    def test_page_academic_visible(self, page, e2e_server):
        """意图 academic_query：教务 DDL 页面存在并可筛选/查看即将到期。"""
        _login(page, e2e_server, "学生4", "123456")
        _navigate(page, e2e_server, "/academic")
        page.wait_for_selector("#academic-table", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "教务" in content or "DDL" in content or "暂无" in content, "教务 DDL 页面未正确渲染"
        # 验证筛选标签和「即将到期」按钮存在
        assert page.locator("#academic-filter").count() == 1
        assert page.locator("#btn-upcoming").count() == 1

    def test_page_study_abroad_visible(self, page, e2e_server):
        """意图 progress_track：留学进度页面存在并展示 7 阶段时间线。"""
        _login(page, e2e_server, "学生4", "123456")
        _navigate(page, e2e_server, "/study-abroad")
        page.wait_for_selector("#progress-content", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "留学" in content or "进度" in content or "阶段" in content or "暂无" in content, "留学进度页面未正确渲染"
        # 验证时间线组件存在
        assert page.locator(".timeline").count() > 0 or "暂无" in content, "缺少留学进度时间线"

    def test_page_leave_visible(self, page, e2e_server):
        """意图 admin_service：请假申请页面存在并可提交。"""
        _login(page, e2e_server, "学生4", "123456")
        _navigate(page, e2e_server, "/leave")
        page.wait_for_selector("#leave-list", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "请假" in content, "请假申请页面未正确渲染"
        # 验证「提交申请」按钮存在
        assert page.locator("#btn-new-leave").count() == 1

    def test_page_feedback_visible(self, page, e2e_server):
        """意图 feedback：反馈工单页面存在并可提交。"""
        _login(page, e2e_server, "学生4", "123456")
        _navigate(page, e2e_server, "/feedback")
        page.wait_for_selector("#feedback-list", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "反馈" in content or "工单" in content, "反馈工单页面未正确渲染"
        assert page.locator("#btn-new-feedback").count() == 1

    def test_page_psych_alert_visible(self, page, e2e_server):
        """意图 psych_care：心理预警页面存在并可筛选/新增。"""
        _login(page, e2e_server, "学生4", "123456")
        _navigate(page, e2e_server, "/psych-alert")
        page.wait_for_selector("#alert-table", timeout=10000)
        content = page.locator("#content").inner_text()
        assert "心理" in content or "预警" in content, "心理预警页面未正确渲染"
        # 验证筛选标签存在
        assert page.locator("#alert-filter-tabs").count() == 1

    def test_chat_student_title(self, page, e2e_server):
        """意图 life_support / upgrade_intent / psych_care：学生登录后，聊天标题应为「学生助手」。"""
        _login(page, e2e_server, "学生4", "123456")
        _open_chat(page)
        title = page.locator("#chat-title").inner_text()
        assert "学生" in title, f"期望聊天标题包含「学生」，实际为：{title}"

    def test_chat_student_message(self, page, e2e_server):
        """学生助手聊天组件能发送消息并收到回复。"""
        _login(page, e2e_server, "学生4", "123456")
        _send_chat(page, "我最近压力很大")
        messages = page.locator(".chat-msg--assistant").all_inner_texts()
        assert len(messages) > 0, "学生助手未返回任何回复"


# ═══════════════════════════════════════════════
# 四、通用前端回归
# ═══════════════════════════════════════════════

class TestFrontendRegression:
    """前端通用回归测试，覆盖路由、布局、组件等基础能力。"""

    def test_login_page_render(self, page, e2e_server):
        """登录页正确渲染表单和提示。"""
        page.goto(f"{e2e_server}/#/login")
        page.wait_for_selector("#login-form", timeout=10000)
        assert page.locator("#login-username").count() == 1
        assert page.locator("#login-password").count() == 1
        content = page.locator("#content").inner_text()
        assert "粤教服务" in content
        assert "admin" in content or "员工" in content or "学生" in content, "登录页缺少测试账号提示"

    def test_logout_redirect(self, page, e2e_server):
        """退出登录后正确回到登录页。"""
        _login(page, e2e_server, "员工1", "123456")
        page.click("text=退出登录")
        page.wait_for_selector("#login-form", timeout=10000)
        assert "#/login" in page.url or page.locator("#login-form").count() == 1

    def test_sidebar_role_filter(self, page, e2e_server):
        """侧边栏按角色过滤菜单：员工看不到学生专属菜单，反之亦然。"""
        # 员工登录
        _login(page, e2e_server, "员工1", "123456")
        sidebar_text = page.locator("#sidebar").inner_text()
        assert "CRM客户" in sidebar_text
        assert "教务DDL" not in sidebar_text, "员工不应看到「教务DDL」菜单"
        # 学生登录
        _login(page, e2e_server, "学生4", "123456")
        sidebar_text = page.locator("#sidebar").inner_text()
        assert "教务DDL" in sidebar_text
        assert "CRM客户" not in sidebar_text, "学生不应看到「CRM客户」菜单"

    def test_404_fallback_to_index(self, page, e2e_server):
        """前端路由回退：访问不存在的路径应返回 index.html（SPA 行为）。"""
        page.goto(f"{e2e_server}/nonexistent-path")
        # 应能加载到 app.js 挂载的 DOM 结构
        assert page.locator("#app").count() == 1

    def test_chat_minimize_close(self, page, e2e_server):
        """聊天窗口的最小化和关闭按钮正常工作。"""
        page.goto(f"{e2e_server}/#/login")
        _open_chat(page)
        # 最小化
        page.click("#chat-minimize")
        assert page.locator("#chat-widget").evaluate("el => el.classList.contains('chat-widget--minimized')")
        # 再次点击恢复
        page.click("#chat-minimize")
        assert not page.locator("#chat-widget").evaluate("el => el.classList.contains('chat-widget--minimized')")
        # 关闭
        page.click("#chat-close")
        assert page.locator("#chat-widget.hidden").count() == 1
        assert page.locator("#chat-toggle").is_visible()
