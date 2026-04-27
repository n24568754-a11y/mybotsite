// --- 初期設定とFirebase ---
const firebaseConfig = { databaseURL: "https://mybot-4e6b1-default-rtdb.firebaseio.com/" };
firebase.initializeApp(firebaseConfig);
const database = firebase.database();

let GACHA_PRICES = { 'normal': 10000, 'limited_time': 30000, 'limited_stock': 50000 };
let sessionPassword = "", currentItem = null, rotationY = 0, isDragging = false, startX = 0, gachaResult = null;

// --- キャラクター（マスコット）設定データ ---
const mascotData = {
    'menu-page': {
        defaultImg: 'character.png',
        reactions: [
            { text: "おかえりなさいにゃ", img: "character.png" },
            { text: "おねむかにゃ", img: "character.png" },
            { text: "いい夢だといいにゃー", img: "character.png" }
        ]
    },
    'shop-page': {
        defaultImg: 'character_shop.png',
        reactions: [
            { text: "良い掘り出し物があるかもにゃ?", img: "character_shop_smile.png" },
            { text: "軍資金の確認を忘れずににゃ", img: "character_shop.png" },
            { text: "迷ったら買うにゃ！", img: "character_shop.png" }
        ]
    },
    'gacha-menu-page': {
        defaultImg: 'character_gacha.png',
        reactions: [
            { text: "おまじにゃい！", img: "character_gacha_excited.png" },
            { text: "きっといいものが出ます...", img: "character_gacha.png" },
            { text: "深追いは禁物にゃよ？", img: "character_gacha.png" }
        ]
    },
    'archive-page': {
        defaultImg: 'character.png',
        reactions: [
            { text: "これまでの軌跡だにゃー", img: "character.png" },
            { text: "コレクション、順調ですか？", img: "character.png" }
        ]
    },
    'tasks-page': {
        defaultImg: 'character.png',
        reactions: [
            { text: "ミッションをこなして報酬を稼ぐにゃ", img: "character.png" },
            { text: "勤勉だにゃー", img: "character.png" }
        ]
    },
    'profile-page': {
        defaultImg: 'character.png',
        reactions: [
            { text: "現在のステータスを表示してるにゃ", img: "character.png" },
            { text: "素晴らしい成績だにゃー", img: "character.png" }
        ]
    }
};

let currentActivePageId = 'menu-page';

// --- マウスの軌跡処理 ---
let lastMouseX = 0, lastMouseY = 0;
document.addEventListener('mousemove', (e) => {
    const x = e.clientX, y = e.clientY;
    const dist = Math.hypot(x - lastMouseX, y - lastMouseY);
    if (dist > 15) {
        const trail = document.createElement('div');
        trail.className = 'trail';
        trail.style.left = x + 'px'; trail.style.top = y + 'px';
        const angle = Math.atan2(y - lastMouseY, x - lastMouseX);
        trail.style.transform = `rotate(${angle}rad)`;
        document.body.appendChild(trail);
        setTimeout(() => trail.remove(), 500);
        lastMouseX = x; lastMouseY = y;
    }
});

// --- パーティクル生成 ---
function createParticles() {
    const container = document.getElementById('particle-container');
    if(!container) return;
    for(let i=0; i<20; i++) {
        const p = document.createElement('div'); p.className = 'particle';
        const size = Math.random() * 4 + 2;
        p.style.width = size + 'px'; p.style.height = size + 'px';
        p.style.left = Math.random() * 100 + 'vw';
        p.style.animationDuration = (Math.random() * 10 + 10) + 's';
        p.style.animationDelay = (Math.random() * 5) + 's';
        container.appendChild(p);
    }
}
createParticles();

// --- リアルタイム同期 ---
database.ref('/').on('value', (snapshot) => {
    const data = snapshot.val();
    if (data) {
        window.SHOP_DATA = data.SHOP_DATA || [];
        window.GACHA_DATA = data.GACHA_DATA || [];
        window.USER_PROFILES = data.USER_PROFILES || {};
        window.MISSIONS_DEF = data.MISSIONS || {};
        updateRanking(window.USER_PROFILES);
        if (sessionPassword) {
            if (!document.getElementById('profile-page').classList.contains('hidden')) updateProfileDisplay(sessionPassword);
            if (!document.getElementById('archive-page').classList.contains('hidden')) renderArchive();
            if (!document.getElementById('tasks-page').classList.contains('hidden')) renderMissions();
        }
    }
});

