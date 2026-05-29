import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (FULLY FIXED)
 */

const scene = new THREE.Scene();
const container = document.getElementById('dice-container');

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 6;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);

const purpleLight = new THREE.PointLight(0x8a2be2, 5, 20);
purpleLight.position.set(2, 3, 4);
scene.add(purpleLight);

const diceArray = [];
const geometry = new THREE.BoxGeometry(1, 1, 1);

// 各面に描画する数字の配置（サイコロの標準配置）
const faceNumbers = {
    right: 5,   // x+
    left: 2,    // x-
    up: 4,      // y+
    down: 3,    // y-
    front: 1,   // z+
    back: 6     // z-
};

function createDiceMaterials() {
    const dotPositions = {
        1: [[64, 64]],
        2: [[32, 32], [96, 96]],
        3: [[32, 32], [64, 64], [96, 96]],
        4: [[32, 32], [32, 96], [96, 32], [96, 96]],
        5: [[32, 32], [32, 96], [96, 32], [96, 96], [64, 64]],
        6: [[32, 32], [32, 64], [32, 96], [96, 32], [96, 64], [96, 96]]
    };

    const createTexture = (number) => {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, 128, 128);
        ctx.strokeStyle = '#8a2be2';
        ctx.lineWidth = 10;
        ctx.strokeRect(5, 5, 118, 118);
        ctx.fillStyle = '#ffffff';

        const dots = dotPositions[number];
        if (dots) {
            dots.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 14, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        const texture = new THREE.CanvasTexture(canvas);
        return new THREE.MeshStandardMaterial({
            map: texture,
            emissiveMap: texture,
            emissive: 0x333333,
            emissiveIntensity: 0.3,
            roughness: 0.2,
            metalness: 0.6,
            side: THREE.DoubleSide
        });
    };

    return [
        createTexture(faceNumbers.right),  // 右 (x+)
        createTexture(faceNumbers.left),   // 左 (x-)
        createTexture(faceNumbers.up),     // 上 (y+)
        createTexture(faceNumbers.down),   // 下 (y-)
        createTexture(faceNumbers.front),  // 前 (z+)
        createTexture(faceNumbers.back)    // 後 (z-)
    ];
}

function spawnDice(x) {
    const materials = createDiceMaterials();
    const mesh = new THREE.Mesh(geometry, materials);
    mesh.position.x = x;
    mesh.position.y = 0;
    mesh.userData = { originalX: x };
    mesh.quaternion.setFromEuler(new THREE.Euler(
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2
    ));
    scene.add(mesh);
    return mesh;
}

// 3つのサイコロを生成
diceArray.push(spawnDice(-1.8), spawnDice(0), spawnDice(1.8));

// 【修正版】正しい表示結果を得るための回転定義
const faceQuaternions = {
    1: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, 0, 'XYZ')),           // 前面
    2: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI / 2, 0, 'XYZ')), // +90度
    3: new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0, 'XYZ')),// 上面
    4: new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, 0, 'XYZ')), // 下面
    5: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -Math.PI / 2, 0, 'XYZ')),// -90度
    6: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI, 0, 'XYZ'))      // 背面
};

let isRolling = false;
let isFixed = false;
let rollSpeed = 0;
let stopTimeout = null;
let rollAnimationId = null;

function animateRoll() {
    if (!isRolling) return;

    diceArray.forEach((d, i) => {
        rollSpeed = Math.min(rollSpeed + 0.015, 0.35);
        const deltaRot = new THREE.Euler(
            rollSpeed * (1 + i * 0.1),
            rollSpeed * 1.3 * (1 - i * 0.05),
            rollSpeed * 0.9 * (1 + i * 0.08)
        );
        const deltaQuat = new THREE.Quaternion().setFromEuler(deltaRot);
        d.quaternion.premultiply(deltaQuat);
        d.position.y = Math.abs(Math.sin(Date.now() * 0.012 + i * 2)) * 0.4;
    });

    renderer.render(scene, camera);
    rollAnimationId = requestAnimationFrame(animateRoll);
}

function animateIdle() {
    if (isRolling || isFixed) {
        renderer.render(scene, camera);
        requestAnimationFrame(animateIdle);
        return;
    }

    diceArray.forEach((d, i) => {
        const idleRot = new THREE.Euler(0, 0.003 * (i + 1), 0);
        const idleQuat = new THREE.Quaternion().setFromEuler(idleRot);
        d.quaternion.premultiply(idleQuat);
        d.position.y = Math.sin(Date.now() * 0.001 + i) * 0.05;
    });

    renderer.render(scene, camera);
    requestAnimationFrame(animateIdle);
}

// アイドルアニメーション開始
animateIdle();

// --- 外部連携API ---

window.startDiceRoll = function() {
    if (stopTimeout) clearTimeout(stopTimeout);
    if (rollAnimationId) cancelAnimationFrame(rollAnimationId);

    isRolling = true;
    isFixed = false;
    rollSpeed = 0;

    diceArray.forEach((d, i) => {
        d.position.y = 0.2;
    });

    animateRoll();
    console.log("🎲 賽が回ります...");
};

window.stopDiceRoll = function(resultDice) {
    if (rollAnimationId) {
        cancelAnimationFrame(rollAnimationId);
        rollAnimationId = null;
    }
    isRolling = false;

    if (resultDice && Array.isArray(resultDice) && resultDice.length === 3) {
        isFixed = true;

        diceArray.forEach((dice, index) => {
            const targetValue = resultDice[index];
            const targetQuat = faceQuaternions[targetValue];

            if (targetQuat) {
                dice.quaternion.copy(targetQuat);
                dice.position.y = 0;
            }
        });

        console.log(`🎲 結果固定: ${resultDice.join(', ')}`);

        if (stopTimeout) clearTimeout(stopTimeout);
        stopTimeout = setTimeout(() => {
            isFixed = false;
        }, 8000);

    } else {
        isFixed = false;
        console.warn("無効な結果データ:", resultDice);
    }
};

window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});

console.log("🎲 3D Dice Engine 初期化完了（完全修正版）");