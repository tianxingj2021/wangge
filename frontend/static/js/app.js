// API基础URL
const API_BASE = '/api/v1';

// 主题管理
(function() {
    const THEME_STORAGE_KEY = 'theme-preference';
    const DARK_MODE_CLASS = 'dark-mode';
    
    // 获取当前主题
    function getCurrentTheme() {
        // 优先使用localStorage中保存的主题
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        if (savedTheme === 'dark' || savedTheme === 'light') {
            return savedTheme;
        }
        
        // 如果没有保存的主题，检测系统偏好
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    // 应用主题
    function applyTheme(theme) {
        const html = document.documentElement;
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        if (theme === 'dark') {
            html.classList.add(DARK_MODE_CLASS);
            if (themeIcon) themeIcon.textContent = '☀️';
            if (themeText) themeText.textContent = '浅色';
        } else {
            html.classList.remove(DARK_MODE_CLASS);
            if (themeIcon) themeIcon.textContent = '🌙';
            if (themeText) themeText.textContent = '深色';
        }
        
        // 保存到localStorage
        localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
    
    // 切换主题
    function toggleTheme(e) {
        e.preventDefault();
        e.stopPropagation();
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }
    
    // 初始化主题
    function initTheme() {
        // 先应用主题（避免闪烁）
        const theme = getCurrentTheme();
        applyTheme(theme);
        
        // 绑定切换按钮
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', toggleTheme);
            console.log('主题切换按钮已绑定');
        } else {
            console.error('未找到主题切换按钮');
        }
        
        // 监听系统主题变化（仅在未手动设置时）
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // 只有在localStorage中没有保存主题时才跟随系统
                const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
                if (!savedTheme || savedTheme === 'auto') {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
    
    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        // DOM已经加载完成，立即初始化
        initTheme();
    }
})();

// 显示消息
function showMessage(text, type = 'success') {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    setTimeout(() => {
        messageEl.className = 'message';
    }, 3000);
}

// 标签页状态管理
const ACTIVE_TAB_STORAGE_KEY = 'active-tab';

// 保存当前选中的标签页
function saveActiveTab(page) {
    localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, page);
}

// 获取保存的标签页
function getSavedActiveTab() {
    return localStorage.getItem(ACTIVE_TAB_STORAGE_KEY) || 'dashboard';
}

// 切换到指定标签页
function switchToTab(page) {
    // 更新按钮状态
    document.querySelectorAll('.nav-btn').forEach(b => {
        if (b.dataset.page === page) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
    
    // 更新页面显示
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const targetPage = document.getElementById(`${page}-page`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // 保存到localStorage
    saveActiveTab(page);
    
    // 加载对应页面数据
    if (page === 'dashboard') {
        loadDashboard();
    } else if (page === 'config') {
        // 配置页面：立即加载交易所配置
        loadExchangeConfig();
    } else if (page === 'strategy') {
        // 策略页面：并行加载交易所列表和策略类型，然后加载策略列表
        Promise.all([
            loadExchangesForStrategy(),
            loadStrategyTypes()
        ]).then(() => {
            loadStrategies();
        });
    } else if (page === 'order') {
        loadOrders();
    } else if (page === 'account') {
        loadBalance();
    }
}

// 页面导航
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const page = btn.dataset.page;
        switchToTab(page);
    });
});

// 加载仪表盘数据
async function loadDashboard() {
    try {
        // 先加载策略列表（关键数据）
        const strategiesRes = await fetch(`${API_BASE}/strategy/list`);
        
        // 处理策略列表
        if (strategiesRes.ok) {
            const strategiesData = await strategiesRes.json();
            const runningCount = strategiesData.strategies.filter(s => s.is_running).length;
            document.getElementById('running-strategies').textContent = runningCount;
        } else {
            document.getElementById('running-strategies').textContent = '--';
        }
        
        // 余额延迟加载（非关键数据，不阻塞页面）
        // 先显示"加载中..."，然后异步加载
        document.getElementById('total-balance').textContent = '加载中...';
        loadBalanceAsync();
        
    } catch (error) {
        console.error('加载仪表盘失败:', error);
        document.getElementById('running-strategies').textContent = '--';
        document.getElementById('total-balance').textContent = '--';
    }
}

// 异步加载余额（带超时控制和重试机制）
async function loadBalanceAsync(retryCount = 0) {
    const maxRetries = 1; // 最多重试1次
    try {
        // 增加超时时间到60秒，与后端初始化超时时间一致
        // Extended交易所初始化在主网上可能需要30-60秒
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);
        
        try {
            const balanceRes = await fetch(`${API_BASE}/exchange/balance`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (balanceRes.ok) {
                const balanceData = await balanceRes.json();
                const balanceValue = balanceData.total || '--';
                document.getElementById('total-balance').textContent = balanceValue;
                console.log('余额加载成功:', balanceValue);
            } else {
                // 如果失败且还有重试次数，则重试
                if (retryCount < maxRetries) {
                    console.log(`余额获取失败，${2}秒后重试...`);
                    document.getElementById('total-balance').textContent = '重试中...';
                    setTimeout(() => {
                        loadBalanceAsync(retryCount + 1);
                    }, 2000);
                } else {
                    document.getElementById('total-balance').textContent = '--';
                }
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                // 超时，如果还有重试次数，则重试
                if (retryCount < maxRetries) {
                    console.log(`余额获取超时，${2}秒后重试...`);
                    document.getElementById('total-balance').textContent = '重试中...';
                    setTimeout(() => {
                        loadBalanceAsync(retryCount + 1);
                    }, 2000);
                } else {
                    document.getElementById('total-balance').textContent = '--';
                    console.log('余额获取超时，已放弃');
                }
            } else {
                // 其他错误，如果还有重试次数，则重试
                if (retryCount < maxRetries) {
                    console.log(`余额获取失败: ${fetchError.message}，${2}秒后重试...`);
                    document.getElementById('total-balance').textContent = '重试中...';
                    setTimeout(() => {
                        loadBalanceAsync(retryCount + 1);
                    }, 2000);
                } else {
                    throw fetchError;
                }
            }
        }
    } catch (error) {
        // 余额获取失败，显示"--"
        document.getElementById('total-balance').textContent = '--';
        console.log('余额获取失败:', error.message);
    }
}

// 策略类型和配置
let strategyTypes = [];
let currentStrategyType = null;

