import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (Enhanced for Bot Sync)
 */

const scene = new THREE.Scene();
const container = document.getElementById('dice-container');

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 6;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambientLight);

const purpleLight = new THREE.PointLight(0x8a2be2, 2.5, 10);
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

function createDiceMaterials() {
    return Array(6).fill().map((_, i) => new THREE.MeshStandardMaterial({
        color: 0x0a0a0a,
        emissive: 0x8a2be2,
        emissiveIntensity: 0.3,
        roughness: 0.1,
        metalness: 0.7
    }));
}

function spawnDice(x) {
    const materials = createDiceMaterials();
    const mesh = new THREE.Mesh(geometry, materials);
    mesh.position.x = x;
    mesh.position.y = 0;
    mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
    scene.add(mesh);
    return mesh;
}

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
            d.position.y = Math.abs(Math.sin(Date.now() * 0.015 + i)) * 0.5;
        } else {
            rollSpeed = 0;
            // 待機中の浮遊感
            d.rotation.y += 0.005 * (i + 1);
            d.position.y = Math.sin(Date.now() * 0.001 + i) * 0.1;
        }
    });

    renderer.render(scene, camera);
}

animate();

// --- 外部連携API ---

/**
 * サイコロ回転開始
 */
window.startDiceRoll = function() {
    if (isRolling) return;
    isRolling = true;
    console.log("🎲 漆黒の賽が回ります...");
};

/**
 * サイコロ停止 (ボットの結果を反映)
 * @param {Array} resultDice - 例: [1, 2, 6]
 */
window.stopDiceRoll = function(resultDice) {
    isRolling = false;

    // ボットから有効な出目が届いた場合、その角度に固定する
    if (resultDice && Array.isArray(resultDice)) {
        diceArray.forEach((d, i) => {
            const val = resultDice[i];
            const rot = faceRotations[val];
            if (rot) {
                // 瞬間的に正しい角度へ（必要ならここをTweenアニメーションにしてもOK）
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