// --- 関数定義 ---
function updateRanking(profiles) {
    const list = document.getElementById('ranking-list');
    if(!list) return;
    list.innerHTML = "";
    const sorted = Object.entries(profiles).sort(([,a], [,b]) => b.money - a.money).slice(0, 8);
    sorted.forEach(([pwd, u], i) => {
        const item = document.createElement('div');
        item.className = 'rank-item';
        item.innerHTML = `<span class="rank-num">${i+1}</span><img src="${u.avatar}" class="rank-avatar" onerror="this.src='https://discord.com/assets/f78426a064bc98b57351.png'"><span class="rank-name">${u.name}</span><span class="rank-money">${Number(u.money).toLocaleString()}</span>`;
        list.appendChild(item);
    });
}

function toggleTheme() {
    const body = document.documentElement;
    const btn = document.querySelector('.theme-switch');
    if (body.getAttribute('data-theme') === 'light') { body.removeAttribute('data-theme'); btn.innerText = '🌙'; }
    else { body.setAttribute('data-theme', 'light'); btn.innerText = '☀️'; }
}

function showPage(id) {
    if ((id === 'archive-page' || id === 'tasks-page') && !sessionPassword) {
        document.getElementById('modal-confirm-btn').onclick = () => {
            const pwd = document.getElementById('password-input').value;
            if (window.USER_PROFILES && window.USER_PROFILES[pwd]) {
                sessionPassword = pwd;
                localStorage.setItem('user_pwd', pwd); // 追加
                closeModal(); showPage(id);
            } else { alert("ACCESS DENIED"); }
        };
        showModal(); return;
    }

    currentActivePageId = id; // 現在のページを記録
    document.querySelectorAll('main > div').forEach(c => c.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
    const layout = document.getElementById('main-layout-container');
    const sidebar = document.getElementById('main-sidebar');
    const ad = document.querySelector('.ad-section');

    if (id === 'menu-page') { 
        layout.classList.remove('full-width'); 
        sidebar.classList.remove('hidden'); 
        ad.classList.remove('hidden');
    } else { 
        layout.classList.add('full-width'); 
        sidebar.classList.add('hidden'); 
        ad.classList.add('hidden');
    }

    // --- キャラクターの更新ロジック ---
    const mData = mascotData[id];
    if (mData) {
        const imgEl = document.getElementById('mascot-img');
        const quoteEl = document.getElementById('char-quote');
        if(imgEl) imgEl.src = mData.defaultImg;
        if(quoteEl) quoteEl.innerText = mData.reactions[0].text;
    }

    if(id === 'shop-page') renderShop();
    if(id === 'gacha-menu-page') renderGachaMenu();
    if(id === 'archive-page') renderArchive();
    if(id === 'tasks-page') renderMissions();
    window.scrollTo(0,0);
}

// キャラクリック時の反応
document.addEventListener('DOMContentLoaded', () => {
    const mascotImg = document.getElementById('mascot-img');
    if(mascotImg) {
        mascotImg.addEventListener('click', () => {
            const data = mascotData[currentActivePageId];
            if (!data) return;

            const random = data.reactions[Math.floor(Math.random() * data.reactions.length)];
            const imgEl = document.getElementById('mascot-img');
            const quoteEl = document.getElementById('char-quote');

            imgEl.src = random.img;
            quoteEl.innerText = random.text;

            // アニメーション適用
            imgEl.classList.add('bounce-anim');
            setTimeout(() => imgEl.classList.remove('bounce-anim'), 500);
        });
    }
});

function renderArchive() {
    const container = document.getElementById('archive-grid');
    if (!container || !window.USER_PROFILES || !sessionPassword) return;
    container.innerHTML = "";

    const profile = window.USER_PROFILES[sessionPassword];
    const inventoryData = profile?.inventory ? Object.values(profile.inventory) : [];
    const ownedIds = new Set(inventoryData.map(id => String(id)));

    if (window.GACHA_DATA) {
        window.GACHA_DATA.forEach(item => {
            const div = document.createElement('div');
            const isOwned = ownedIds.has(String(item.id));
            div.className = `archive-item ${isOwned ? 'owned' : ''}`;
            const displayName = isOwned ? item.name : '???';
            div.innerHTML = `<img src="gacha_card.png" class="archive-img"><div class="archive-name">${displayName}</div>`;
            container.appendChild(div);
        });
    }
}

function renderMissions() {
    const container = document.getElementById('mission-list');
    if (!container || !window.USER_PROFILES || !sessionPassword) return;
    container.innerHTML = "";

    const u = USER_PROFILES[sessionPassword] || {};
    const completedMissions = u.completed_missions || [];
    const claimedMissions = u.claimed_missions || [];

    const dailyCont = document.createElement('div');
    const permanentCont = document.createElement('div');
    dailyCont.innerHTML = '<div class="mission-category-title">Daily Missions</div>';
    permanentCont.innerHTML = '<div class="mission-category-title">Permanent Missions</div>';

    let hasDaily = false, hasPermanent = false;

    if (window.MISSIONS_DEF) {
        Object.entries(window.MISSIONS_DEF).forEach(([m_id, m_info]) => {
            let typeKey = m_info.type;
            let typeLabel = "OBJ";
            let typeClass = "";

            if (typeKey === "chat_chars" || typeKey === "chat" || typeKey === "daily_chat") {
                typeLabel = "💬 CHAT"; typeKey = "chat"; typeClass = "type-chat";
            } else if (typeKey === "vc_minutes" || typeKey === "vc" || typeKey === "daily_vc") {
                typeLabel = "🔊 VC"; typeKey = "vc"; typeClass = "type-vc";
            }

            const currentVal = u.stats ? (u.stats[typeKey] ?? 0) : 0;
            const goal = m_info.goal;
            const isReached = completedMissions.includes(m_id) || currentVal >= goal;
            const isClaimed = claimedMissions.includes(m_id);
            const percent = Math.min(100, (currentVal / goal) * 100);

            const card = document.createElement('div');
            card.className = `mission-card ${isClaimed ? 'completed-claimed' : ''}`;

            let actionHtml = isClaimed ? `<span class="claimed-text">RECEIVED</span>` 
                : (isReached ? `<button class="claim-btn" onclick="claimMission('${m_id}', event)">CLAIM</button>` : "");

            card.innerHTML = `
                <div class="check-box">${isClaimed ? '✔' : ''}</div>
                <div class="mission-info">
                    <div class="mission-header">
                        <div style="display:flex; align-items:center;">
                            <span class="mission-type-badge ${typeClass}">${typeLabel}</span>
                            <span class="mission-title">${m_info.name}</span>
                        </div>
                        ${actionHtml}
                    </div>
                    <div class="mission-progress">${Math.floor(currentVal).toLocaleString()} / ${goal.toLocaleString()}</div>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: ${percent}%"></div></div>
                </div>`;

            if (m_id.includes('m_daily')) {
                dailyCont.appendChild(card); hasDaily = true;
            } else {
                permanentCont.appendChild(card); hasPermanent = true;
            }
        });
    }
    if (hasDaily) container.appendChild(dailyCont);
    if (hasPermanent) container.appendChild(permanentCont);
}

async function claimMission(missionId, event) {
    const url = (typeof CONFIG !== 'undefined') ? CONFIG.webhookUrl : "";
    if (!url || !sessionPassword) return;

    const btn = event.target;
    btn.disabled = true; btn.innerText = "WAIT...";

    try {
        await fetch(url, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: `!mission_pay ${sessionPassword} ${missionId}` })
        });
        alert("報酬を申請しました。ボットの処理をお待ちください。");
    } catch(e) {
        alert("通信エラーが発生しました。");
        btn.disabled = false; btn.innerText = "CLAIM";
    }
}

