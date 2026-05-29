import * as THREE from 'three';

const scene = new THREE.Scene();
const container = document.getElementById('dice-container');

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 8;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);
const purpleLight = new THREE.PointLight(0x8a2be2, 5, 20);
purpleLight.position.set(2, 3, 4);
scene.add(purpleLight);
const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
fillLight.position.set(-2, 1, -3);
scene.add(fillLight);

// 各面に描画する数字を明確に定義（サイコロの標準配置）
// 標準的なサイコロ: 1-6, 2-5, 3-4 が対面
// 正面(1) - 背面(6), 右面(2) - 左面(5), 上面(3) - 下面(4)
const faceNumbers = {
    right: 2,   // x+
    left: 5,    // x-
    up: 3,      // y+
    down: 4,    // y-
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
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, 256, 256);
        ctx.strokeStyle = '#8a2be2';
        ctx.lineWidth = 15;
        ctx.strokeRect(10, 10, 236, 236);
        ctx.fillStyle = '#ffffff';

        const dots = dotPositions[number];
        if (dots) {
            dots.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 24, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // デバッグ用に数字を直接描画（確認用）
        ctx.font = 'Bold 40px "Meiryo"';
        ctx.fillStyle = '#ffaa00';
        ctx.shadowBlur = 0;
        ctx.fillText(number.toString(), 200, 50);

        const texture = new THREE.CanvasTexture(canvas);
        return new THREE.MeshStandardMaterial({ map: texture, roughness: 0.2, metalness: 0.5 });
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

// 正面に表示したい数字と、そのための回転角度
// 正面を向かせたい数字と、それに必要な回転
const rotationsToShowNumber = {
    1: { x: 0, y: 0, z: 0 },                    // 前面そのまま
    2: { x: 0, y: Math.PI, z: 0 },              // 背面を前に
    3: { x: -Math.PI / 2, y: 0, z: 0 },         // 上面を前に
    4: { x: Math.PI / 2, y: 0, z: 0 },          // 下面を前に
    5: { x: 0, y: -Math.PI / 2, z: 0 },         // 右面を前に
    6: { x: 0, y: Math.PI / 2, z: 0 }           // 左面を前に
};

const geometry = new THREE.BoxGeometry(1.2, 1.2, 1.2);
const materials = createDiceMaterials();
const dice = new THREE.Mesh(geometry, materials);
scene.add(dice);

// カメラコントロール用
let isDragging = false;
let lastX = 0;
let lastY = 0;
let targetRotationX = 0.5;
let targetRotationY = 0.5;

renderer.domElement.addEventListener('mousedown', (e) => {
    isDragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
});
window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const deltaX = e.clientX - lastX;
    const deltaY = e.clientY - lastY;
    targetRotationY += deltaX * 0.01;
    targetRotationX += deltaY * 0.01;
    lastX = e.clientX;
    lastY = e.clientY;
});
window.addEventListener('mouseup', () => { isDragging = false; });

function animate() {
    requestAnimationFrame(animate);
    dice.rotation.x = targetRotationX;
    dice.rotation.y = targetRotationY;
    renderer.render(scene, camera);
}
animate();

// テスト用：特定の数字を正面に表示
window.showNumber = (num) => {
    const rot = rotationsToShowNumber[num];
    if (rot) {
        targetRotationX = rot.x;
        targetRotationY = rot.y;
        console.log(`数字 ${num} を正面に表示: x=${rot.x}, y=${rot.y}`);
    }
};

// 現在の正面の数字を取得
window.getFrontNumber = () => {
    // 簡易的な判定
    const rx = dice.rotation.x % (Math.PI * 2);
    const ry = dice.rotation.y % (Math.PI * 2);

    // 各軸の許容誤差
    const eps = 0.3;

    if (Math.abs(ry) < eps) return 1;
    if (Math.abs(ry - Math.PI) < eps || Math.abs(ry + Math.PI) < eps) return 2;
    if (Math.abs(rx + Math.PI/2) < eps) return 3;
    if (Math.abs(rx - Math.PI/2) < eps) return 4;
    if (Math.abs(ry + Math.PI/2) < eps) return 5;
    if (Math.abs(ry - Math.PI/2) < eps) return 6;
    return "?";
};

console.log("=== サイコロテストツール ===");
console.log("マウスドラッグで回転");
console.log("コンソールで showNumber(1) などと入力して正面を表示");
console.log("getFrontNumber() で現在の正面の数字を取得");