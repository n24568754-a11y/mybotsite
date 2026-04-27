/**
 * CAPITALISM - UNDERGROUND CHINCHIRO SYSTEM
 * Web-Discord Sync Logic (Final Sync Version)
 */

// Firebaseの初期化（config.jsが読み込まれている前提）
const database = firebase.database();

document.addEventListener('DOMContentLoaded', () => {
    const rollBtn = document.getElementById('roll-button');
    const betInput = document.getElementById('bet-input');
    const displayMoney = document.getElementById('display-money');
    const resultArea = document.getElementById('result-display');
    const resultRank = document.getElementById('result-rank');
    const resultDetail = document.getElementById('result-detail');
    const charQuote = document.getElementById('char-quote');

    // 1. 所持金のリアルタイム同期
    function syncBalance() {
        const pwd = localStorage.getItem('user_pwd');
        if (!pwd) {
            if (charQuote) charQuote.innerText = "IDENTITYを認証してください。";
            return;
        }

        // USER_PROFILESの下にある指定パスワードのmoneyを監視
        database.ref(`USER_PROFILES/${pwd}/money`).on('value', (snap) => {
            const currentMoney = snap.val() || 0;
            if (displayMoney) displayMoney.innerText = currentMoney.toLocaleString();
        });
    }
    syncBalance();

    // 2. メイン実行関数
    window.startChinchiroProcess = async function() {
        const pwd = localStorage.getItem('user_pwd');
        const betAmount = parseInt(betInput.value);

        // バリデーション
        if (!pwd) {
            alert("IDENTITYページでパスワードを認証してください。");
            return resetUI();
        }
        if (isNaN(betAmount) || betAmount < 100) {
            alert("100 CPL以上を賭けてください。");
            return resetUI();
        }

        // Firebaseにリクエストを送信 (Discordボットがこれを監視)
        const reqId = Date.now();
        const reqRef = database.ref('CHINCHIRO_SYSTEM/REQUESTS').push();

        await reqRef.set({
            pwd: pwd,
            bet: betAmount,
            timestamp: reqId
        });

        // ボットからの結果を待機 (CHINCHIRO_LAST_RESULT/[pwd])
        const resultRef = database.ref(`CHINCHIRO_LAST_RESULT/${pwd}`);

        // 8秒でタイムアウト設定
        const timeout = setTimeout(() => {
            alert("ディーラー（ボット）からの応答がありません。");
            resetUI();
        }, 8000);

        resultRef.on('value', (snapshot) => {
            const data = snapshot.val();

            // 書き込まれたデータが今回のリクエスト以降のものか確認
            if (data && data.timestamp && new Date(data.timestamp).getTime() >= reqId) {
                clearTimeout(timeout);
                resultRef.off(); // 監視を終了

                /**
                 * 【重要修正箇所】
                 * dice_engine.js の関数名 window.stopDiceRoll に合わせて呼び出す
                 */
                if (typeof window.stopDiceRoll === 'function') {
                    window.stopDiceRoll(data.dice);
                }

                // アニメーション演出（2秒）の後に結果を表示
                setTimeout(() => {
                    showFinalResult(data);
                }, 2000); 
            }
        });
    };

    // 3. 結果表示処理
    function showFinalResult(data) {
        if (!resultArea) return;

        resultArea.classList.remove('hidden');
        resultRank.innerText = data.result;
        resultDetail.innerText = `出目: ${data.dice.join(', ')} | 収支: ${data.change.toLocaleString()} CPL`;

        // キャラクターメッセージの更新
        if (data.change > 0) {
            charQuote.innerText = "運命は貴方に微笑んだようです。おめでとう。";
            resultRank.style.color = "gold";
        } else if (data.change < 0) {
            charQuote.innerText = "奈落へようこそ。次があるかは分かりませんが。";
            resultRank.style.color = "#ff4444";
        } else {
            charQuote.innerText = "引き分けか… 命拾いしましたね。";
            resultRank.style.color = "#fff";
        }

        resetUI();
    }

    // 4. UI状態のリセット
    function resetUI() {
        if (rollBtn) {
            rollBtn.disabled = false;
            rollBtn.innerText = "賽を振る / ROLL";
        }
        if (betInput) {
            betInput.disabled = false;
        }
    }

    // 5. ボタンイベントの設定
    if (rollBtn) {
        rollBtn.addEventListener('click', () => {
            // dice_engine.js の3D演出を開始
            if (typeof window.startDiceRoll === 'function') {
                window.startDiceRoll();
            }

            // UIをロック
            rollBtn.disabled = true;
            betInput.disabled = true;
            rollBtn.innerText = "ROLLING...";
            if (resultArea) resultArea.classList.add('hidden');

            // 処理開始
            startChinchiroProcess();
        });
    }
});