function renderShop() {
    const container = document.getElementById('shop-items');
    if (!container) return;
    container.innerHTML = ""; 
    if (!window.SHOP_DATA || !window.SHOP_DATA.length) return;
    const step = 360 / SHOP_DATA.length;
    const r = Math.max(400, 180 / Math.tan(Math.PI / SHOP_DATA.length));
    SHOP_DATA.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'card'; card.style.backgroundImage = "url('shop_card.png')";
        card.style.transform = `rotateY(${i * step}deg) translateZ(${r}px)`;
        card.innerHTML = `<h3>${item.name}</h3><p>${item.desc}</p><div class="money-display" style="font-size:24px;">${item.price.toLocaleString()}</div><button class="main-shop-btn" onclick="openBuyModal('${item.name}', ${item.price}, '${item.id}')">BUY NOW</button>`;
        container.appendChild(card);
    });
    setupRotation();
}

function setupRotation() {
    const el = document.getElementById('shop-items');
    const cardContainer = document.querySelector('.card-container');
    if (!cardContainer || !el) return;
    cardContainer.onmousedown = (e) => { isDragging = true; startX = e.pageX; };
    cardContainer.ontouchstart = (e) => { isDragging = true; startX = e.touches[0].pageX; };
    window.onmousemove = (e) => {
        if (!isDragging) return;
        const delta = (e.pageX - startX) * 0.5; rotationY += delta;
        el.style.transform = `rotateY(${rotationY}deg)`; startX = e.pageX;
    };
    window.ontouchmove = (e) => {
        if (!isDragging) return;
        const delta = (e.touches[0].pageX - startX) * 0.5; rotationY += delta;
        el.style.transform = `rotateY(${rotationY}deg)`; startX = e.touches[0].pageX;
    };
    window.onmouseup = window.ontouchend = () => { isDragging = false; };
}

