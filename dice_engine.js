import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (Image-free Version)
 */

const scene = new THREE.Scene();
const container = document.getElementById('dice-container');

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 6;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const purpleLight = new THREE.PointLight(0x8a2be2, 3, 15);
purpleLight.position.set(2, 3, 4);
scene.add(purpleLight);

const diceArray = [];
const geometry = new THREE.BoxGeometry(1, 1, 1);

// 各面に対応する回転角度（ボットの結果を上に向けるための定義）
const faceRotations = {
    1: { x: 0,           y: 0 },             // 前面
    2: { x: -Math.PI / 2, y: 0 },            // 底面が前にくる -> 上が2
    3: { x: 0,           y: Math.PI / 2 },    // 右面が前にくる -> 上が3
    4: { x: 0,           y: -Math.PI / 2 },   // 左面が前にくる -> 上が4
    5: { x: Math.PI / 2,  y: 0 },            // 天面が前にくる -> 上が5
    6: { x: Math.PI,      y: 0 }             // 背面が前にくる -> 上が6
};

/**
 * 画像を使わずにサイコロのテクスチャをCanvasで生成する
 */
function createDiceMaterials() {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    // サイコロの目の配置データ
    const dotPositions = [
        [], // 0
        [[64, 64]], // 1
        [[32, 32], [96, 96]], // 2
        [[32, 32], [64, 64], [96, 96]], // 3
        [[32, 32], [32, 96], [96, 32], [96, 96]], // 4
        [[32, 32], [32, 96], [96, 32], [96, 96], [64, 64]], // 5
        [[32, 32], [32, 64], [32, 96], [96, 32], [96, 64], [96, 96]] // 6
    ];

    // 各面のテクスチャを生成（全6面）
    return dotPositions.slice(1).map((dots) => {
        // 背景（漆黒）
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, 128, 128);

        // 枠線（魔力的な紫）
        ctx.strokeStyle = '#8a2be2';
        ctx.lineWidth = 6;
        ctx.strokeRect(4, 4, 120, 120);

        // 目（白点）
        ctx.fillStyle = '#ffffff';
        dots.forEach(([x, y]) => {
            ctx.beginPath();
            ctx.arc(x, y, 12, 0, Math.PI * 2);
            ctx.fill();
            // 目の周りにかすかな光
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#8a2be2';
        });
        ctx.shadowBlur = 0; // リセット

        const texture = new THREE.CanvasTexture(canvas.cloneNode(true));
        return new THREE.MeshStandardMaterial({
            map: texture,
            emissive: 0x8a2be2,
            emissiveIntensity: 0.2,
            roughness: 0.1,
            metalness: 0.5
        });
    });
}

function spawnDice(x) {
    const materials = createDiceMaterials();
    const mesh = new THREE.Mesh(geometry, materials);
    mesh.position.x = x;
    mesh.position.y = 0;
    // 初期角度をランダムに
    mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
    scene.add(mesh);
    return mesh;
}

// 3つのサイコロを配置
diceArray.push(spawnDice(-1.8));
diceArray.push(spawnDice(0));
diceArray.push(spawnDice(1.8));

let isRolling = false;
let rollSpeed = 0;

function animate() {
    requestAnimationFrame(animate);

    diceArray.forEach((d, i) => {
        if (isRolling) {
            rollSpeed = Math.min(rollSpeed + 0.02, 0.4);
            d.rotation.x += rollSpeed;
            d.rotation.y += rollSpeed * 1.2;
            d.rotation.z += rollSpeed * 0.8;
            // 跳ねる動き
            d.position.y = Math.abs(Math.sin(Date.now() * 0.015 + i)) * 0.5;
        } else {
            rollSpeed = 0;
            // 待機中のゆらゆらした動き
            d.rotation.y += 0.005 * (i + 1);
            d.position.y = Math.sin(Date.now() * 0.001 + i) * 0.1;
        }
    });

    renderer.render(scene, camera);
}

animate();

// --- 外部連携API ---

window.startDiceRoll = function() {
    if (isRolling) return;
    isRolling = true;
    console.log("🎲 漆黒の賽が回ります...");
};

window.stopDiceRoll = function(resultDice) {
    isRolling = false;

    if (resultDice && Array.isArray(resultDice)) {
        diceArray.forEach((d, i) => {
            const val = resultDice[i];
            const rot = faceRotations[val];
            if (rot) {
                // 結果の角度へ固定
                d.rotation.set(rot.x, rot.y, 0);
                d.position.y = 0; 
            }
        });
        console.log(`🎲 結果固定: ${resultDice}`);
    } else {
        console.log("🎲 演出停止");
    }
};

window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});