// 加载交易所列表供策略选择（账号列表）
async function loadExchangesForStrategy() {
    try {
        const res = await fetch(`${API_BASE}/config/exchanges`);
        const data = await res.json();
        
        const select = document.getElementById('strategy-exchange');
        select.innerHTML = '<option value="">请选择交易所账号</option>';
        
        // 处理API返回格式：{"exchanges": [...], "count": ...}
        const exchanges = data.exchanges || (Array.isArray(data) ? data : []);
        
        if (exchanges && exchanges.length > 0) {
            exchanges.forEach(exchange => {
                const option = document.createElement('option');
                // 使用account_key作为value（如果存在），否则使用name（向后兼容）
                option.value = exchange.account_key || exchange.name;
                // 显示账号别名或显示名称
                const displayName = exchange.account_alias || exchange.display_name || exchange.name.charAt(0).toUpperCase() + exchange.name.slice(1);
                const exchangeName = exchange.exchange_name || exchange.name;
                const testnetText = exchange.testnet ? ' (测试网)' : ' (主网)';
                option.textContent = `${displayName} (${exchangeName})${testnetText}`;
                // 保存account_key到data属性（用于向后兼容）
                option.dataset.accountKey = exchange.account_key || exchange.name;
                select.appendChild(option);
            });
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '暂无已配置的交易所';
            option.disabled = true;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('加载交易所列表失败:', error);
        const select = document.getElementById('strategy-exchange');
        select.innerHTML = '<option value="">加载失败</option>';
    }
}

// 加载策略类型列表
async function loadStrategyTypes() {
    try {
        const res = await fetch(`${API_BASE}/strategy/types`);
        const data = await res.json();
        strategyTypes = data.strategy_types;
        
        const select = document.getElementById('strategy-type');
        select.innerHTML = '<option value="">请选择策略类型</option>';
        
        strategyTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.type;
            option.textContent = `${type.name} - ${type.description}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载策略类型失败:', error);
        showMessage('加载策略类型失败: ' + error.message, 'error');
    }
}

// 策略类型改变时更新配置表单
function onStrategyTypeChange() {
    const select = document.getElementById('strategy-type');
    const strategyType = select.value;
    const container = document.getElementById('strategy-config-container');
    const paramsContainer = document.getElementById('strategy-params-content');
    const collapsible = document.getElementById('strategy-params-collapsible');
    
    if (!strategyType) {
        container.innerHTML = '';
        collapsible.style.display = 'none';
        currentStrategyType = null;
        return;
    }
    
    const typeInfo = strategyTypes.find(t => t.type === strategyType);
    if (!typeInfo) {
        container.innerHTML = '<p>策略类型不存在</p>';
        collapsible.style.display = 'none';
        return;
    }
    
    currentStrategyType = typeInfo;
    container.innerHTML = '';
    paramsContainer.innerHTML = '';
    
    // 分离必填字段和可选字段
    const requiredFields = typeInfo.config_fields.filter(f => f.required);
    const optionalFields = typeInfo.config_fields.filter(f => !f.required);
    
    // 生成必填字段（显示在主容器中）
    requiredFields.forEach(field => {
        const formGroup = createFormField(field);
        container.appendChild(formGroup);
    });
    
    // 生成可选字段（显示在折叠容器中）
    if (optionalFields.length > 0) {
        collapsible.style.display = 'block';
        // 默认折叠状态
        paramsContainer.classList.add('collapsed');
        const header = document.querySelector('.collapsible-header');
        if (header) {
            header.classList.add('collapsed');
        }
        const icon = document.getElementById('collapse-icon');
        if (icon) {
            icon.textContent = '▶';
        }
        
        optionalFields.forEach(field => {
            const formGroup = createFormField(field);
            paramsContainer.appendChild(formGroup);
        });
    } else {
        collapsible.style.display = 'none';
    }
}

// 创建表单字段的辅助函数
function createFormField(field) {
    const formGroup = document.createElement('div');
    formGroup.className = 'form-group';
    
    const label = document.createElement('label');
    label.textContent = field.label + (field.required ? ' *' : '') + ':';
    
    let input;
    if (field.type === 'select') {
        input = document.createElement('select');
        if (field.options) {
            field.options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt.value;
                option.textContent = opt.label;
                input.appendChild(option);
            });
        }
    } else {
        input = document.createElement('input');
        input.type = field.type;
        if (field.placeholder) {
            input.placeholder = field.placeholder;
        }
        if (field.step) {
            input.step = field.step;
        }
        if (field.min !== undefined) {
            input.min = field.min;
        }
        if (field.default !== undefined) {
            input.value = field.default;
        }
    }
    
    input.id = `strategy-${field.name}`;
    input.required = field.required || false;
    
    formGroup.appendChild(label);
    formGroup.appendChild(input);
    return formGroup;
}

// 切换策略参数折叠/展开
function toggleStrategyParams() {
    const content = document.getElementById('strategy-params-content');
    const header = document.querySelector('.collapsible-header');
    const icon = document.getElementById('collapse-icon');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        header.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        header.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

// 策略表单提交
document.getElementById('strategy-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!currentStrategyType) {
        showMessage('请先选择策略类型', 'error');
        return;
    }
    
    // 获取选择的账号
    const exchangeSelect = document.getElementById('strategy-exchange');
    const accountKey = exchangeSelect.value;
    
    if (!accountKey) {
        showMessage('请先选择交易所账号', 'error');
        return;
    }
    
    // 收集配置数据（优先使用account_key，向后兼容exchange_name）
    const config = {
        account_key: accountKey
    };
    
    // 验证必填字段
    for (const field of currentStrategyType.config_fields) {
        if (field.required) {
            const input = document.getElementById(`strategy-${field.name}`);
            if (!input || !input.value.trim()) {
                showMessage(`请填写必填字段: ${field.label || field.name}`, 'error');
                return;
            }
        }
    }
    
    // 收集所有字段值
    currentStrategyType.config_fields.forEach(field => {
        const input = document.getElementById(`strategy-${field.name}`);
        if (input) {
            let value = input.value.trim();
            
            // 如果字段为空且不是必填的，跳过（使用后端默认值）
            if (!value && !field.required) {
                return; // 不发送可选字段，使用后端默认值
            }
            
            // 根据字段类型转换
            if (field.type === 'number') {
                if (field.step && field.step.includes('.')) {
                    value = parseFloat(value);
                } else {
                    value = parseInt(value);
                }
                // 检查是否为有效数字
                if (isNaN(value)) {
                    showMessage(`${field.label || field.name} 必须是有效数字`, 'error');
                    return;
                }
            }
            
            // 对于滑动窗口网格策略，order_size 需要是字符串（但保持数字精度）
            if (currentStrategyType.type === 'sliding_window_grid' && field.name === 'order_size') {
                // 如果已经是数字，转换为字符串；否则直接使用原始值
                if (typeof value === 'number') {
                    value = value.toString();
                } else {
                    value = String(value);
                }
            }
            
            config[field.name] = value;
        }
    });
    
    // 根据策略类型选择API端点
    let apiEndpoint;
    if (currentStrategyType.type === 'grid') {
        apiEndpoint = `${API_BASE}/strategy/grid/start`;
        config.order_type = 'limit';
    } else if (currentStrategyType.type === 'sliding_window_grid') {
        apiEndpoint = `${API_BASE}/strategy/sliding-window-grid/start`;
    } else {
        showMessage('不支持的策略类型', 'error');
        return;
    }
    
    try {
        const res = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('策略启动成功！', 'success');
            // 启动成功后立即插入策略卡片，避免等待列表刷新
            addStrategyCard(data.strategy_id, config.symbol, currentStrategyType.type);
            document.getElementById('strategy-form').reset();
            document.getElementById('strategy-type').value = '';
            onStrategyTypeChange();
            loadStrategies();
        } else {
            // 显示详细的验证错误信息
            let errorMsg = '策略启动失败';
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    // Pydantic 验证错误格式
                    errorMsg = data.detail.map(err => {
                        const field = err.loc ? err.loc.join('.') : '未知字段';
                        return `${field}: ${err.msg}`;
                    }).join('; ');
                } else {
                    errorMsg = data.detail;
                }
            }
            console.error('策略启动失败:', data);
            showMessage(errorMsg, 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
});

// WebSocket连接管理
const strategyWebSockets = {};

// 策略状态轮询定时器管理（用于非滑动窗口网格，或WebSocket回退场景）
const strategyPollIntervals = {};

// 策略状态请求的 AbortController 管理，避免同一策略并发多个 /status 请求
const strategyStatusControllers = {};

function startStrategyPolling(strategyId, strategyType, immediate = true) {
    // 避免重复创建轮询定时器
    if (strategyPollIntervals[strategyId]) {
        clearInterval(strategyPollIntervals[strategyId]);
    }
    if (immediate) {
        loadStrategyStatus(strategyId, strategyType);
    }
    const intervalId = setInterval(() => {
        loadStrategyStatus(strategyId, strategyType);
    }, 3000);
    strategyPollIntervals[strategyId] = intervalId;
}

function stopStrategyPolling(strategyId) {
    if (strategyPollIntervals[strategyId]) {
        clearInterval(strategyPollIntervals[strategyId]);
        delete strategyPollIntervals[strategyId];
    }
}

// 启动后直接插入策略卡片
function addStrategyCard(strategyId, symbol, strategyType) {
    const container = document.getElementById('strategy-list-container');
    if (!container) return;
    if (container.innerHTML.includes('暂无运行中的策略')) {
        container.innerHTML = '';
    }
    const item = document.createElement('div');
    item.className = 'strategy-item';
    item.id = `strategy-${strategyId}`;
    item.innerHTML = `
        <div class="strategy-card-header">
            <div class="strategy-card-title">
                <span class="strategy-symbol">${symbol}</span>
                <span class="status-indicator running" id="strategy-status-indicator-${strategyId}">
                    <span class="status-dot running"></span>
                    <span>运行中</span>
                </span>
            </div>
            <div class="actions" id="strategy-actions-${strategyId}">
                <button class="btn-small" onclick="updateStrategy('${strategyId}', '${strategyType}')">更新</button>
                <button class="btn-small btn-danger" onclick="stopStrategy('${strategyId}', '${strategyType}')">停止</button>
                <button class="btn-small btn-danger" onclick="deleteStrategy('${strategyId}')" title="删除策略">删除</button>
            </div>
        </div>
        <div class="strategy-card-content">
            <div class="info">
                <div id="strategy-status-${strategyId}">
                    <p>加载中...</p>
                </div>
            </div>
        </div>
    `;
    container.prepend(item);
    if (strategyType === 'sliding_window_grid') {
        // 先立即加载一次状态，避免等待WebSocket连接
        loadStrategyStatus(strategyId, strategyType);
        // 确保没有残留的轮询
        stopStrategyPolling(strategyId);
        // 然后启动WebSocket连接
        connectStrategyWebSocket(strategyId, symbol, strategyType);
    } else {
        // 使用轮询方式更新状态（统一通过管理函数，避免重复定时器）
        startStrategyPolling(strategyId, strategyType, true);
    }
}

// 加载策略列表
async function loadStrategies() {
    try {
        const res = await fetch(`${API_BASE}/strategy/list`);
        const data = await res.json();
        
        const container = document.getElementById('strategy-list-container');
        container.innerHTML = '';
        
        if (data.strategies.length === 0) {
            container.innerHTML = '<p>暂无运行中的策略</p>';
            return;
        }
        
        for (let index = 0; index < data.strategies.length; index++) {
            const strategy = data.strategies[index];
            const item = document.createElement('div');
            item.className = 'strategy-item';
            item.id = `strategy-${strategy.strategy_id}`;
            
            try {
                // 根据策略类型加载不同的状态
                let updateEndpoint;
                let stopEndpoint;
                
                if (strategy.strategy_type === 'grid') {
                    updateEndpoint = `${API_BASE}/strategy/grid/${strategy.strategy_id}/update`;
                    stopEndpoint = `${API_BASE}/strategy/grid/${strategy.strategy_id}/stop`;
                } else if (strategy.strategy_type === 'sliding_window_grid') {
                    updateEndpoint = `${API_BASE}/strategy/sliding-window-grid/${strategy.strategy_id}/update`;
                    stopEndpoint = `${API_BASE}/strategy/sliding-window-grid/${strategy.strategy_id}/stop`;
                } else {
                    updateEndpoint = `${API_BASE}/strategy/grid/${strategy.strategy_id}/update`;
                    stopEndpoint = `${API_BASE}/strategy/grid/${strategy.strategy_id}/stop`;
                }
                
                // 获取账号信息
                const accountAlias = strategy.account_alias || strategy.exchange_name || '未知账号';
                
                // 创建卡片式HTML结构
                let initialHtml = `
                    <div class="strategy-card-header">
                        <div class="strategy-card-title">
                            <span class="strategy-symbol">${strategy.symbol}</span>
                            <span class="account-badge">${accountAlias}</span>
                            <span class="status-indicator running" id="strategy-status-indicator-${strategy.strategy_id}">
                                <span class="status-dot running"></span>
                                <span>运行中</span>
                            </span>
                        </div>
                        <div class="actions" id="strategy-actions-${strategy.strategy_id}">
                            <button class="btn-small" onclick="updateStrategy('${strategy.strategy_id}', '${strategy.strategy_type}')">更新</button>
                            <button class="btn-small btn-danger" onclick="stopStrategy('${strategy.strategy_id}', '${strategy.strategy_type}')">停止</button>
                            <button class="btn-small btn-danger" onclick="deleteStrategy('${strategy.strategy_id}')" title="删除策略">删除</button>
                        </div>
                    </div>
                    <div class="strategy-card-content">
                        <div class="info">
                            <div id="strategy-status-${strategy.strategy_id}">
                                <p>加载中...</p>
                            </div>
                        </div>
                    </div>
                `;
                
                item.innerHTML = initialHtml;
                container.appendChild(item);
                
                // 延迟加载策略状态，避免同时发起大量请求
                // 使用分批加载，每个策略延迟不同的时间
                const delay = index * 200; // 每个策略延迟200ms
                setTimeout(() => {
                    // 启动WebSocket连接（仅对滑动窗口网格策略）
                    if (strategy.strategy_type === 'sliding_window_grid') {
                        // 先立即加载一次状态，避免等待WebSocket连接
                        loadStrategyStatus(strategy.strategy_id, strategy.strategy_type);
                        // 确保没有残留的轮询
                        stopStrategyPolling(strategy.strategy_id);
                        // 然后启动WebSocket连接
                        connectStrategyWebSocket(strategy.strategy_id, strategy.symbol, strategy.strategy_type);
                    } else {
                        // 传统网格策略使用轮询（通过统一管理，避免多个定时器叠加）
                        startStrategyPolling(strategy.strategy_id, strategy.strategy_type, true);
                    }
                }, delay);
            } catch (error) {
                console.error(`加载策略 ${strategy.strategy_id} 详情失败:`, error);
                item.innerHTML = `
                    <div class="info">
                        <strong>${strategy.symbol}</strong>
                        <p>加载详情失败: ${error.message}</p>
                    </div>
                `;
                container.appendChild(item);
            }
        }
    } catch (error) {
        console.error('加载策略列表失败:', error);
        showMessage('加载策略列表失败: ' + error.message, 'error');
    }
}

// 连接策略WebSocket
function connectStrategyWebSocket(strategyId, symbol, strategyType) {
    // 如果已有连接，先关闭
    if (strategyWebSockets[strategyId]) {
        strategyWebSockets[strategyId].close();
    }
    
    // 确定WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    // WebSocket路由在/api/v1/ws下
    const wsUrl = `${wsProtocol}//${wsHost}${API_BASE}/ws/strategy/${strategyId}`;
    
    const ws = new WebSocket(wsUrl);
    strategyWebSockets[strategyId] = ws;
    
    ws.onopen = () => {
        console.log(`WebSocket连接已建立: ${strategyId}`);
        // WebSocket 建立后，确保关闭轮询，避免双通道同时请求
        stopStrategyPolling(strategyId);
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'status') {
                updateStrategyStatusDisplay(strategyId, message.data, strategyType);
            } else if (message.type === 'error') {
                console.error(`策略 ${strategyId} WebSocket错误:`, message.message);
                const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
                if (statusContainer) {
                    statusContainer.innerHTML = 
                        `<p style="color: red;">错误: ${message.message}</p>`;
                }
                // 如果策略不存在，关闭连接并刷新策略列表
                if (message.message && (message.message.includes('策略不存在') || message.message.includes('策略已删除'))) {
                    ws.close();
                    setTimeout(() => {
                        loadStrategies();
                    }, 1000);
                }
            } else if (message.error) {
                // 处理连接时的错误（如策略不存在）
                console.error(`策略 ${strategyId} WebSocket错误:`, message.error);
                const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
                if (statusContainer) {
                    statusContainer.innerHTML = 
                        `<p style="color: red;">错误: ${message.error}</p>`;
                }
                // 策略不存在，关闭连接并刷新策略列表
                ws.close();
                setTimeout(() => {
                    loadStrategies();
                }, 1000);
            }
        } catch (error) {
            console.error('解析WebSocket消息失败:', error);
        }
    };
    
    ws.onerror = (error) => {
        console.error(`策略 ${strategyId} WebSocket错误:`, error);
        // 错误时回退到轮询：关闭当前WebSocket并停止重连逻辑
        try {
            ws.onerror = null;
            ws.onclose = null;
            ws.close();
        } catch (e) {
            console.error('关闭出错的WebSocket失败:', e);
        }
        delete strategyWebSockets[strategyId];
        // 启动轮询（通过统一管理，避免重复定时器）
        startStrategyPolling(strategyId, strategyType, true);
    };
    
    ws.onclose = (event) => {
        console.log(`WebSocket连接已关闭: ${strategyId}`, event.code, event.reason);
        delete strategyWebSockets[strategyId];
        
        // 如果是因为策略不存在而关闭（code 1000 或 1001），不重连，直接刷新策略列表
        if (event.code === 1000 || event.code === 1001) {
            // 正常关闭，可能是策略不存在
            const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
            if (statusContainer) {
                statusContainer.innerHTML = 
                    `<p style="color: orange;">策略不存在，可能服务器已重启。正在刷新策略列表...</p>`;
            }
            setTimeout(() => {
                loadStrategies();
            }, 1000);
        } else {
            // 其他原因关闭，尝试重连
            setTimeout(() => {
                if (document.getElementById(`strategy-${strategyId}`)) {
                    connectStrategyWebSocket(strategyId, symbol, strategyType);
                }
            }, 5000);
        }
    };
}