function renderGachaMenu() {
    const container = document.getElementById('gacha-types-container');
    if (!container) return;
    container.innerHTML = "";
    const types = [{ id: 'normal', name: '通常召喚' }, { id: 'limited_time', name: '期間限定' }, { id: 'limited_stock', name: '数量限定' }];
    types.forEach(t => {
        const btn = document.createElement('button'); btn.className = 'main-shop-btn';
        btn.style.width = "280px"; btn.innerHTML = `${t.name}<br><small>${GACHA_PRICES[t.id].toLocaleString()} Credits</small>`;
        btn.onclick = () => openGachaAuth(t.id, GACHA_PRICES[t.id]);
        container.appendChild(btn);
    });
}

function openGachaAuth(type, price) {
    const pool = GACHA_DATA.filter(i => i.type === type && (i.stock === -1 || i.stock > 0));
    if (!pool.length) return alert("EMPTY.");
    document.getElementById('modal-confirm-btn').onclick = async () => { 
        const pwd = document.getElementById('password-input').value;
        if (!window.USER_PROFILES[pwd]) { alert("ACCESS DENIED"); return; }
        sessionPassword = pwd;
        localStorage.setItem('user_pwd', pwd); // 追加
        gachaResult = pool[Math.floor(Math.random() * pool.length)];
        currentItem = { name: "ガチャ召喚", price: price, id: gachaResult.id };
        closeModal(); await executeOrderSilent(pwd); startGachaAnimation();
    };
    showModal();
}

function startGachaAnimation() {
    document.getElementById('gacha-reveal-modal').classList.add('active');
    document.getElementById('chest-container').classList.remove('hidden');
    document.getElementById('gacha-result-area').classList.add('hidden');
}

function revealGachaResult() {
    document.getElementById('chest-container').classList.add('hidden');
    document.getElementById('gacha-result-area').classList.remove('hidden');
    const resultBox = document.getElementById('result-card-box');
    resultBox.style.backgroundImage = "url('gacha_card.png')";
    document.getElementById('result-series').innerText = gachaResult.series;
    document.getElementById('result-name').innerText = gachaResult.name;
}

function closeGachaReveal() { document.getElementById('gacha-reveal-modal').classList.remove('active'); showPage('menu-page'); }
function showModal() { document.getElementById('password-input').value = sessionPassword; document.getElementById('auth-modal').classList.add('active'); }
function closeModal() { document.getElementById('auth-modal').classList.remove('active'); }

function openBuyModal(name, price, id) {
    currentItem = { name, price, id };
    document.getElementById('modal-confirm-btn').onclick = async () => { 
        const pwd = document.getElementById('password-input').value;
        if (!window.USER_PROFILES[pwd]) { alert("ACCESS DENIED"); return; }
        sessionPassword = pwd;
        localStorage.setItem('user_pwd', pwd); // 追加
        await executeOrderSilent(pwd);
        closeModal(); alert("購入リクエストを送信しました。");
    };
    showModal();
}

function openProfileAuth() {
    document.getElementById('modal-confirm-btn').onclick = () => {
        const pwd = document.getElementById('password-input').value;
        if (window.USER_PROFILES && window.USER_PROFILES[pwd]) {
            sessionPassword = pwd;
            localStorage.setItem('user_pwd', pwd); // 追加
            closeModal();
            updateProfileDisplay(pwd); showPage('profile-page');
        } else { alert("ACCESS DENIED"); }
    };
    showModal();
}

function updateProfileDisplay(pwd) {
    const u = USER_PROFILES[pwd]; if (!u) return;
    document.getElementById('prof-avatar').src = u.avatar;
    document.getElementById('prof-name').innerText = u.name;
    document.getElementById('prof-money').innerText = Number(u.money).toLocaleString();
    document.getElementById('prof-subs').innerText = Object.keys(u.subscriptions || {}).length;
    document.getElementById('prof-chat').innerText = (u.stats?.chat || 0).toLocaleString();
    document.getElementById('prof-vc').innerText = (u.stats?.vc || 0).toLocaleString();
}

async function executeOrderSilent(password) {
    const url = (typeof CONFIG !== 'undefined') ? CONFIG.webhookUrl : "";
    if (!url) return;
    await fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: `!pay_req ${password} ${currentItem.id} ${currentItem.price} ${currentItem.name}` })
    });
}
