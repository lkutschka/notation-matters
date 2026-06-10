browser_candidate_references = {
    "url": [
        "https://www.baidu.com",
        "https://www.taobao.com",
        "https://www.jd.com",
        "https://www.qq.com",
        "https://www.sina.com.cn",
        "https://www.163.com",
        "https://www.sohu.com",
        "https://www.zhihu.com",
        "https://www.douban.com",
        "https://www.bilibili.com",
        "https://www.weibo.com",
        "https://www.tmall.com",
        "https://www.alipay.com",
        "https://www.ctrip.com",
        "https://www.meituan.com",
        "https://www.douyin.com",
        "https://www.xiaohongshu.com",
        "https://www.youku.com",
        "https://www.iqiyi.com",
        "https://www.tencent.com",
        "https://www.xiaomi.com",
        "https://www.huawei.com",
        "https://www.oppo.com",
        "https://www.vivo.com",
        "https://www.oneplus.com",
        "https://www.realme.com",
        "https://www.meizu.com",
        "https://www.zte.com",
        "https://www.alibaba.com",
        "https://www.aliexpress.com",
        "https://www.amazon.cn",
        "https://www.kuaishou.com",
        "https://www.yy.com",
        "https://www.huya.com",
        "https://www.douyu.com",
        "https://www.v.qq.com",
        "https://www.mgtv.com",
        "https://www.le.com",
        "https://www.pptv.com",
        "https://www.fun.tv",
        "https://www.cntv.cn",
        "https://www.cctv.com",
        "https://www.people.com.cn",
        "https://www.xinhuanet.com",
        "https://www.chinanews.com.cn",
        "https://www.gmw.cn",
        "https://www.cyol.com",
        "https://www.jschina.com.cn",
        "https://www.ynet.com",
        "https://www.thepaper.cn",
        "https://www.jiemian.com",
        "https://www.caixin.com"
    ],
    "iframeSelector": [
        "#iframeResult",
        "#iframeContent",
        ".iframe-container iframe",
        "#externalFrame",
        "#embedFrame",
        "#playerFrame",
        "#videoFrame",
        "#loginFrame",
        "#paymentFrame",
        "#chatFrame",
        "#adFrame",
        "#previewFrame",
        "#widgetFrame",
        "#contentFrame",
        "#mainFrame",
        "#sideFrame",
        "#popupFrame",
        "#modalFrame",
        "#dynamicFrame",
        "#thirdPartyFrame"
    ],
    "selector": [
        "#username",
        "#password",
        ".login-btn",
        ".search-input",
        ".submit-btn",
        "#main-nav",
        ".product-item",
        ".add-to-cart",
        "#checkout-btn",
        ".user-avatar",
        ".dropdown-menu",
        "#home-link",
        "#contact-form",
        ".news-item",
        ".video-player",
        "#comment-box",
        ".rating-stars",
        "#footer-links",
        ".social-share",
        ".cookie-banner"
    ],
    "key": [
        "Enter",
        "Tab",
        "ArrowDown",
        "ArrowUp",
        "ArrowLeft",
        "ArrowRight",
        "Escape",
        "Backspace",
        "Delete",
        "Home",
        "End",
        "PageUp",
        "PageDown",
        "F5",
        "Control",
        "Alt",
        "Shift",
        "Space",
        "a",
        "1"
    ],
    "script": [
        "document.title",
        "window.scrollTo(0, document.body.scrollHeight)",
        "alert('test')",
        "console.log('hello world')",
        "document.querySelector('button').click()",
        "window.location.href",
        "document.cookie",
        "localStorage.getItem('token')",
        "sessionStorage.setItem('key', 'value')",
        "document.querySelectorAll('.item').length",
        "window.innerWidth",
        "window.innerHeight",
        "document.readyState",
        "performance.now()",
        "navigator.userAgent",
        "document.querySelector('input').value = 'test'",
        "document.activeElement.blur()",
        "window.history.back()",
        "window.print()",
        "document.execCommand('copy')"
    ],
    "value": [
        "testuser",
        "password123",
        "example@example.com",
        "13800138000",
        "2023-01-01",
        "100.00",
        "https://example.com",
        "123456",
        "18"
    ]
}

