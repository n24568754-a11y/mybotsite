import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (Perfect Rotation Sync - FIXED)
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

/**
 * 【修正版】正しい出目を正面に向けるための回転定義
 * Three.jsのBoxGeometryのマテリアルインデックス:
 * 0: 右 (x+), 1: 左 (x-), 2: 上 (y+), 3: 下 (y-), 4: 前 (z+), 5: 後 (z-)
 */
const faceRotations = {
    1: { x: 0,            y: 0,            z: 0 },        // 前面 (z+) = 目1
    2: { x: 0,            y: Math.PI,      z: 0 },        // 後面 (z-) = 目2
    3: { x: Math.PI / 2,  y: 0,            z: 0 },        // 下面 (y-) = 目3
    4: { x: -Math.PI / 2, y: 0,            z: 0 },        // 上面 (y+) = 目4
    5: { x: 0,            y: Math.PI / 2,  z: 0 },        // 右面 (x+) = 目5
    6: { x: 0,            y: -Math.PI / 2, z: 0 }         // 左面 (x-) = 目6
};

function createDiceMaterials() {
    const dotPositions = [
        [], [[64, 64]], [[32, 32], [96, 96]], [[32, 32], [64, 64], [96, 96]],
        [[32, 32], [32, 96], [96, 32], [96, 96]], 
        [[32, 32], [32, 96], [96, 32], [96, 96], [64, 64]],
        [[32, 32], [32, 64], [32, 96], [96, 32], [96, 64], [96, 96]]
    ];

    // マテリアルの順序: 右, 左, 上, 下, 前, 後
    // それぞれに割り当てる目の番号: 5, 6, 4, 3, 1, 2
    const materialOrder = [5, 6, 4, 3, 1, 2]; 

    return materialOrder.map((num) => {
        const dots = dotPositions[num];
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 128;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, 128, 128);
        ctx.strokeStyle = '#8a2be2'; ctx.lineWidth = 10; ctx.strokeRect(5, 5, 118, 118);
        ctx.fillStyle = '#ffffff';
        dots.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 16, 0, Math.PI * 2); ctx.fill(); });

        const texture = new THREE.CanvasTexture(canvas);
        return new THREE.MeshStandardMaterial({
            map: texture, emissiveMap: texture, emissive: 0xffffff,
            emissiveIntensity: 0.5, roughness: 0.1, metalness: 0.5, side: THREE.DoubleSide
        });
    });
}

function spawnDice(x) {
    const materials = createDiceMaterials();
    const mesh = new THREE.Mesh(geometry, materials);
    mesh.position.x = x; mesh.position.y = 0;
    mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
    scene.add(mesh);
    return mesh;
}

diceArray.push(spawnDice(-1.8), spawnDice(0), spawnDice(1.8));

let isRolling = false;
let isFixed = false; 
let rollSpeed = 0;
let stopTimeout = null;

function animate() {
    requestAnimationFrame(animate);

    diceArray.forEach((d, i) => {
        if (isRolling) {
            rollSpeed = Math.min(rollSpeed + 0.02, 0.4);
            d.rotation.x += rollSpeed;
            d.rotation.y += rollSpeed * 1.2;
            d.rotation.z += rollSpeed * 0.8;
            d.position.y = Math.abs(Math.sin(Date.now() * 0.015 + i)) * 0.5;
        } else if (!isFixed) {
            d.rotation.y += 0.005 * (i + 1);
            d.position.y = Math.sin(Date.now() * 0.001 + i) * 0.1;
        }
    });

    renderer.render(scene, camera);
}

animate();

// --- 外部連携API ---

window.startDiceRoll = function() {
    if (stopTimeout) clearTimeout(stopTimeout);
    isRolling = true;
    isFixed = false; 
    rollSpeed = 0;
    console.log("🎲 漆黒の賽が回ります...");
};

window.stopDiceRoll = function(resultDice) {
    isRolling = false;

    if (resultDice && Array.isArray(resultDice)) {
        isFixed = true; 
        diceArray.forEach((d, i) => {
            const val = resultDice[i];
            const rot = faceRotations[val];
            if (rot) {
                // Z軸も明示的にリセット
                d.rotation.set(rot.x, rot.y, rot.z);
                d.position.y = 0; 
            }
        });
        console.log(`🎲 結果固定: ${resultDice}`);

        // 5秒後にゆっくり回転を再開
        stopTimeout = setTimeout(() => {
            isFixed = false;
        }, 5000); 

    } else {
        isFixed = false;
        console.log("🎲 演出停止");
    }
};

window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h; camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});