// 更新策略状态显示
function updateStrategyStatusDisplay(strategyId, status, strategyType) {
    const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
    if (!statusContainer) return;
    
    // 保存订单详情的展开状态和滚动位置（如果存在）
    const detailsDiv = document.getElementById(`order-details-${strategyId}`);
    const wasExpanded = detailsDiv && detailsDiv.classList.contains('expanded');
    const previousScrollTop = detailsDiv ? detailsDiv.scrollTop : 0;
    
    const isRunning = status.is_running;
    
    // 更新状态指示器
    const statusIndicator = document.getElementById(`strategy-status-indicator-${strategyId}`);
    if (statusIndicator) {
        if (isRunning) {
            statusIndicator.className = 'status-indicator running';
            statusIndicator.innerHTML = '<span class="status-dot running"></span><span>运行中</span>';
        } else {
            statusIndicator.className = 'status-indicator stopped';
            statusIndicator.innerHTML = '<span class="status-dot stopped"></span><span>已停止</span>';
        }
    }
    
    // 更新按钮状态
    const actionsDiv = document.querySelector(`#strategy-${strategyId} .actions`);
    if (actionsDiv) {
        if (isRunning) {
            actionsDiv.innerHTML = `
                <button class="btn-small" onclick="updateStrategy('${strategyId}', '${strategyType}')">更新</button>
                <button class="btn-small btn-danger" onclick="stopStrategy('${strategyId}', '${strategyType}')">停止</button>
                <button class="btn-small btn-danger" onclick="deleteStrategy('${strategyId}')" title="删除策略">删除</button>
            `;
        } else {
            actionsDiv.innerHTML = `
                <button class="btn-small" onclick="updateStrategy('${strategyId}', '${strategyType}')">更新</button>
                <button class="btn-small btn-success" onclick="startStrategy('${strategyId}', '${strategyType}')">启动</button>
                <button class="btn-small btn-danger" onclick="deleteStrategy('${strategyId}')" title="删除策略">删除</button>
            `;
        }
    }
    
    if (strategyType === 'sliding_window_grid') {
        // 格式化持仓信息
        const positionBtc = parseFloat(status.position_btc || 0);
        const positionInfo = status.position_info || {};
        const avgPrice = parseFloat(positionInfo.avg_price || 0);
        const unrealizedPnl = parseFloat(positionInfo.unrealized_pnl || 0);
        const positionSide = positionInfo.side || 'none';
        
        // 根据持仓方向
        let positionSideText = '';
        let positionSideClass = 'none';
        if (positionSide === 'long') {
            positionSideText = '多单';
            positionSideClass = 'long';
        } else if (positionSide === 'short') {
            positionSideText = '空单';
            positionSideClass = 'short';
        } else {
            positionSideText = '无持仓';
        }
        
        // 格式化订单列表
        const sellOrders = status.sell_orders || [];
        const buyOrders = status.buy_orders || [];
        const sellOrdersCount = status.sell_orders_count || sellOrders.length;
        const buyOrdersCount = status.buy_orders_count || buyOrders.length;
        
        // 对卖单按价格从大到小排序（最高价在顶部，最低价在底部）
        const sortedSellOrders = [...sellOrders].sort((a, b) => {
            const priceA = parseFloat(a.price) || 0;
            const priceB = parseFloat(b.price) || 0;
            return priceB - priceA;
        });
        
        // 对买单按价格从大到小排序
        const sortedBuyOrders = [...buyOrders].sort((a, b) => {
            const priceA = parseFloat(a.price) || 0;
            const priceB = parseFloat(b.price) || 0;
            return priceB - priceA;
        });
        
        // 生成订单表格HTML
        let sellOrdersTableHtml = '';
        if (sortedSellOrders.length > 0) {
            sellOrdersTableHtml = `
                <div class="order-table-container">
                    <div class="order-table-title">卖单 (${sortedSellOrders.length})</div>
                    <table class="order-table">
                        <thead>
                            <tr>
                                <th>价格</th>
                                <th>数量</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sortedSellOrders.map(order => `
                                <tr>
                                    <td class="price">${order.price}</td>
                                    <td class="quantity">${order.quantity}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        let buyOrdersTableHtml = '';
        if (sortedBuyOrders.length > 0) {
            buyOrdersTableHtml = `
                <div class="order-table-container">
                    <div class="order-table-title">买单 (${sortedBuyOrders.length})</div>
                    <table class="order-table">
                        <thead>
                            <tr>
                                <th>价格</th>
                                <th>数量</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sortedBuyOrders.map(order => `
                                <tr>
                                    <td class="price">${order.price}</td>
                                    <td class="quantity">${order.quantity}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // 构建新的HTML结构
        const pnlClass = unrealizedPnl >= 0 ? 'positive' : 'negative';
        const pnlSign = unrealizedPnl >= 0 ? '+' : '';
        
        // 使用卖1价格作为当前价格显示
        const displayPrice = status.ask_price || status.current_price || '--';
        
        statusContainer.innerHTML = `
            <!-- 关键指标网格 -->
            <div class="strategy-metrics">
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">当前价格</div>
                    <div class="strategy-metric-value">${displayPrice}</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">持仓数量</div>
                    <div class="strategy-metric-value">${positionBtc.toFixed(6)} BTC</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">未实现盈亏</div>
                    <div class="strategy-metric-value ${pnlClass}">${pnlSign}${unrealizedPnl.toFixed(2)}</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">活跃订单</div>
                    <div class="strategy-metric-value">${status.active_orders || 0}</div>
                </div>
            </div>
            
            <!-- 持仓信息 -->
            ${positionBtc !== 0 ? `
                <div class="position-info">
                    <span class="position-direction ${positionSideClass}">
                        ${positionSide === 'long' ? '↑' : positionSide === 'short' ? '↓' : ''} ${positionSideText}
                    </span>
                    <span>持仓: ${positionBtc.toFixed(6)} BTC</span>
                    <span>|</span>
                    <span>均价: ${avgPrice.toFixed(2)}</span>
                    <span>|</span>
                    <span class="${pnlClass}">盈亏: ${pnlSign}${unrealizedPnl.toFixed(2)}</span>
                </div>
            ` : ''}
            
            <!-- 市场数据 -->
            <div class="strategy-market-data">
                <div class="strategy-market-data-item">
                    <span class="strategy-market-data-label">买1:</span>
                    <span class="strategy-market-data-value">${status.bid_price || '--'}</span>
                </div>
                <div class="strategy-market-data-item">
                    <span class="strategy-market-data-label">卖1:</span>
                    <span class="strategy-market-data-value">${status.ask_price || '--'}</span>
                </div>
                <div class="strategy-market-data-item">
                    <span class="strategy-market-data-label">每单数量:</span>
                    <span class="strategy-market-data-value">${status.order_size || '--'}</span>
                </div>
                <div class="strategy-market-data-item">
                    <span class="strategy-market-data-label">循环次数:</span>
                    <span class="strategy-market-data-value">${status.cycle_count || 0}</span>
                </div>
            </div>
            
            <!-- 订单摘要 -->
            <div class="order-summary" onclick="toggleOrderDetails('${strategyId}', event)">
                <div class="order-summary-content">
                    <div class="order-summary-item">
                        <span class="order-summary-label">卖单:</span>
                        <span class="order-summary-value sell">${sellOrdersCount}</span>
                    </div>
                    <div class="order-summary-item">
                        <span class="order-summary-label">买单:</span>
                        <span class="order-summary-value buy">${buyOrdersCount}</span>
                    </div>
                    <div class="order-summary-item">
                        <span class="order-summary-label">总计:</span>
                        <span class="order-summary-value">${status.active_orders || 0}</span>
                    </div>
                </div>
                <span class="order-toggle ${wasExpanded ? 'expanded' : 'collapsed'}" id="order-toggle-${strategyId}">${wasExpanded ? '收起详情' : '展开详情'}</span>
            </div>
            
            <!-- 订单详情（可折叠） -->
            <div class="order-details ${wasExpanded ? 'expanded' : ''}" id="order-details-${strategyId}">
                ${sellOrdersTableHtml}
                ${buyOrdersTableHtml}
            </div>
        `;

        // 如果之前是展开状态，则恢复滚动位置
        if (wasExpanded) {
            const newDetailsDiv = document.getElementById(`order-details-${strategyId}`);
            if (newDetailsDiv) {
                newDetailsDiv.scrollTop = previousScrollTop;
            }
        }
    } else {
        // 传统网格策略
        // 使用卖1价格作为当前价格显示（如果有的话）
        const displayPrice = status.ask_price || status.current_price || '--';
        
        statusContainer.innerHTML = `
            <div class="strategy-metrics">
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">当前价格</div>
                    <div class="strategy-metric-value">${displayPrice}</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">网格数量</div>
                    <div class="strategy-metric-value">${status.grid_count || 0}</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">活跃订单</div>
                    <div class="strategy-metric-value">${status.active_orders || 0}</div>
                </div>
                <div class="strategy-metric-item">
                    <div class="strategy-metric-label">已成交</div>
                    <div class="strategy-metric-value">${status.filled_orders || 0}</div>
                </div>
            </div>
            <div class="strategy-market-data">
                <div class="strategy-market-data-item">
                    <span class="strategy-market-data-label">价格区间:</span>
                    <span class="strategy-market-data-value">${status.lower_price || 0} - ${status.upper_price || 0}</span>
                </div>
            </div>
        `;
    }
}

// 切换订单详情显示/隐藏
function toggleOrderDetails(strategyId, event) {
    // 阻止事件冒泡，防止触发其他点击事件
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    const detailsDiv = document.getElementById(`order-details-${strategyId}`);
    const toggleSpan = document.getElementById(`order-toggle-${strategyId}`);
    
    if (!detailsDiv || !toggleSpan) return;
    
    if (detailsDiv.classList.contains('expanded')) {
        detailsDiv.classList.remove('expanded');
        toggleSpan.classList.remove('expanded');
        toggleSpan.classList.add('collapsed');
        toggleSpan.textContent = '展开详情';
    } else {
        detailsDiv.classList.add('expanded');
        toggleSpan.classList.remove('collapsed');
        toggleSpan.classList.add('expanded');
        toggleSpan.textContent = '收起详情';
    }
}

// 加载策略状态（轮询方式，用于传统网格或WebSocket失败时）
async function loadStrategyStatus(strategyId, strategyType) {
    try {
        let statusEndpoint;
        if (strategyType === 'grid') {
            statusEndpoint = `${API_BASE}/strategy/grid/${strategyId}/status`;
        } else if (strategyType === 'sliding_window_grid') {
            statusEndpoint = `${API_BASE}/strategy/sliding-window-grid/${strategyId}/status`;
        } else {
            statusEndpoint = `${API_BASE}/strategy/grid/${strategyId}/status`;
        }
        
        // 为该策略的状态请求添加超时和并发控制
        // 如果上一次请求还在进行，先中止它，避免堆积
        if (strategyStatusControllers[strategyId]) {
            try {
                strategyStatusControllers[strategyId].abort();
            } catch (e) {
                console.warn(`中止上一次状态请求失败: ${strategyId}`, e);
            }
        }
        
        // 添加超时控制（30秒），并记录当前controller
        const controller = new AbortController();
        strategyStatusControllers[strategyId] = controller;
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        
        try {
            const statusRes = await fetch(statusEndpoint, {
                signal: controller.signal
            });
            
            // 如果策略不存在（404），刷新策略列表
            if (statusRes.status === 404) {
                const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
                if (statusContainer) {
                    statusContainer.innerHTML = 
                        `<p style="color: orange;">策略不存在，可能服务器已重启。正在刷新策略列表...</p>`;
                }
                setTimeout(() => {
                    loadStrategies();
                }, 1000);
                return;
            }
            
            if (!statusRes.ok) {
                throw new Error(`HTTP ${statusRes.status}: ${statusRes.statusText}`);
            }
            
            const status = await statusRes.json();
            updateStrategyStatusDisplay(strategyId, status, strategyType);
        } catch (fetchError) {
            if (fetchError.name === 'AbortError') {
                // 超时一般是网络抖动或后端暂时响应慢，保持上一次状态，不在卡片上展示错误
                console.warn(`加载策略状态超时（保持上次显示状态）: ${strategyId}`, fetchError);
                return;
            }
            throw fetchError;
        } finally {
            clearTimeout(timeoutId);
            // 仅在当前controller仍是最新时清理记录，防止覆盖新请求
            if (strategyStatusControllers[strategyId] === controller) {
                delete strategyStatusControllers[strategyId];
            }
        }
    } catch (error) {
        console.error(`加载策略状态失败: ${strategyId}`, error);
        const statusContainer = document.getElementById(`strategy-status-${strategyId}`);
        if (statusContainer) {
            // 提供更友好的错误信息
            let errorMessage = error.message || '未知错误';
            if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError')) {
                errorMessage = '网络连接失败，请检查服务器是否运行';
            } else if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
                errorMessage = '请求超时，请检查网络连接';
            }
            statusContainer.innerHTML = 
                `<p style="color: red;">加载状态失败: ${errorMessage}</p>`;
        }
    }
}

