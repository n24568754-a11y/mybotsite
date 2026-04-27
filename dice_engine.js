import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (Visual Result Version)
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
 * 視覚的に結果がわかる「正面向き」の回転定義
 * ボットからの数字をカメラ側にピタッと向けるための座標データ
 */
const faceRotations = {
    1: { x: 0,            y: 0 },              // 1: 正面
    2: { x: 0,            y: -Math.PI / 2 },   // 2: 右面を正面へ
    3: { x: Math.PI / 2,  y: 0 },              // 3: 底面を正面へ
    4: { x: -Math.PI / 2, y: 0 },              // 4: 天面を正面へ
    5: { x: 0,            y: Math.PI / 2 },    // 5: 左面を正面へ
    6: { x: Math.PI,      y: 0 }               // 6: 背面を正面へ
};

function createDiceMaterials() {
    const dotPositions = [
        [], [[64, 64]], [[32, 32], [96, 96]], [[32, 32], [64, 64], [96, 96]],
        [[32, 32], [32, 96], [96, 32], [96, 96]], 
        [[32, 32], [32, 96], [96, 32], [96, 96], [64, 64]],
        [[32, 32], [32, 64], [32, 96], [96, 32], [96, 64], [96, 96]]
    ];

    return dotPositions.slice(1).map((dots) => {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 128;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, 128, 128);
        ctx.strokeStyle = '#8a2be2'; ctx.lineWidth = 10; ctx.strokeRect(5, 5, 118, 118);
        ctx.fillStyle = '#ffffff';
        dots.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 16, 0, Math.PI * 2); ctx.fill(); });

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;

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
let isFixed = false; // 10秒間ピタッと止めるためのフラグ
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
            // 通常待機時はゆっくり回転して浮遊
            d.rotation.y += 0.005 * (i + 1);
            d.position.y = Math.sin(Date.now() * 0.001 + i) * 0.1;
        }
        // isFixedがtrueの時は、d.rotationもd.positionも更新しない（完全に静止）
    });

    renderer.render(scene, camera);
}

animate();

// --- 外部連携API ---

window.startDiceRoll = function() {
    if (stopTimeout) clearTimeout(stopTimeout);
    isRolling = true;
    isFixed = false; 
    console.log("🎲 漆黒の賽が回ります...");
};

window.stopDiceRoll = function(resultDice) {
    isRolling = false;

    if (resultDice && Array.isArray(resultDice)) {
        isFixed = true; // アニメーションを停止フラグ
        diceArray.forEach((d, i) => {
            const val = resultDice[i];
            const rot = faceRotations[val];
            if (rot) {
                // 結果の数字をカメラ（正面）へ向ける
                d.rotation.set(rot.x, rot.y, 0);
                d.position.y = 0; 
            }
        });
        console.log(`🎲 結果固定(10秒間): ${resultDice}`);

        // 10秒後に「ゆらゆら待機モード」に戻る
        stopTimeout = setTimeout(() => {
            isFixed = false;
        }, 10000); 

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
