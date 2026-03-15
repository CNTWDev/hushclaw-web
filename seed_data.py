"""Seed the database with sample categories and skills."""
import os
import sys
from datetime import datetime, timedelta
import random

# Ensure the app directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine, SessionLocal, Base
from app.models import Category, Skill, Rating

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data
db.query(Rating).delete()
db.query(Skill).delete()
db.query(Category).delete()
db.commit()

# ── Categories ────────────────────────────────────────────────────────────────
categories_data = [
    ("职场办公", "office-work", "💼"),
    ("个人生活", "personal-life", "🏠"),
    ("信息采集", "data-collection", "📡"),
    ("表单自动化", "form-automation", "📝"),
    ("电商监控", "ecommerce", "🛍️"),
    ("政务民生", "government", "🏛️"),
]

cats = {}
for name, slug, icon in categories_data:
    cat = Category(name=name, slug=slug, icon=icon)
    db.add(cat)
    db.flush()
    cats[slug] = cat

db.commit()

# ── Skills ────────────────────────────────────────────────────────────────────
skills_data = [
    # 职场办公
    {
        "title": "自动整理邮件收件箱",
        "short_desc": "AI 自动读取邮件，按主题分类归档，标记重要邮件，一键清理垃圾邮件",
        "description": "该技能连接到你的网页邮箱（支持 Gmail、163、QQ邮箱），自动扫描近 30 天邮件：\n\n• 按发件人 / 主题聚类归档\n• 对含关键词（如「合同」「发票」）的邮件打星标\n• 将超过 90 天未读邮件移入归档\n• 生成每日邮件摘要报告\n\n注意：需在浏览器已登录邮箱账号的状态下运行。",
        "category": "office-work",
        "platform": "all",
        "install_count": 3420,
        "rating_sum": 210,
        "rating_count": 48,
        "author": "Hushclaw Team",
        "tags": "邮件, 办公, 自动化, Gmail",
    },
    {
        "title": "一键生成会议纪要",
        "short_desc": "打开腾讯会议/飞书会议网页版，AI 自动转录并生成结构化纪要",
        "description": "在腾讯会议或飞书会议结束后：\n\n• 自动抓取会议录音/转录文本\n• 提炼关键决策、行动项、负责人、截止日期\n• 生成 Markdown 格式纪要，支持一键复制\n• 可选自动发送至参会人邮箱\n\n支持中英文混合会议内容。",
        "category": "office-work",
        "platform": "all",
        "install_count": 2890,
        "rating_sum": 185,
        "rating_count": 41,
        "author": "张明",
        "tags": "会议, 纪要, 办公, 飞书",
    },
    {
        "title": "自动填写差旅报销单",
        "short_desc": "识别上传的票据图片，自动填写企业报销系统表单",
        "description": "上传出差票据照片后：\n\n• OCR 识别火车票、机票、出租车发票等\n• 自动提取金额、日期、出发/目的地\n• 按照公司报销模板逐字段填写\n• 自动上传原始票据图片\n• 生成报销汇总 Excel\n\n支持钉钉、企业微信等主流报销系统。",
        "category": "office-work",
        "platform": "all",
        "install_count": 1560,
        "rating_sum": 95,
        "rating_count": 22,
        "author": "李华",
        "tags": "报销, 财务, 自动化",
    },

    # 个人生活
    {
        "title": "每日新闻摘要推送",
        "short_desc": "每天自动抓取指定新闻源，AI 提炼摘要，汇总为每日简报",
        "description": "自定义你关心的新闻来源（支持任意网站），每天定时：\n\n• 抓取最新文章标题和正文\n• AI 提炼 3-5 句核心摘要\n• 按科技 / 财经 / 社会等分类整理\n• 输出到指定页面或复制到剪贴板\n\n可配置感兴趣的关键词做精准过滤。",
        "category": "personal-life",
        "platform": "all",
        "install_count": 4100,
        "rating_sum": 280,
        "rating_count": 62,
        "author": "Hushclaw Team",
        "tags": "新闻, 阅读, 效率",
    },
    {
        "title": "自动记录健身数据",
        "short_desc": "从运动 APP 网页版抓取训练数据，自动同步到个人健身日记",
        "description": "连接 Keep / Nike Run Club 网页版：\n\n• 每次运动后自动获取距离、时长、心率数据\n• 计算本周 / 本月累计运动量\n• 自动填写到你的 Notion / Airtable 健身记录表\n• 根据数据生成训练建议\n\n支持跑步、骑行、游泳等多种运动类型。",
        "category": "personal-life",
        "platform": "all",
        "install_count": 980,
        "rating_sum": 72,
        "rating_count": 18,
        "author": "王芳",
        "tags": "健身, 健康, Keep",
    },

    # 信息采集
    {
        "title": "竞品价格监控",
        "short_desc": "定时爬取竞品网站商品价格，发现变动自动记录并提醒",
        "description": "配置目标网站 URL 和商品选择器后：\n\n• 每小时/每天定时采集价格\n• 对比历史数据，标记涨跌幅\n• 价格变动超过阈值时弹出桌面通知\n• 数据导出到 CSV / Google Sheet\n\n支持淘宝、京东、亚马逊等主流电商，也可自定义任意网站。",
        "category": "data-collection",
        "platform": "all",
        "install_count": 2300,
        "rating_sum": 150,
        "rating_count": 35,
        "author": "Hushclaw Team",
        "tags": "爬虫, 价格监控, 数据采集",
    },
    {
        "title": "招聘信息聚合",
        "short_desc": "同时搜索多个招聘平台，去重汇总，按条件筛选职位",
        "description": "配置岗位关键词、城市、薪资范围后：\n\n• 同时搜索 Boss 直聘、智联招聘、猎聘等平台\n• 自动去除重复职位\n• 按薪资、发布时间、公司规模排序\n• 导出到表格，支持一键投递\n\n每天定时运行，第一时间获取最新岗位。",
        "category": "data-collection",
        "platform": "all",
        "install_count": 1870,
        "rating_sum": 118,
        "rating_count": 28,
        "author": "陈晨",
        "tags": "招聘, 求职, 数据聚合",
    },
    {
        "title": "学术论文追踪",
        "short_desc": "监控 arXiv、Google Scholar 等平台，自动推送关键词相关新论文",
        "description": "设置研究方向关键词后：\n\n• 每天扫描 arXiv、Semantic Scholar 最新论文\n• AI 提炼摘要（支持中文输出）\n• 按引用数、发表时间排序\n• 重要论文自动添加到阅读清单\n\n支持导出 BibTeX 格式引用。",
        "category": "data-collection",
        "platform": "all",
        "install_count": 730,
        "rating_sum": 58,
        "rating_count": 14,
        "author": "刘洋",
        "tags": "学术, 论文, arXiv, 研究",
    },

    # 表单自动化
    {
        "title": "批量注册网站账号",
        "short_desc": "根据提供的信息列表，自动批量完成网站注册流程",
        "description": "上传包含用户名、邮箱等信息的 CSV 文件：\n\n• 自动依次访问目标网站注册页面\n• 填写各字段，处理验证码（支持图形验证码识别）\n• 记录注册成功/失败结果\n• 错误重试机制\n\n⚠️ 请确保符合目标网站服务条款，仅用于合规场景。",
        "category": "form-automation",
        "platform": "all",
        "install_count": 1200,
        "rating_sum": 72,
        "rating_count": 19,
        "author": "Hushclaw Team",
        "tags": "表单, 注册, 批量操作",
    },
    {
        "title": "政务表单智能填写",
        "short_desc": "读取个人证件信息，自动填写各类政府网站在线申请表单",
        "description": "上传身份证、户口本等证件照后：\n\n• OCR 提取姓名、身份证号、地址等字段\n• 自动匹配并填写政务网站对应字段\n• 支持下拉菜单、单选框、文件上传\n• 填写完成后截图存档\n\n支持社保查询、公积金申请、户籍业务等常见政务场景。",
        "category": "form-automation",
        "platform": "all",
        "install_count": 2100,
        "rating_sum": 140,
        "rating_count": 32,
        "author": "赵磊",
        "tags": "政务, 表单, 证件, OCR",
    },

    # 电商监控
    {
        "title": "京东/天猫降价提醒",
        "short_desc": "监控商品历史价格，降价时立即推送桌面通知",
        "description": "添加商品链接后：\n\n• 记录当前价格作为基准\n• 每小时检查最新价格（含促销活动价格）\n• 降幅超过设定阈值（如 5%）时推送通知\n• 显示历史价格折线图\n• 节日大促期间加密监控频率\n\n支持京东、天猫、拼多多主要平台。",
        "category": "ecommerce",
        "platform": "all",
        "install_count": 5600,
        "rating_sum": 378,
        "rating_count": 84,
        "author": "Hushclaw Team",
        "tags": "价格, 电商, 京东, 天猫, 购物",
    },
    {
        "title": "店铺销售数据日报",
        "short_desc": "自动抓取电商后台数据，生成每日销售简报",
        "description": "登录电商卖家后台后：\n\n• 自动采集当日/昨日订单量、销售额、退款率\n• 对比上周同期数据，计算增长率\n• 列出销量 Top10 商品\n• 生成图表并导出 PDF 报告\n\n支持淘宝卖家中心、京东商家后台、拼多多商家版。",
        "category": "ecommerce",
        "platform": "all",
        "install_count": 1450,
        "rating_sum": 98,
        "rating_count": 23,
        "author": "孙丽",
        "tags": "电商, 销售, 报表, 卖家",
    },

    # 政务民生
    {
        "title": "社保缴费记录查询",
        "short_desc": "自动登录社保网站，获取缴费记录并保存为本地文件",
        "description": "首次使用需完成实名认证，之后：\n\n• 自动登录当地社保局网站\n• 导出近 5 年缴费明细\n• 计算累计缴费年限和金额\n• 转换为 Excel 格式本地保存\n\n支持全国主要城市社保查询系统，数据仅保存本地。",
        "category": "government",
        "platform": "all",
        "install_count": 3200,
        "rating_sum": 205,
        "rating_count": 47,
        "author": "Hushclaw Team",
        "tags": "社保, 政务, 查询",
    },
    {
        "title": "公积金余额及贷款查询",
        "short_desc": "自动登录住房公积金中心，查询账户余额、贷款额度及还款记录",
        "description": "通过官方公积金网站：\n\n• 自动获取账户余额和月缴金额\n• 查询可贷款额度\n• 导出还款计划表\n• 记录历史提取记录\n\n数据全程本地处理，不上传任何服务器。",
        "category": "government",
        "platform": "all",
        "install_count": 2700,
        "rating_sum": 175,
        "rating_count": 40,
        "author": "周强",
        "tags": "公积金, 政务, 贷款",
    },
    {
        "title": "火车票自动抢票（macOS）",
        "short_desc": "12306 网页版自动刷票，发现余票立即下单，支持候补购票",
        "description": "配置出发地、目的地、日期、车次偏好后：\n\n• 实时刷新余票状态\n• 发现指定车次有票立即自动选座下单\n• 支持候补购票流程\n• 多车次并行监控\n• 购票成功后发送桌面通知\n\n注意：需提前登录 12306 并完成常用联系人设置。仅在 macOS 经过测试。",
        "category": "government",
        "platform": "mac",
        "install_count": 8900,
        "rating_sum": 580,
        "rating_count": 130,
        "author": "Hushclaw Team",
        "tags": "12306, 抢票, 火车票, 春运",
    },
    {
        "title": "驾照科目一刷题（Windows）",
        "short_desc": "自动在驾校刷题网站循环做题，统计错题并重点练习",
        "description": "打开任意驾考刷题网站后：\n\n• 自动连续作答题目\n• 错题自动收藏，生成错题本\n• 统计各章节正确率\n• 模拟考试模式（随机 100 题计时）\n\n仅在 Windows 平台测试通过，Mac 版本开发中。",
        "category": "government",
        "platform": "windows",
        "install_count": 4300,
        "rating_sum": 275,
        "rating_count": 63,
        "author": "吴建国",
        "tags": "驾照, 刷题, 学习",
    },
    {
        "title": "个税申报自动填写",
        "short_desc": "从个人所得税 APP 网页版导出数据，自动填写年度汇算申报表",
        "description": "年度个税汇算期间：\n\n• 自动读取工资薪金、专项附加扣除信息\n• 核对收入和已预缴税款\n• 自动填写汇算申报各项字段\n• 计算应退/应补税额\n• 填写完成后截图留存\n\n支持 2024 年度及以后的汇算申报。",
        "category": "government",
        "platform": "all",
        "install_count": 6100,
        "rating_sum": 395,
        "rating_count": 89,
        "author": "Hushclaw Team",
        "tags": "个税, 税务, 年度汇算",
    },
]

base_date = datetime.utcnow()
for i, s in enumerate(skills_data):
    cat = cats[s["category"]]
    created = base_date - timedelta(days=random.randint(1, 180))
    skill = Skill(
        title=s["title"],
        short_desc=s["short_desc"],
        description=s["description"],
        category_id=cat.id,
        platform=s["platform"],
        install_count=s["install_count"],
        rating_sum=s["rating_sum"],
        rating_count=s["rating_count"],
        author=s["author"],
        tags=s["tags"],
        is_active=True,
        created_at=created,
    )
    db.add(skill)

db.commit()
db.close()

print(f"✅ 数据库初始化完成")
print(f"   分类: {len(categories_data)} 个")
print(f"   技能: {len(skills_data)} 个")
print(f"\n运行: uvicorn app.main:app --reload --port 8000")
print(f"访问: http://localhost:8000")