// 停止策略
async function stopStrategy(strategyId, strategyType) {
    if (!confirm('确定要停止这个策略吗？')) return;
    
    try {
        let endpoint;
        if (strategyType === 'grid') {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/stop`;
        } else if (strategyType === 'sliding_window_grid') {
            endpoint = `${API_BASE}/strategy/sliding-window-grid/${strategyId}/stop`;
        } else {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/stop`;
        }
        
        const res = await fetch(endpoint, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('策略已停止', 'success');
            // 停止WebSocket和轮询
            if (strategyWebSockets[strategyId]) {
                try {
                    strategyWebSockets[strategyId].close();
                } catch (e) {}
                delete strategyWebSockets[strategyId];
            }
            stopStrategyPolling(strategyId);
            // 刷新策略状态以更新按钮
            if (strategyType === 'sliding_window_grid') {
                loadStrategyStatus(strategyId, strategyType);
            } else {
                loadStrategies();
            }
        } else {
            // 如果策略不存在，可能是服务器重启导致，自动刷新策略列表
            if (res.status === 404) {
                showMessage(data.detail || '策略不存在，可能服务器已重启。正在刷新策略列表...', 'warning');
                setTimeout(() => {
                    loadStrategies();
                }, 1000);
            } else {
                showMessage(data.detail || '停止策略失败', 'error');
            }
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 启动策略
async function startStrategy(strategyId, strategyType) {
    try {
        let endpoint;
        if (strategyType === 'grid') {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/start`;
        } else if (strategyType === 'sliding_window_grid') {
            endpoint = `${API_BASE}/strategy/sliding-window-grid/${strategyId}/start`;
        } else {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/start`;
        }

        const res = await fetch(endpoint, {
            method: 'POST'
        });

        const data = await res.json();

        if (res.ok) {
            showMessage('策略已启动', 'success');
            // 启动成功后刷新状态 / 列表
            if (strategyType === 'sliding_window_grid') {
                // 仅刷新当前策略状态，避免全量刷新
                loadStrategyStatus(strategyId, strategyType);
            } else {
                loadStrategies();
            }
        } else {
            // 如果策略不存在，可能是服务器重启导致
            if (res.status === 404) {
                showMessage(data.detail || '策略不存在，可能服务器已重启。正在刷新策略列表...', 'warning');
                setTimeout(() => {
                    loadStrategies();
                }, 1000);
            } else {
                showMessage(data.detail || '启动策略失败', 'error');
            }
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 删除策略
async function deleteStrategy(strategyId) {
    if (!confirm('确定要删除这个策略吗？删除后无法恢复。')) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/strategy/${strategyId}`, {
            method: 'DELETE'
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('策略已删除', 'success');
            
            // 关闭WebSocket连接（如果存在）
            if (strategyWebSockets[strategyId]) {
                strategyWebSockets[strategyId].close();
                delete strategyWebSockets[strategyId];
            }
            // 停止轮询（如果存在）
            stopStrategyPolling(strategyId);
            
            // 从页面中移除策略卡片
            const strategyCard = document.getElementById(`strategy-${strategyId}`);
            if (strategyCard) {
                strategyCard.remove();
            }
            
            // 刷新策略列表
            loadStrategies();
        } else {
            showMessage(data.detail || '删除策略失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 更新策略
async function updateStrategy(strategyId, strategyType) {
    try {
        let endpoint;
        if (strategyType === 'grid') {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/update`;
        } else if (strategyType === 'sliding_window_grid') {
            endpoint = `${API_BASE}/strategy/sliding-window-grid/${strategyId}/update`;
        } else {
            endpoint = `${API_BASE}/strategy/grid/${strategyId}/update`;
        }
        
        const res = await fetch(endpoint, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('策略已更新', 'success');
            loadStrategies();
        } else {
            showMessage(data.detail || '更新策略失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 订单表单提交
document.getElementById('order-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const order = {
        symbol: document.getElementById('order-symbol').value,
        side: document.getElementById('order-side').value,
        order_type: document.getElementById('order-type').value,
        quantity: document.getElementById('order-quantity').value,
        price: document.getElementById('order-price').value || null
    };
    
    try {
        const res = await fetch(`${API_BASE}/order/place`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(order)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('订单提交成功！', 'success');
            document.getElementById('order-form').reset();
            loadOrders();
        } else {
            showMessage(data.detail || '订单提交失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
});

// 加载订单列表
async function loadOrders() {
    // TODO: 实现订单列表加载
    // 需要先选择交易对
    const symbol = prompt('请输入交易对（如 BTC/USDT）:');
    if (!symbol) return;
    
    try {
        const res = await fetch(`${API_BASE}/order/open/${encodeURIComponent(symbol)}`);
        const data = await res.json();
        
        const container = document.getElementById('order-list-container');
        container.innerHTML = '';
        
        if (data.orders.length === 0) {
            container.innerHTML = '<p>暂无未成交订单</p>';
            return;
        }
        
        for (const order of data.orders) {
            const item = document.createElement('div');
            item.className = 'order-item';
            item.innerHTML = `
                <div class="info">
                    <strong>${order.symbol}</strong>
                    <p>${order.side} | ${order.type} | 数量: ${order.quantity} | 价格: ${order.price || '市价'}</p>
                </div>
                <div class="actions">
                    <button class="btn-small btn-danger" onclick="cancelOrder('${order.symbol}', '${order.order_id}')">取消</button>
                </div>
            `;
            container.appendChild(item);
        }
    } catch (error) {
        console.error('加载订单列表失败:', error);
    }
}

// 取消订单
async function cancelOrder(symbol, orderId) {
    if (!confirm('确定要取消这个订单吗？')) return;
    
    try {
        const res = await fetch(`${API_BASE}/order/cancel/${encodeURIComponent(symbol)}/${orderId}`, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('订单已取消', 'success');
            loadOrders();
        } else {
            showMessage(data.detail || '取消订单失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 加载余额（显示所有交易所的余额）
async function loadBalance() {
    try {
        const res = await fetch(`${API_BASE}/exchange/balances`);
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || '获取余额失败');
        }
        
        const data = await res.json();
        
        const container = document.getElementById('balance-container');
        container.innerHTML = '';
        
        if (!data.balances || data.balances.length === 0) {
            container.innerHTML = '<p style="color: #999; padding: 20px; text-align: center;">暂无已配置的交易所</p>';
            return;
        }
        
        // 格式化数字显示
        const formatNumber = (num) => {
            const n = parseFloat(num);
            if (isNaN(n)) return '0.00';
            return n.toFixed(8).replace(/\.?0+$/, '');
        };
        
        // 为每个交易所创建余额卡片
        data.balances.forEach(exchangeBalance => {
            const card = document.createElement('div');
            card.className = 'balance-card';
            
            if (exchangeBalance.status === 'error') {
                // 显示错误信息
                card.innerHTML = `
                    <div class="balance-card-header">
                        <h3>${exchangeBalance.display_name}</h3>
                        <span class="exchange-badge ${exchangeBalance.testnet ? 'testnet' : 'mainnet'}">${exchangeBalance.testnet ? '测试网' : '主网'}</span>
                    </div>
                    <div class="balance-card-content">
                        <p style="color: red;">获取余额失败: ${exchangeBalance.error || '未知错误'}</p>
                    </div>
                `;
            } else if (exchangeBalance.balance) {
                const balance = exchangeBalance.balance;
                
                // 如果有多个币种余额（Extended格式）
                if (balance.balances && Array.isArray(balance.balances) && balance.balances.length > 0) {
                    let balancesHtml = '<div class="balance-list">';
                    balance.balances.forEach(b => {
                        balancesHtml += `
                            <div class="balance-item">
                                <div class="balance-currency">${b.currency || 'N/A'}</div>
                                <div class="balance-amounts">
                                    <div>可用: <strong>${formatNumber(b.available || '0')}</strong></div>
                                    <div>冻结: <strong>${formatNumber(b.frozen || '0')}</strong></div>
                                    <div>总计: <strong>${formatNumber(b.total || '0')}</strong></div>
                                </div>
                            </div>
                        `;
                    });
                    balancesHtml += '</div>';
                    
                    // 显示总余额
                    if (balance.total_wallet_balance) {
                        balancesHtml = `
                            <div class="balance-summary">
                                <div>总钱包余额: <strong>${formatNumber(balance.total_wallet_balance)}</strong></div>
                                <div>可用余额: <strong>${formatNumber(balance.available_balance || '0')}</strong></div>
                            </div>
                            ${balancesHtml}
                        `;
                    }
                    
                    card.innerHTML = `
                        <div class="balance-card-header">
                            <h3>${exchangeBalance.display_name}</h3>
                            <span class="exchange-badge ${exchangeBalance.testnet ? 'testnet' : 'mainnet'}">${exchangeBalance.testnet ? '测试网' : '主网'}</span>
                        </div>
                        <div class="balance-card-content">
                            ${balancesHtml}
                        </div>
                    `;
                } else {
                    // 标准格式：单个币种余额
                    card.innerHTML = `
                        <div class="balance-card-header">
                            <h3>${exchangeBalance.display_name}</h3>
                            <span class="exchange-badge ${exchangeBalance.testnet ? 'testnet' : 'mainnet'}">${exchangeBalance.testnet ? '测试网' : '主网'}</span>
                        </div>
                        <div class="balance-card-content">
                            <div class="balance-item">
                                <div class="balance-currency">${balance.currency || '全部'}</div>
                                <div class="balance-amounts">
                                    <div>可用: <strong>${formatNumber(balance.available || '0')}</strong></div>
                                    <div>冻结: <strong>${formatNumber(balance.frozen || '0')}</strong></div>
                                    <div>总计: <strong>${formatNumber(balance.total || balance.available || '0')}</strong></div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            } else {
                card.innerHTML = `
                    <div class="balance-card-header">
                        <h3>${exchangeBalance.display_name}</h3>
                        <span class="exchange-badge ${exchangeBalance.testnet ? 'testnet' : 'mainnet'}">${exchangeBalance.testnet ? '测试网' : '主网'}</span>
                    </div>
                    <div class="balance-card-content">
                        <p style="color: #999;">暂无余额信息</p>
                    </div>
                `;
            }
            
            container.appendChild(card);
        });
    } catch (error) {
        console.error('加载余额失败:', error);
        const container = document.getElementById('balance-container');
        container.innerHTML = `<p style="color: red;">加载余额失败: ${error.message}</p>`;
        showMessage('加载余额失败: ' + error.message, 'error');
    }
}

// 加载交易所配置
async function loadExchangeConfig() {
    try {
        // 并行加载支持的交易所列表和已配置的交易所，提高加载速度
        const [exchangesRes, configuredRes] = await Promise.allSettled([
            fetch(`${API_BASE}/exchange/list`),
            fetch(`${API_BASE}/config/exchanges`)
        ]);
        
        // 处理支持的交易所列表
        if (exchangesRes.status === 'fulfilled' && exchangesRes.value.ok) {
            const exchangesData = await exchangesRes.value.json();
            const exchangeSelect = document.getElementById('exchange-name');
            if (exchangeSelect) {
                exchangeSelect.innerHTML = '<option value="">请选择交易所</option>';
                exchangesData.exchanges.forEach(exchange => {
                    const option = document.createElement('option');
                    option.value = exchange;
                    option.textContent = exchange.charAt(0).toUpperCase() + exchange.slice(1);
                    exchangeSelect.appendChild(option);
                });
            }
        }
        
        // 处理已配置的交易所
        if (configuredRes.status === 'fulfilled' && configuredRes.value.ok) {
            const data = await configuredRes.value.json();
            await loadConfiguredExchangesData(data);
        } else if (configuredRes.status === 'fulfilled') {
            // 如果请求成功但返回非200，尝试单独加载
            await loadConfiguredExchanges();
        }
    } catch (error) {
        console.error('加载交易所配置失败:', error);
    }
}

// 加载已配置的交易所数据（从已获取的数据）
async function loadConfiguredExchangesData(data) {
    const container = document.getElementById('configured-exchanges-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (data.exchanges.length === 0) {
        container.innerHTML = '<p style="color: #999; padding: 20px; text-align: center;">暂无已配置的交易所</p>';
        return;
    }
    
    for (const exchange of data.exchanges) {
        const card = document.createElement('div');
        card.className = 'exchange-card';
        const displayName = exchange.account_alias || exchange.display_name || exchange.name;
        const exchangeName = exchange.exchange_name || '';
        const fullDisplayName = exchange.account_alias ? 
            `${exchange.account_alias} (${exchangeName})` : 
            displayName;
        card.innerHTML = `
            <div class="exchange-card-header">
                <h4>${fullDisplayName}</h4>
                <span class="exchange-badge ${exchange.testnet ? 'testnet' : 'mainnet'}">${exchange.testnet ? '测试网' : '主网'}</span>
            </div>
            <div class="exchange-card-actions">
                <button class="btn-small" onclick="editExchange('${exchange.account_key || exchange.name}')">编辑</button>
                <button class="btn-small btn-danger" onclick="deleteExchange('${exchange.account_key || exchange.name}')">删除</button>
            </div>
        `;
        container.appendChild(card);
    }
}

// 加载已配置的交易所卡片
async function loadConfiguredExchanges() {
    try {
        const res = await fetch(`${API_BASE}/config/exchanges`);
        const data = await res.json();
        
        const container = document.getElementById('configured-exchanges-container');
        container.innerHTML = '';
        
        if (data.exchanges.length === 0) {
            container.innerHTML = '<p style="color: #999; padding: 20px; text-align: center;">暂无已配置的交易所</p>';
            return;
        }
        
        data.exchanges.forEach(exchange => {
            const card = document.createElement('div');
            card.className = 'exchange-card';
            // 显示账号别名或显示名称
            const displayName = exchange.account_alias || exchange.display_name || exchange.name;
            const exchangeName = exchange.exchange_name || '';
            const fullDisplayName = exchange.account_alias ? 
                `${exchange.account_alias} (${exchangeName})` : 
                displayName;
            card.innerHTML = `
                <div class="exchange-card-header">
                    <h4>${fullDisplayName}</h4>
                    <span class="exchange-badge ${exchange.testnet ? 'testnet' : 'mainnet'}">${exchange.testnet ? '测试网' : '主网'}</span>
                </div>
                <div class="exchange-card-actions">
                    <button class="btn-small" onclick="editExchange('${exchange.account_key || exchange.name}')">编辑</button>
                    <button class="btn-small btn-danger" onclick="deleteExchange('${exchange.account_key || exchange.name}')">删除</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('加载已配置交易所失败:', error);
    }
}

// 编辑交易所配置（支持account_key）
async function editExchange(accountKeyOrName) {
    try {
        // 尝试通过account_key或exchange_name获取配置
        const res = await fetch(`${API_BASE}/config/exchange/${accountKeyOrName}`);
        if (!res.ok) {
            throw new Error('获取配置失败');
        }
        
        const config = await res.json();
        
        // 填充表单
        // 使用account_key作为编辑标识（如果存在），否则使用传入的值
        const editKey = config.account_key || accountKeyOrName;
        document.getElementById('editing-exchange-name').value = editKey;
        document.getElementById('exchange-name').value = config.name;
        document.getElementById('exchange-account-alias').value = config.account_alias || '';
        document.getElementById('exchange-api-key').value = config.api_key || '';
        document.getElementById('exchange-secret-key').value = config.secret_key || '';
        document.getElementById('exchange-testnet').checked = config.testnet || false;
        
        // Extended特定配置
        if (config.name.toLowerCase() === 'extended') {
            document.getElementById('extended-config').style.display = 'block';
            document.getElementById('exchange-public-key').value = config.public_key || '';
            document.getElementById('exchange-private-key').value = config.private_key || '';
            document.getElementById('exchange-vault').value = config.vault || '';
            document.getElementById('exchange-default-market').value = config.default_market || 'BTC-USD';
        } else {
            document.getElementById('extended-config').style.display = 'none';
        }
        
        // 更新表单标题和按钮
        document.getElementById('config-form-title').textContent = `编辑交易所: ${config.name.charAt(0).toUpperCase() + config.name.slice(1)}`;
        document.getElementById('save-config-btn').textContent = '更新配置';
        document.getElementById('cancel-edit-btn').style.display = 'inline-block';
        
        // 禁用交易所选择（编辑时不能更改交易所类型）
        document.getElementById('exchange-name').disabled = true;
        
        // 滚动到表单
        document.getElementById('exchange-config-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        showMessage('加载配置失败: ' + error.message, 'error');
    }
}

// 取消编辑
function cancelEdit() {
    document.getElementById('exchange-config-form').reset();
    document.getElementById('editing-exchange-name').value = '';
    document.getElementById('config-form-title').textContent = '添加新交易所';
    document.getElementById('save-config-btn').textContent = '保存配置';
    document.getElementById('cancel-edit-btn').style.display = 'none';
    document.getElementById('exchange-name').disabled = false;
    document.getElementById('extended-config').style.display = 'none';
    document.getElementById('config-status').innerHTML = '';
}

// 删除交易所配置
async function deleteExchange(exchangeName) {
    if (!confirm(`确定要删除交易所 ${exchangeName} 的配置吗？`)) return;
    
    try {
        const res = await fetch(`${API_BASE}/config/exchange/${exchangeName}`, {
            method: 'DELETE'
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('交易所配置已删除', 'success');
            await loadConfiguredExchanges();
        } else {
            showMessage(data.detail || '删除失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 交易所选择变化
function onExchangeChange() {
    const exchangeName = document.getElementById('exchange-name').value;
    const extendedConfig = document.getElementById('extended-config');
    
    if (exchangeName.toLowerCase() === 'extended') {
        extendedConfig.style.display = 'block';
    } else {
        extendedConfig.style.display = 'none';
    }
}

// 交易所配置表单提交
document.getElementById('exchange-config-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const config = {
        name: document.getElementById('exchange-name').value,
        api_key: document.getElementById('exchange-api-key').value,
        secret_key: document.getElementById('exchange-secret-key').value,
        testnet: document.getElementById('exchange-testnet').checked
    };
    
    // 账号别名（可选）
    const accountAlias = document.getElementById('exchange-account-alias').value.trim();
    if (accountAlias) {
        config.account_alias = accountAlias;
    }
    
    // Extended特定配置
    if (config.name.toLowerCase() === 'extended') {
        const publicKey = document.getElementById('exchange-public-key').value;
        const privateKey = document.getElementById('exchange-private-key').value;
        const vault = document.getElementById('exchange-vault').value;
        const defaultMarket = document.getElementById('exchange-default-market').value;
        
        if (publicKey) config.public_key = publicKey;
        if (privateKey) config.private_key = privateKey;
        if (vault) config.vault = parseInt(vault);
        if (defaultMarket) config.default_market = defaultMarket;
    }
    
    try {
        const res = await fetch(`${API_BASE}/config/exchange`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showMessage('配置保存成功！', 'success');
            document.getElementById('config-status').innerHTML = '<p style="color: green;">✓ 配置已保存</p>';
            
            // 重新加载已配置的交易所列表
            await loadConfiguredExchanges();
            
            // 重置表单（如果不是编辑模式）
            const editingName = document.getElementById('editing-exchange-name').value;
            if (!editingName) {
                document.getElementById('exchange-config-form').reset();
                document.getElementById('extended-config').style.display = 'none';
            } else {
                // 编辑模式：取消编辑状态
                cancelEdit();
            }
        } else {
            showMessage(data.detail || '配置保存失败', 'error');
            document.getElementById('config-status').innerHTML = '<p style="color: red;">✗ 配置保存失败</p>';
        }
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
        document.getElementById('config-status').innerHTML = '<p style="color: red;">✗ 网络错误</p>';
    }
});

// 测试连接
async function testConnection() {
    const config = {
        name: document.getElementById('exchange-name').value,
        api_key: document.getElementById('exchange-api-key').value,
        secret_key: document.getElementById('exchange-secret-key').value,
        testnet: document.getElementById('exchange-testnet').checked
    };
    
    if (!config.name || !config.api_key || !config.secret_key) {
        showMessage('请先填写完整的配置信息', 'error');
        return;
    }
    
    // 账号别名（可选）
    const accountAlias = document.getElementById('exchange-account-alias').value.trim();
    if (accountAlias) {
        config.account_alias = accountAlias;
    }
    
    // Extended特定配置
    if (config.name.toLowerCase() === 'extended') {
        const publicKey = document.getElementById('exchange-public-key').value;
        const privateKey = document.getElementById('exchange-private-key').value;
        const vault = document.getElementById('exchange-vault').value;
        const defaultMarket = document.getElementById('exchange-default-market').value;
        
        if (publicKey) config.public_key = publicKey;
        if (privateKey) config.private_key = privateKey;
        if (vault) config.vault = parseInt(vault);
        if (defaultMarket) config.default_market = defaultMarket;
    }
    
    document.getElementById('config-status').innerHTML = '<p>正在测试连接...</p>';
    
    try {
        const res = await fetch(`${API_BASE}/config/exchange/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        let data;
        try {
            data = await res.json();
        } catch (e) {
            // 如果响应不是JSON，尝试读取文本
            const text = await res.text();
            throw new Error(text || '服务器返回了无效的响应');
        }
        
        if (data.status === 'success') {
            showMessage('连接测试成功！', 'success');
            document.getElementById('config-status').innerHTML = '<p style="color: green;">✓ ' + (data.message || '连接成功') + '</p>';
        } else {
            const errorMsg = data.message || data.detail || '未知错误';
            showMessage('连接测试失败: ' + errorMsg, 'error');
            document.getElementById('config-status').innerHTML = '<p style="color: red;">✗ ' + errorMsg + '</p>';
        }
    } catch (error) {
        const errorMsg = error.message || '网络错误';
        showMessage('连接测试失败: ' + errorMsg, 'error');
        document.getElementById('config-status').innerHTML = '<p style="color: red;">✗ ' + errorMsg + '</p>';
    }
}

// 清空配置（已废弃，使用deleteExchange代替）
async function clearConfig() {
    if (!confirm('确定要清空所有交易所配置吗？')) return;
    
    try {
        // 获取所有已配置的交易所并逐个删除
        const res = await fetch(`${API_BASE}/config/exchanges`);
        const data = await res.json();
        
        for (const exchange of data.exchanges) {
            await fetch(`${API_BASE}/config/exchange/${exchange.name}`, {
                method: 'DELETE'
            });
        }
        
        showMessage('所有配置已清空', 'success');
        document.getElementById('exchange-config-form').reset();
        document.getElementById('extended-config').style.display = 'none';
        document.getElementById('config-status').innerHTML = '';
        await loadConfiguredExchanges();
    } catch (error) {
        showMessage('网络错误: ' + error.message, 'error');
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    // 恢复之前选中的标签页
    const savedTab = getSavedActiveTab();
    switchToTab(savedTab);
});

