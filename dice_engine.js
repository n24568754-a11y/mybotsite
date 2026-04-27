import * as THREE from 'three';

/**
 * VOID PLATFORM - 3D DICE ENGINE (High-Visibility Version)
 */

const scene = new THREE.Scene();
const container = document.getElementById('dice-container');

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 6;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

// ライトを少し強めに調整
const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);

const purpleLight = new THREE.PointLight(0x8a2be2, 5, 20);
purpleLight.position.set(2, 3, 4);
scene.add(purpleLight);

const diceArray = [];
const geometry = new THREE.BoxGeometry(1, 1, 1);

const faceRotations = {
    1: { x: 0,           y: 0 },             
    2: { x: -Math.PI / 2, y: 0 },            
    3: { x: 0,           y: Math.PI / 2 },    
    4: { x: 0,           y: -Math.PI / 2 },   
    5: { x: Math.PI / 2,  y: 0 },            
    6: { x: Math.PI,      y: 0 }             
};

/**
 * 目をハッキリと発光させるマテリアル作成
 */
function createDiceMaterials() {
    const dotPositions = [
        [], // 0
        [[64, 64]], // 1
        [[32, 32], [96, 96]], // 2
        [[32, 32], [64, 64], [96, 96]], // 3
        [[32, 32], [32, 96], [96, 32], [96, 96]], // 4
        [[32, 32], [32, 96], [96, 32], [96, 96], [64, 64]], // 5
        [[32, 32], [32, 64], [32, 96], [96, 32], [96, 64], [96, 96]] // 6
    ];

    return dotPositions.slice(1).map((dots) => {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        // 背景：完全な黒
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, 128, 128);

        // 枠線：紫
        ctx.strokeStyle = '#8a2be2';
        ctx.lineWidth = 10;
        ctx.strokeRect(5, 5, 118, 118);

        // 目：白（少し大きく、ハッキリと）
        ctx.fillStyle = '#ffffff';
        dots.forEach(([x, y]) => {
            ctx.beginPath();
            ctx.arc(x, y, 16, 0, Math.PI * 2);
            ctx.fill();
        });

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true; // 確実にテクスチャを更新

        return new THREE.MeshStandardMaterial({
            map: texture,
            emissiveMap: texture, // 白い目の部分を自ら光らせる
            emissive: 0xffffff,   // 発光色を白に
            emissiveIntensity: 0.4,
            roughness: 0.1,
            metalness: 0.5,
            side: THREE.DoubleSide // 面が裏返っていても表示する
        });
    });
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
                d.rotation.set(rot.x, rot.y, 0);
                d.position.y = 0; 
            }
        });
        console.log(`🎲 結果固定: ${resultDice}`);
    }
};

window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});