finance_candidate_references = {
    "symbol_list": [
        # Global Market Stock
        "AAPL",      # Apple Inc.
        "MSFT",      # Microsoft Corporation
        "GOOGL",     # Alphabet Inc. (Google)
        "AMZN",      # Amazon.com Inc.
        "NVDA",      # NVIDIA Corporation
        "META",      # Meta Platforms Inc. - Meta/Facebook
        "TSLA",      # Tesla Inc.
        "BRK.A",     # Berkshire Hathaway
        "BRK.B",     # Berkshire Hathaway
        "LLY",       # Eli Lilly and Company
        "TSM",       # Taiwan Semiconductor
        "WMT",       # Walmart Inc.
        "JPM",       # JPMorgan Chase & Co.
        "V",         # Visa Inc.
        "PG",        # Procter & Gamble
        "UNH",       # UnitedHealth Group
        "HD",        # Home Depot
        "MA",        # Mastercard
        "BAC",       # Bank of America
        "ABBV",      # AbbVie Inc.
        "PFE",       # Pfizer Inc. 
        "KO",        # Coca-Cola Company
        "PEP",       # PepsiCo Inc.
        "MRK",       # Merck & Co.
        "CSCO",      # Cisco Systems
        "ADBE",      # Adobe Inc.
        "NFLX",      # Netflix Inc.
        "CRM",       # Salesforce Inc.
        "ACN",       # Accenture plc 
        "TMO",       # Thermo Fisher Scientific
        # China Mainland Stock List
        "SH600519",  # 贵州茅台
        "SH600036",  # 招商银行
        "SH600900",  # 长江电力
        "SH600276",  # 恒瑞医药
        "SH600887",  # 伊利股份
        "SH600031",  # 三一重工
        "SH600000",  # 浦发银行
        "SH600028",  # 中国石化
        "SH600030",  # 中信证券
        "SH600104",  # 上汽集团
        "SZ000858",  # 五粮液
        "SZ000002",  # 万科A
        "SZ000001",  # 平安银行
        "SZ000333",  # 美的集团
        "SZ000651",  # 格力电器
        "SZ000725",  # 京东方A
        "SZ000063",  # 中兴通讯
        "SZ002594",  # 比亚迪
        "SZ300750",  # 宁德时代
        "SZ300059",  # 东方财富
        # HKEX
        "00700",     # 腾讯控股 - Tencent Holdings
        "03690",     # 美团点评 - Meituan Dianping
        "09988",     # 阿里巴巴 - Alibaba Group
        "01810",     # 小米集团 - Xiaomi Corporation
        "09618",     # 京东集团 - JD.com
        "09868",     # 小鹏汽车 - XPeng Motors
        "02015",     # 理想汽车 - Li Auto
        "09866",     # 蔚来汽车 - NIO Inc.
        "02382",     # 舜宇光学 - Sunny Optical
        "00780",     # 同程旅行 - Tongcheng Travel
        "02331",     # 李宁 - Li Ning
        "02020",     # 安踏体育 - ANTA Sports
        "03692",     # 翰森制药 - Hansoh Pharmaceutical
        "01177",     # 中国生物制药 - Sino Biopharmaceutical
        "01093",     # 石药集团 - CSPC Pharmaceutical
        "02269",     # 药明生物 - WuXi Biologics
        "03613",     # 同仁堂国药 - Tong Ren Tang Technologies
        "00883",     # 中国海洋石油 - CNOOC
        "00939",     # 建设银行 - China Construction Bank
        "01398"      # 工商银行 - Industrial and Commercial Bank of China
    ],
    "market": [
        "US",          # United States
        "HK",          # HKEX
        "CN_MAINLAND", # China Mainland Stock A
        "LSE",         # London Stock Exchange
        "NSE_INDIA",   # National Stock Exchange India
        "JPX",         # Japan
        "ASX",         # Australia
        "TSX",         # Toronto
        "FWB",         # Frankfurt
        "EURONEXT",    # EURONEXT
        "SSE",         # Shanghia
        "SZSE",        # Shenzhen
        "KRX",         # Korean
        "SGX",         # Singapore
        "TSE",         # Tokyo
        "BSE",         # Bombay
        "MOEX",        # Moscow
    ]
}

search_candidate_references = {
}

map_candidate_references = {
}

filesystem_candidate_references = {
}

pay_candidate_references = {
}

browser_special_needs_description = '''
1. 对于iframe操作，需要先定位iframe再操作内部元素
2. 文件上传操作需要特殊处理，不能直接设置input值
3. 动态加载的内容需要等待元素出现
4. 跨域iframe有安全限制需要注意
'''

finance_special_needs_description = '''
1. Note that the stock codes and market codes in the candidate set must match exactly, for example, SH600519 must match CN_MAINLAND, AAPL must match US, and there cannot be a pairing of stock codes that do not exist in the market.
2. The values of the candidate set are all from the list provided by the Parameter candidate value reference.
3. If it is easy to determine the market it belongs to from the stock code, the query does not reflect the market, which is closer to the user's daily inquiries, such as directly asking "What is the current share price of <symble>?" instead of "What is the current share price of <symble> in the <market> market?". Of course, the label parameter is still given in full as usual.
'''

search_special_needs_description = '''
'''

map_special_needs_description = '''
'''

filesystem_special_needs_description = '''
'''

pay_special_needs_description = '''
'''

candidate_reference_list = {
    "browser": browser_candidate_references,
    "finance": finance_candidate_references,
    "search": search_candidate_references,
    "map": map_candidate_references,
    "filesystem": filesystem_candidate_references,
    "pay": pay_candidate_references
}

special_needs_description_list = {
    "browser": browser_special_needs_description,
    "finance": finance_special_needs_description,
    "search": search_special_needs_description,
    "map": map_special_needs_description,
    "filesystem": filesystem_special_needs_description,
    "pay": pay_special_needs_description
}
